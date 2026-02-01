"""
Import utilities for HalalPlace data from JSON and CSV files.
"""

import csv
import json
import io
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, date
from decimal import Decimal
from django.contrib.gis.geos import Point
from django.db import transaction
from django.core.exceptions import ValidationError
from .models import HalalPlace, BusinessHours, TimeSlot


class ImportResult:
    """Result container for import operations."""

    def __init__(self):
        self.created_count = 0
        self.updated_count = 0
        self.skipped_count = 0
        self.error_count = 0
        self.errors: List[Dict[str, Any]] = []
        self.warnings: List[str] = []
        self.row_details: List[Dict[str, Any]] = []
        self.total_rows = 0

    def add_error(self, row_num: int, field: str, message: str, data: Dict = None):
        self.errors.append(
            {"row": row_num, "field": field, "message": message, "data": data or {}}
        )
        self.error_count += 1

    def add_warning(self, message: str):
        self.warnings.append(message)

    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics for display."""
        return {
            "total": self.total_rows,
            "created": self.created_count,
            "updated": self.updated_count,
            "skipped": self.skipped_count,
            "errors": self.error_count,
        }

    def add_row_detail(
        self,
        row_num: int,
        name: str,
        action: str,
        status: str,
        details: str = "",
        changes: Dict = None,
    ):
        self.row_details.append(
            {
                "row": row_num,
                "name": name,
                "action": action,
                "status": status,
                "details": details,
                "changes": changes or {},
            }
        )
        self.total_rows += 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "created": self.created_count,
            "updated": self.updated_count,
            "skipped": self.skipped_count,
            "errors": self.error_count,
            "error_details": self.errors,
            "warnings": self.warnings,
        }


class PlaceImporter:
    """Import HalalPlace data from JSON or CSV files."""

    # Fields that can be updated
    ALLOWED_FIELDS = [
        "name",
        "description",
        "category",
        "address",
        "phone_number",
        "website",
        "google_map_link",
        "kakao_map_link",
        "naver_map_link",
        "latitude",
        "longitude",
        "photo_urls",
        "status",
        "temporary_closure_until",
        "temporary_closure_reason",
    ]

    # Valid categories
    VALID_CATEGORIES = [choice[0] for choice in HalalPlace.CATEGORY_CHOICES]
    VALID_STATUSES = [choice[0] for choice in HalalPlace.STATUS_CHOICES]

    def __init__(self, user=None, dry_run=False, update_existing=True):
        """
        Initialize importer.

        Args:
            user: User performing the import (for submitted_by field)
            dry_run: If True, don't actually save to database
            update_existing: If True, update existing places; if False, skip them
        """
        self.user = user
        self.dry_run = dry_run
        self.update_existing = update_existing
        self.result = ImportResult()

    def import_json(self, json_content: str) -> ImportResult:
        """Import places from JSON string."""
        try:
            data = json.loads(json_content)
        except json.JSONDecodeError as e:
            self.result.add_error(0, "json", f"Invalid JSON: {str(e)}")
            return self.result

        # Handle both list and dict (GeoJSON FeatureCollection) formats
        if isinstance(data, dict) and data.get("type") == "FeatureCollection":
            places_data = []
            for feature in data.get("features", []):
                # Get properties from feature
                place_data = feature.get("properties", {}).copy()
                # Extract coordinates from geometry if available
                geometry = feature.get("geometry")
                if geometry and geometry.get("type") == "Point":
                    coordinates = geometry.get("coordinates", [])
                    if len(coordinates) >= 2:
                        # GeoJSON uses [longitude, latitude] order
                        place_data["longitude"] = coordinates[0]
                        place_data["latitude"] = coordinates[1]
                places_data.append(place_data)
        elif isinstance(data, list):
            places_data = data
        elif isinstance(data, dict) and "places" in data:
            places_data = data["places"]
        else:
            self.result.add_error(
                0,
                "json",
                "Unknown JSON structure. Expected list of places or GeoJSON FeatureCollection",
            )
            return self.result

        return self._process_places(places_data)

    def import_csv(self, csv_content: str) -> ImportResult:
        """Import places from CSV string."""
        reader = csv.DictReader(io.StringIO(csv_content))
        places_data = []

        for row_num, row in enumerate(reader, start=2):  # Start at 2 (header is 1)
            try:
                place_data = self._csv_row_to_dict(row, row_num)
                places_data.append(place_data)
            except Exception as e:
                self.result.add_error(row_num, "csv_parse", str(e), dict(row))

        return self._process_places(places_data)

    def _csv_row_to_dict(self, row: Dict[str, str], row_num: int) -> Dict[str, Any]:
        """Convert CSV row to place dictionary."""
        data = {}

        # Basic fields
        for field in [
            "id",
            "name",
            "description",
            "category",
            "status",
            "address",
            "phone_number",
            "website",
            "google_map_link",
            "kakao_map_link",
            "naver_map_link",
            "temporary_closure_reason",
        ]:
            if field in row:
                data[field] = row[field].strip() if row[field] else None

        # Numeric fields
        if row.get("latitude"):
            try:
                data["latitude"] = float(row["latitude"])
            except ValueError:
                raise ValueError(f"Invalid latitude: {row['latitude']}")

        if row.get("longitude"):
            try:
                data["longitude"] = float(row["longitude"])
            except ValueError:
                raise ValueError(f"Invalid longitude: {row['longitude']}")

        # Photo URLs (semicolon-separated in CSV)
        if row.get("photo_urls"):
            data["photo_urls"] = [
                url.strip() for url in row["photo_urls"].split(";") if url.strip()
            ]
        else:
            data["photo_urls"] = []

        # Date fields
        if row.get("temporary_closure_until"):
            try:
                data["temporary_closure_until"] = datetime.strptime(
                    row["temporary_closure_until"], "%Y-%m-%d"
                ).date()
            except ValueError:
                raise ValueError(
                    f"Invalid date format for temporary_closure_until: {row['temporary_closure_until']}"
                )

        return data

    def _process_places(self, places_data: List[Dict[str, Any]]) -> ImportResult:
        """Process list of place dictionaries."""
        for idx, place_data in enumerate(places_data, start=1):
            try:
                self._import_single_place(place_data, idx)
            except Exception as e:
                self.result.add_error(idx, "general", str(e), place_data)

        return self.result

    def _import_single_place(self, data: Dict[str, Any], row_num: int):
        """Import or update a single place."""
        name = data.get("name", "")

        # Validate required fields
        if not data.get("name"):
            self.result.add_error(row_num, "name", "Name is required", data)
            self.result.add_row_detail(
                row_num, name, "validate", "error", "Name is required"
            )
            return

        if not data.get("address"):
            self.result.add_error(row_num, "address", "Address is required", data)
            self.result.add_row_detail(
                row_num, name, "validate", "error", "Address is required"
            )
            return

        # Validate category
        category = data.get("category", "restaurant")
        if category not in self.VALID_CATEGORIES:
            self.result.add_error(
                row_num,
                "category",
                f"Invalid category: {category}. Valid options: {', '.join(self.VALID_CATEGORIES)}",
                data,
            )
            self.result.add_row_detail(
                row_num, name, "validate", "error", f"Invalid category: {category}"
            )
            return

        # Validate status
        status = data.get("status", "pending")
        if status not in self.VALID_STATUSES:
            self.result.add_error(
                row_num,
                "status",
                f"Invalid status: {status}. Valid options: {', '.join(self.VALID_STATUSES)}",
                data,
            )
            self.result.add_row_detail(
                row_num, name, "validate", "error", f"Invalid status: {status}"
            )
            return

        # Check for existing place
        existing = self._find_existing_place(data)

        if existing:
            # Check for changes
            changes = self._get_place_changes(existing, data)

            if not changes:
                # No-op: no changes detected
                self.result.skipped_count += 1
                self.result.add_row_detail(
                    row_num, name, "skip", "no-op", "No changes detected"
                )
                return

            if not self.update_existing:
                self.result.skipped_count += 1
                self.result.add_row_detail(
                    row_num,
                    name,
                    "skip",
                    "skipped",
                    "Update existing disabled",
                    changes,
                )
                return

            # Prepare place data for update
            place_fields = self._prepare_place_data(data)

            if self.dry_run:
                self.result.updated_count += 1
                self.result.add_row_detail(
                    row_num, name, "update", "dry-run", "Would update", changes
                )
                return

            # Save to database
            try:
                with transaction.atomic():
                    for field, value in place_fields.items():
                        setattr(existing, field, value)
                    existing.save()
                    self.result.updated_count += 1
                    self.result.add_row_detail(
                        row_num,
                        name,
                        "update",
                        "success",
                        "Updated successfully",
                        changes,
                    )
            except Exception as e:
                self.result.add_error(row_num, "database", str(e), data)
                self.result.add_row_detail(row_num, name, "update", "error", str(e))

        else:
            # Create new place
            place_fields = self._prepare_place_data(data)

            if self.dry_run:
                self.result.created_count += 1
                self.result.add_row_detail(
                    row_num, name, "create", "dry-run", "Would create"
                )
                return

            # Save to database
            try:
                with transaction.atomic():
                    place = HalalPlace.objects.create(**place_fields)
                    self.result.created_count += 1
                    self.result.add_row_detail(
                        row_num, name, "create", "success", "Created successfully"
                    )
            except Exception as e:
                self.result.add_error(row_num, "database", str(e), data)
                self.result.add_row_detail(row_num, name, "create", "error", str(e))

    def _get_place_changes(
        self, existing: HalalPlace, data: Dict[str, Any]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Compare existing place with new data and return dict of changes.
        Returns: {field: {'old': val, 'new': val}}
        """
        changes = {}
        place_fields = self._prepare_place_data(data)

        # Fields to compare
        comparable_fields = [
            "name",
            "description",
            "category",
            "address",
            "phone_number",
            "website",
            "google_map_link",
            "kakao_map_link",
            "naver_map_link",
            "status",
            "temporary_closure_until",
            "temporary_closure_reason",
        ]

        for field in comparable_fields:
            old_val = getattr(existing, field, None)
            new_val = place_fields.get(field)

            # Normalize None vs empty strings
            old_val = old_val if old_val else None
            new_val = new_val if new_val else None

            # Handle date comparison
            if field == "temporary_closure_until":
                if isinstance(old_val, datetime):
                    old_val = old_val.date()
                if isinstance(new_val, str):
                    try:
                        new_val = datetime.strptime(new_val, "%Y-%m-%d").date()
                    except ValueError:
                        pass

            if old_val != new_val:
                changes[field] = {"old": old_val, "new": new_val}

        # Compare coordinates (rounded to 6 decimal places)
        if existing.location and "location" in place_fields:
            old_lat = round(existing.location.y, 6)
            old_lng = round(existing.location.x, 6)
            new_lat = round(place_fields["location"].y, 6)
            new_lng = round(place_fields["location"].x, 6)

            if old_lat != new_lat or old_lng != new_lng:
                changes["coordinates"] = {
                    "old": {"lat": old_lat, "lng": old_lng},
                    "new": {"lat": new_lat, "lng": new_lng},
                }
        elif (not existing.location) != (
            "location" not in place_fields or not place_fields["location"]
        ):
            changes["coordinates"] = {
                "old": {
                    "lat": round(existing.location.y, 6),
                    "lng": round(existing.location.x, 6),
                }
                if existing.location
                else None,
                "new": {
                    "lat": round(place_fields["location"].y, 6),
                    "lng": round(place_fields["location"].x, 6),
                }
                if place_fields.get("location")
                else None,
            }

        # Compare photo_urls as sets
        old_photos = set(existing.photo_urls or [])
        new_photos = set(place_fields.get("photo_urls") or [])
        if old_photos != new_photos:
            changes["photo_urls"] = {
                "old": sorted(old_photos) if old_photos else None,
                "new": sorted(new_photos) if new_photos else None,
            }

        return changes

    def _find_existing_place(self, data: Dict[str, Any]) -> Optional[HalalPlace]:
        """Find existing place by ID or name+address combination."""
        # Try by ID first
        if data.get("id"):
            try:
                return HalalPlace.objects.get(pk=data["id"])
            except HalalPlace.DoesNotExist:
                pass

        # Try by name and address
        name = data.get("name", "").strip()
        address = data.get("address", "").strip()

        if name and address:
            # Try exact match first
            try:
                return HalalPlace.objects.get(name=name, address=address)
            except HalalPlace.DoesNotExist:
                # Try case-insensitive match
                places = HalalPlace.objects.filter(
                    name__iexact=name, address__iexact=address
                )
                if places.exists():
                    return places.first()

        return None

    def _prepare_place_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare and validate place data for saving."""
        place_data = {}

        # Copy allowed fields
        for field in self.ALLOWED_FIELDS:
            if field in data:
                place_data[field] = data[field]

        # Set defaults
        if "status" not in place_data:
            place_data["status"] = "pending"
        if "category" not in place_data:
            place_data["category"] = "restaurant"

        # Handle location (convert lat/lng to Point)
        latitude = data.get("latitude")
        longitude = data.get("longitude")
        if latitude is not None and longitude is not None:
            try:
                place_data["location"] = Point(
                    float(longitude), float(latitude), srid=4326
                )
            except (ValueError, TypeError) as e:
                raise ValueError(
                    f"Invalid coordinates: lat={latitude}, lng={longitude}"
                )

        # Remove lat/lng from place_data since they're not model fields
        # (they're converted to location Point above)
        place_data.pop("latitude", None)
        place_data.pop("longitude", None)

        # Set submitted_by
        if self.user:
            place_data["submitted_by"] = self.user

        # Validate photo URLs
        if "photo_urls" in place_data and place_data["photo_urls"]:
            validated_urls = []
            for url in place_data["photo_urls"]:
                url = url.strip()
                if url and (
                    url.startswith("http://")
                    or url.startswith("https://")
                    or url.startswith("/")
                ):
                    validated_urls.append(url)
            place_data["photo_urls"] = validated_urls if validated_urls else None

        return place_data

    def validate_file(
        self, file_content: str, file_format: str
    ) -> Tuple[bool, List[str]]:
        """
        Validate import file without importing.

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        if file_format == "json":
            try:
                data = json.loads(file_content)
                if isinstance(data, dict) and data.get("type") == "FeatureCollection":
                    places = [f["properties"] for f in data.get("features", [])]
                elif isinstance(data, list):
                    places = data
                else:
                    errors.append(
                        "JSON must be a list of places or a GeoJSON FeatureCollection"
                    )
                    return False, errors
            except json.JSONDecodeError as e:
                errors.append(f"Invalid JSON: {str(e)}")
                return False, errors

        elif file_format == "csv":
            try:
                reader = csv.DictReader(io.StringIO(file_content))
                places = list(reader)
                if not places:
                    errors.append("CSV file is empty or has no data rows")
                    return False, errors
            except Exception as e:
                errors.append(f"Invalid CSV: {str(e)}")
                return False, errors

        else:
            errors.append(f"Unsupported file format: {file_format}")
            return False, errors

        # Validate each place
        for idx, place in enumerate(places, start=1):
            if not place.get("name"):
                errors.append(f"Row {idx}: Missing required field 'name'")
            if not place.get("address"):
                errors.append(f"Row {idx}: Missing required field 'address'")

            if "category" in place and place["category"] not in self.VALID_CATEGORIES:
                errors.append(f"Row {idx}: Invalid category '{place['category']}'")

            if "status" in place and place["status"] not in self.VALID_STATUSES:
                errors.append(f"Row {idx}: Invalid status '{place['status']}'")

        is_valid = len(errors) == 0
        return is_valid, errors
