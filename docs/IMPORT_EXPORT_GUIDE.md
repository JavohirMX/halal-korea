# Data Import/Export Guide

This guide explains how to use the data import and export features in the Halal Korea admin panel.

## Overview

The Data Management system allows administrators to import and export HalalPlace data in multiple formats:
- **JSON**: Complete data with nested business hours
- **CSV**: Spreadsheet format with flattened data
- **Excel**: Formatted spreadsheet with styled headers
- **GeoJSON**: Geographic data for mapping applications

## Accessing Data Management

Navigate to **Admin Panel** → **Data Management** from the top menu or Quick Actions on the Monitoring Dashboard.

## Exporting Data

### From Data Management Page

1. Go to `/admin/places/data-management/`
2. Select the desired format from the **Quick Export** section
3. Click the export button
4. The file will download automatically

### Export Formats

| Format | Extension | Best For |
|--------|-----------|----------|
| JSON | `.json` | Complete data backup, API integration |
| CSV | `.csv` | Spreadsheet editing, data analysis |
| Excel | `.xlsx` | Formatted reports, sharing with non-technical users |
| GeoJSON | `.geojson` | Geographic mapping, GIS applications |

### From Admin List View

1. Go to **Places** → **Halal Places** in the admin
2. Select places using the checkboxes (or select all)
3. Choose an export action from the **Action** dropdown:
   - 📄 Export selected to JSON
   - 📋 Export selected to CSV
   - 📊 Export selected to Excel
   - 🗺️ Export selected to GeoJSON
4. Click **Go** to download the file

## Importing Data

### Supported Formats

- **JSON**: Array of place objects or GeoJSON FeatureCollection
- **CSV**: Comma-separated values with header row

### Required Fields

Every place must have at least:
- `name`: Place name
- `address`: Physical address

### Optional Fields

- `category`: restaurant, market, mosque, prayer_room (default: restaurant)
- `description`: Place description
- `phone_number`: Contact phone
- `website`: Website URL
- `google_map_link`: Google Maps URL
- `kakao_map_link`: Kakao Map URL
- `naver_map_link`: Naver Map URL
- `latitude`: GPS latitude coordinate
- `longitude`: GPS longitude coordinate
- `photo_urls`: Array of photo URLs (JSON) or semicolon-separated (CSV)
- `status`: pending, approved, rejected, archived (default: pending)
- `temporary_closure_until`: Date in YYYY-MM-DD format
- `temporary_closure_reason`: Reason for temporary closure

### Import Process

1. Go to `/admin/places/data-management/`
2. Select the file format (JSON or CSV)
3. Choose import options:
   - **Dry Run**: Validate without saving
   - **Update Existing**: Update places with matching name/address
4. Upload your file or paste content
5. Review the preview
6. Click **Import Data**

### CSV Format Example

```csv
id,name,description,category,status,address,phone_number,website,google_map_link,kakao_map_link,naver_map_link,latitude,longitude,photo_urls
1,Example Restaurant,A great halal restaurant,restaurant,approved,123 Seoul St,02-123-4567,https://example.com,https://goo.gl/maps/...,https://map.kakao.com/...,https://map.naver.com/...,37.5665,126.9780,https://example.com/photo1.jpg;https://example.com/photo2.jpg
```

### JSON Format Example

```json
[
  {
    "name": "Example Restaurant",
    "description": "A great halal restaurant",
    "category": "restaurant",
    "status": "approved",
    "address": "123 Seoul St",
    "phone_number": "02-123-4567",
    "website": "https://example.com",
    "google_map_link": "https://goo.gl/maps/...",
    "kakao_map_link": "https://map.kakao.com/...",
    "naver_map_link": "https://map.naver.com/...",
    "latitude": 37.5665,
    "longitude": 126.9780,
    "photo_urls": [
      "https://example.com/photo1.jpg",
      "https://example.com/photo2.jpg"
    ]
  }
]
```

### GeoJSON Format Example

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "Point",
        "coordinates": [126.9780, 37.5665]
      },
      "properties": {
        "name": "Example Restaurant",
        "address": "123 Seoul St",
        "category": "restaurant"
      }
    }
  ]
}
```

## Duplicate Detection

The import system automatically detects duplicates by:

1. **ID Match**: If an `id` field is provided and exists in the database
2. **Name + Address Match**: Case-insensitive match on both name and address

When duplicates are found:
- If **Update Existing** is enabled: The existing record will be updated
- If **Update Existing** is disabled: The record will be skipped

## Validation

The system validates:

- **Required fields**: Name and address must be present
- **Category**: Must be one of: restaurant, market, mosque, prayer_room
- **Status**: Must be one of: pending, approved, rejected, archived
- **Coordinates**: Latitude must be between -90 and 90, longitude between -180 and 180
- **Photo URLs**: Must be valid HTTP/HTTPS URLs or relative paths
- **Dates**: Must be in YYYY-MM-DD format

## Import Results

After importing, you'll see a summary:

- **Created**: Number of new places added
- **Updated**: Number of existing places modified
- **Skipped**: Number of duplicates skipped (when update_existing=False)
- **Errors**: Number of failed records with details

## Best Practices

### Before Importing

1. **Always validate first**: Use Dry Run mode to check for errors
2. **Backup your data**: Export existing data before bulk imports
3. **Test with small batches**: Import a few records first to verify format
4. **Check coordinates**: Ensure latitude/longitude are correct (lat: -90 to 90, lng: -180 to 180)

### Data Preparation

1. **Clean your data**: Remove empty rows and fix formatting issues
2. **Standardize addresses**: Use consistent address formats
3. **Validate URLs**: Ensure all website and photo URLs are accessible
4. **Check categories**: Use valid category codes only

### After Importing

1. **Review imported data**: Check a few records in the admin
2. **Verify locations**: Confirm map coordinates display correctly
3. **Check photos**: Ensure photo URLs are loading properly
4. **Update status**: Change status from "pending" to "approved" after review

## Troubleshooting

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| "Name is required" | Missing name field | Add name to all records |
| "Invalid category" | Unknown category value | Use: restaurant, market, mosque, prayer_room |
| "Invalid JSON" | Malformed JSON | Validate JSON syntax |
| "Invalid CSV" | Malformed CSV | Check for unescaped commas or quotes |
| "Invalid coordinates" | Out of range lat/lng | Ensure lat: -90 to 90, lng: -180 to 180 |

### Getting Help

If you encounter issues:

1. Check the error messages in the import results
2. Review the sample formats above
3. Try importing a single record first
4. Use Dry Run mode to validate without saving
5. Export existing data to see the expected format

## Tips for Different Use Cases

### Bulk Adding New Places

1. Prepare your data in Excel or Google Sheets
2. Export as CSV
3. Use the import tool with "Update Existing" enabled
4. Review and approve the imported places

### Migrating from Another System

1. Export data from your existing system
2. Map fields to Halal Korea format
3. Use Dry Run to validate
4. Import in batches of 100-200 records

### Creating Backups

1. Export to JSON for complete data preservation
2. Export to Excel for human-readable backups
3. Store backups securely
4. Test restoring from backup periodically

### Sharing Data

1. Use CSV for easy sharing and editing
2. Use GeoJSON for mapping applications
3. Use Excel for presentations and reports
4. Use JSON for API integrations

## API Integration

The export data can be used with external systems:

- **GeoJSON**: Import into Google Maps, Mapbox, or QGIS
- **JSON**: Parse with any programming language
- **CSV**: Open in Excel, Google Sheets, or data analysis tools
- **Excel**: Share with team members for review

## Security Notes

- Only staff/superuser accounts can access Data Management
- All imports are logged in the admin action log
- Photo URLs are validated for security
- Import operations can be monitored in the admin dashboard
