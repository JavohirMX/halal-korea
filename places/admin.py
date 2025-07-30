from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from django.contrib import messages
from django.contrib.gis.geos import Point
from django.db.models import Count, Q
from django.urls import path
from django.http import HttpResponse, JsonResponse
from django.template.response import TemplateResponse
from django.shortcuts import get_object_or_404
from django.utils.safestring import mark_safe
from django.forms import ModelForm, CharField, Textarea
from django.core.exceptions import ValidationError
import json
import logging

from .models import HalalPlace, PlaceEditSuggestion, PlaceImageSuggestion

logger = logging.getLogger(__name__)


# Custom admin filters
class StatusFilter(admin.SimpleListFilter):
    title = 'Status'
    parameter_name = 'status'

    def lookups(self, request, model_admin):
        return (
            ('pending', 'Pending Review'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
            ('archived', 'Archived'),
            ('with_suggestions', 'Has Pending Suggestions'),
            ('popular', 'Popular (Has Reviews)'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'with_suggestions':
            return queryset.filter(edit_suggestions__status='pending').distinct()
        elif self.value() == 'popular':
            return queryset.annotate(review_count=Count('reviews')).filter(review_count__gt=0)
        elif self.value():
            return queryset.filter(status=self.value())
        return queryset


class CategoryFilter(admin.SimpleListFilter):
    title = 'Category'
    parameter_name = 'category'

    def lookups(self, request, model_admin):
        return HalalPlace.CATEGORY_CHOICES + [
            ('with_images', 'Has Images'),
            ('no_images', 'No Images'),
        ]

    def queryset(self, request, queryset):
        if self.value() == 'with_images':
            return queryset.exclude(Q(photo_urls__isnull=True) | Q(photo_urls=[]))
        elif self.value() == 'no_images':
            return queryset.filter(Q(photo_urls__isnull=True) | Q(photo_urls=[]))
        elif self.value():
            return queryset.filter(category=self.value())
        return queryset


# Custom form for HalalPlace with enhanced image management
class HalalPlaceAdminForm(ModelForm):
    image_management = CharField(
        required=False,
        widget=Textarea(attrs={
            'style': 'display: none;',
            'id': 'image-management-field'
        }),
        help_text="Advanced image management interface"
    )

    class Meta:
        model = HalalPlace
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            # Populate image management field with current photos
            if self.instance.photo_urls:
                self.fields['image_management'].initial = json.dumps(self.instance.photo_urls)

    def clean_photo_urls(self):
        photo_urls = self.cleaned_data.get('photo_urls')
        if photo_urls:
            # Validate each URL
            for url in photo_urls:
                if url and not url.startswith(('http://', 'https://', '/')):
                    raise ValidationError(f"Invalid URL format: {url}")
        return photo_urls


@admin.register(HalalPlace)
class HalalPlaceAdmin(admin.ModelAdmin):
    form = HalalPlaceAdminForm
    list_display = (
        'name_with_link', 'category_icon', 'status', 'location_display', 
        'image_count', 'suggestion_count', 'submitted_by', 'created_at'
    )
    list_filter = (StatusFilter, CategoryFilter, 'submitted_by', 'created_at', 'updated_at')
    search_fields = ('name', 'description', 'address', 'submitted_by__username')
    readonly_fields = ('created_at', 'updated_at', 'image_preview_grid', 'suggestion_summary', 'location_map', 'status_badge')
    list_editable = ('status',)
    list_per_page = 25
    ordering = ('-created_at',)
    
    actions = [
        'bulk_approve', 'bulk_archive', 'bulk_reject', 'bulk_set_pending',
        'export_selected', 'validate_images', 'generate_stats'
    ]

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'category', 'status', 'status_badge')
        }),
        ('Location', {
            'fields': ('address', 'location', 'location_map'),
            'classes': ('wide',)
        }),
        ('Contact Information', {
            'fields': ('phone_number', 'website'),
            'classes': ('collapse',)
        }),
        ('Map Links', {
            'fields': ('google_map_link', 'kakao_map_link', 'naver_map_link'),
            'classes': ('collapse',)
        }),
        ('Images', {
            'fields': ('photo_urls', 'image_preview_grid', 'image_management'),
            'classes': ('wide',)
        }),
        ('Metadata', {
            'fields': ('submitted_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
        ('Suggestions', {
            'fields': ('suggestion_summary',),
            'classes': ('collapse',)
        })
    )

    class Media:
        css = {
            'all': ('admin/css/enhanced_admin.css',)
        }
        js = ('admin/js/enhanced_admin.js', 'admin/js/image_management.js')

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('image-manager/<int:place_id>/', self.admin_site.admin_view(self.image_manager_view), name='places_halalplace_image_manager'),
            path('bulk-stats/', self.admin_site.admin_view(self.bulk_stats_view), name='places_halalplace_bulk_stats'),
        ]
        return custom_urls + urls

    # Custom display methods
    def name_with_link(self, obj):
        url = f"/admin/places/halalplace/{obj.pk}/change/"
        return format_html('<a href="{}" style="font-weight: bold; color: #0066cc;">{}</a>', url, obj.name)
    name_with_link.short_description = "Name"
    name_with_link.admin_order_field = "name"

    def category_icon(self, obj):
        icons = {
            'restaurant': '🍽️',
            'market': '🛒',
            'mosque': '🕌',
            'prayer_room': '🤲'
        }
        icon = icons.get(obj.category, '📍')
        return format_html(
            '<span style="font-size: 18px; margin-right: 5px;">{}</span>{}',
            icon, obj.get_category_display()
        )
    category_icon.short_description = "Category"
    category_icon.admin_order_field = "category"

    def status_badge(self, obj):
        colors = {
            'pending': '#fbbf24',
            'approved': '#10b981',
            'rejected': '#ef4444',
            'archived': '#6b7280'
        }
        color = colors.get(obj.status, '#6b7280')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 4px 8px; border-radius: 12px; font-size: 11px; font-weight: bold;">{}</span>',
            color, obj.get_status_display().upper()
        )
    status_badge.short_description = "Status"
    status_badge.admin_order_field = "status"

    def location_display(self, obj):
        if obj.location:
            lat, lng = obj.location.y, obj.location.x
            address_display = obj.address[:30] + '...' if len(obj.address) > 30 else obj.address
            return format_html(
                '<div style="font-size: 11px;"><strong>📍</strong> {}, {}<br/><span style="color: #666;">{}</span></div>',
                round(lat, 4), round(lng, 4), address_display
            )
        return format_html('<span style="color: #999;">No location</span>')
    location_display.short_description = "Location"

    def image_count(self, obj):
        count = len(obj.photo_urls) if obj.photo_urls else 0
        if count > 0:
            return format_html(
                '<div style="text-align: center;"><strong style="color: #059669; font-size: 16px;">{}</strong><br/><span style="font-size: 10px; color: #666;">images</span></div>',
                count
            )
        return format_html('<span style="color: #999;">No images</span>')
    image_count.short_description = "Images"

    def suggestion_count(self, obj):
        pending = obj.edit_suggestions.filter(status='pending').count()
        approved = obj.edit_suggestions.filter(status='approved').count()
        if pending > 0:
            return format_html(
                '<div style="text-align: center;"><strong style="color: #dc2626;">{}</strong> pending<br/><span style="font-size: 10px; color: #666;">{} approved</span></div>',
                pending, approved
            )
        elif approved > 0:
            return format_html(
                '<div style="text-align: center;"><span style="color: #059669;">{} approved</span></div>',
                approved
            )
        return format_html('<span style="color: #999;">No suggestions</span>')
    suggestion_count.short_description = "Suggestions"

    def image_preview_grid(self, obj):
        if not obj.photo_urls:
            return format_html('<p style="color: #666; font-style: italic;">No images uploaded</p>')
        
        html_parts = ['<div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(120px, 1fr)); gap: 10px; max-width: 600px;">']
        
        for i, url in enumerate(obj.photo_urls[:8]):  # Show max 8 images
            html_parts.append(
                f'<div style="position: relative; border: 1px solid #ddd; border-radius: 8px; overflow: hidden;">'
                f'<img src="{url}" style="width: 100%; height: 80px; object-fit: cover;" alt="Image {i+1}" />'
                f'<div style="position: absolute; top: 2px; left: 2px; background: rgba(0,0,0,0.7); color: white; padding: 2px 6px; border-radius: 4px; font-size: 10px;">{i+1}</div>'
                f'</div>'
            )
        
        if len(obj.photo_urls) > 8:
            html_parts.append(
                f'<div style="display: flex; align-items: center; justify-content: center; background: #f3f4f6; border: 1px solid #ddd; border-radius: 8px; height: 80px; color: #666; font-size: 12px;">+{len(obj.photo_urls) - 8} more</div>'
            )
        
        html_parts.append('</div>')
        html_parts.append(f'<p style="margin-top: 10px;"><a href="/admin/places/halalplace/image-manager/{obj.pk}/" style="background: #0066cc; color: white; padding: 6px 12px; border-radius: 4px; text-decoration: none; font-size: 12px;">🖼️ Manage Images</a></p>')
        
        return format_html(''.join(html_parts))
    image_preview_grid.short_description = "Image Gallery"

    def suggestion_summary(self, obj):
        suggestions = obj.edit_suggestions.all()
        if not suggestions:
            return format_html('<p style="color: #666; font-style: italic;">No suggestions</p>')
        
        pending = suggestions.filter(status='pending')
        approved = suggestions.filter(status='approved')
        rejected = suggestions.filter(status='rejected')
        
        html = '<div style="font-size: 12px;">'
        if pending:
            html += f'<div style="margin-bottom: 5px;"><strong style="color: #dc2626;">⏳ {pending.count()} Pending:</strong>'
            for suggestion in pending[:3]:
                html += f'<br/>• {suggestion.get_field_name_display()} by {suggestion.suggested_by.username}'
            if pending.count() > 3:
                html += f'<br/>• ... and {pending.count() - 3} more'
            html += '</div>'
        
        if approved:
            html += f'<div style="color: #059669;">✅ {approved.count()} Approved</div>'
        if rejected:
            html += f'<div style="color: #dc2626;">❌ {rejected.count()} Rejected</div>'
        
        html += '</div>'
        return format_html(html)
    suggestion_summary.short_description = "Suggestion Summary"

    def location_map(self, obj):
        if obj.location:
            lat, lng = obj.location.y, obj.location.x
            return format_html(
                '<div style="text-align: center;">'
                '<iframe src="https://maps.google.com/maps?q={},{}&z=15&output=embed" '
                'width="300" height="200" style="border: 1px solid #ddd; border-radius: 8px;"></iframe>'
                '<p style="margin-top: 5px; font-size: 11px; color: #666;">Lat: {}, Lng: {}</p>'
                '</div>',
                lat, lng, round(lat, 6), round(lng, 6)
            )
        return format_html('<p style="color: #666; font-style: italic;">No location set</p>')
    location_map.short_description = "Map Preview"

    # Bulk action methods
    def bulk_approve(self, request, queryset):
        updated = queryset.update(status='approved')
        self.message_user(request, f'Successfully approved {updated} place(s).')
    bulk_approve.short_description = "✅ Approve selected places"

    def bulk_archive(self, request, queryset):
        updated = queryset.update(status='archived')
        self.message_user(request, f'Successfully archived {updated} place(s).')
    bulk_archive.short_description = "📦 Archive selected places"

    def bulk_reject(self, request, queryset):
        updated = queryset.update(status='rejected')
        self.message_user(request, f'Successfully rejected {updated} place(s).')
    bulk_reject.short_description = "❌ Reject selected places"

    def bulk_set_pending(self, request, queryset):
        updated = queryset.update(status='pending')
        self.message_user(request, f'Successfully set {updated} place(s) to pending.')
    bulk_set_pending.short_description = "⏳ Set to pending review"

    def export_selected(self, request, queryset):
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="halal_places_export.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Name', 'Category', 'Status', 'Address', 'Phone', 'Website',
            'Latitude', 'Longitude', 'Image Count', 'Created At', 'Submitted By'
        ])
        
        for place in queryset:
            lat, lng = (place.location.y, place.location.x) if place.location else ('', '')
            image_count = len(place.photo_urls) if place.photo_urls else 0
            
            writer.writerow([
                place.name, place.get_category_display(), place.get_status_display(),
                place.address, place.phone_number or '', place.website or '',
                lat, lng, image_count, place.created_at.strftime('%Y-%m-%d'),
                place.submitted_by.username if place.submitted_by else ''
            ])
        
        return response
    export_selected.short_description = "📊 Export selected to CSV"

    def validate_images(self, request, queryset):
        validated_count = 0
        error_count = 0
        
        for place in queryset:
            if place.photo_urls:
                valid_urls = []
                for url in place.photo_urls:
                    try:
                        # Basic URL validation - you could add more sophisticated checks
                        if url and (url.startswith(('http://', 'https://')) or url.startswith('/')):
                            valid_urls.append(url)
                        else:
                            error_count += 1
                    except Exception:
                        error_count += 1
                
                if len(valid_urls) != len(place.photo_urls):
                    place.photo_urls = valid_urls
                    place.save()
                    validated_count += 1
        
        if validated_count:
            self.message_user(request, f'Validated images for {validated_count} places. Removed {error_count} invalid URLs.')
        else:
            self.message_user(request, 'All image URLs are valid.')
    validate_images.short_description = "🔍 Validate image URLs"

    def generate_stats(self, request, queryset):
        stats = {
            'total': queryset.count(),
            'by_status': {},
            'by_category': {},
            'with_images': 0,
            'with_suggestions': 0
        }
        
        for status_choice in HalalPlace.STATUS_CHOICES:
            count = queryset.filter(status=status_choice[0]).count()
            stats['by_status'][status_choice[1]] = count
        
        for category_choice in HalalPlace.CATEGORY_CHOICES:
            count = queryset.filter(category=category_choice[0]).count()
            stats['by_category'][category_choice[1]] = count
        
        stats['with_images'] = queryset.exclude(Q(photo_urls__isnull=True) | Q(photo_urls=[])).count()
        stats['with_suggestions'] = queryset.filter(edit_suggestions__status='pending').distinct().count()
        
        messages.success(request, f"Generated stats for {stats['total']} places. Check the detailed breakdown in the response.")
        
        # Store stats in session for the bulk stats view
        request.session['bulk_stats'] = stats
        return HttpResponse(f"""
            <h3>Statistics for Selected Places</h3>
            <p><strong>Total:</strong> {stats['total']}</p>
            <h4>By Status:</h4>
            <ul>{''.join([f'<li>{k}: {v}</li>' for k, v in stats['by_status'].items()])}</ul>
            <h4>By Category:</h4>
            <ul>{''.join([f'<li>{k}: {v}</li>' for k, v in stats['by_category'].items()])}</ul>
            <p><strong>With Images:</strong> {stats['with_images']}</p>
            <p><strong>With Pending Suggestions:</strong> {stats['with_suggestions']}</p>
            <p><a href="javascript:window.close()">Close Window</a></p>
        """)
    generate_stats.short_description = "📈 Generate statistics"

    # Custom admin views
    def image_manager_view(self, request, place_id):
        place = get_object_or_404(HalalPlace, pk=place_id)
        
        if request.method == 'POST':
            import json
            data = json.loads(request.body)
            
            if data.get('action') == 'reorder':
                place.photo_urls = data.get('urls', [])
                place.save()
                return JsonResponse({'success': True})
            
            elif data.get('action') == 'delete':
                url_to_delete = data.get('url')
                if url_to_delete and place.photo_urls:
                    place.photo_urls = [url for url in place.photo_urls if url != url_to_delete]
                    place.save()
                    return JsonResponse({'success': True})
            
            elif data.get('action') == 'add':
                new_url = data.get('url')
                if new_url:
                    if not place.photo_urls:
                        place.photo_urls = []
                    place.photo_urls.append(new_url)
                    place.save()
                    return JsonResponse({'success': True})
        
        context = {
            'place': place,
            'photo_urls': place.photo_urls or [],
            'title': f'Image Manager - {place.name}',
            'opts': self.model._meta,
        }
        
        return TemplateResponse(request, 'admin/places/image_manager.html', context)

    def bulk_stats_view(self, request):
        context = {
            'title': 'Bulk Statistics',
            'opts': self.model._meta,
            'stats': request.session.get('bulk_stats', {}),
        }
        return TemplateResponse(request, 'admin/places/bulk_stats.html', context)


@admin.register(PlaceEditSuggestion)
class PlaceEditSuggestionAdmin(admin.ModelAdmin):
    list_display = ('place', 'field_name', 'suggested_by', 'status', 'created_at', 'reviewed_by')
    list_filter = ('status', 'field_name', 'created_at')
    search_fields = ('place__name', 'suggested_by__username', 'reason')
    readonly_fields = ('created_at', 'current_value_display', 'suggested_value_display')
    raw_id_fields = ('place', 'suggested_by', 'reviewed_by')
    fieldsets = (
        ('Suggestion Info', {
            'fields': ('place', 'suggested_by', 'field_name', 'reason')
        }),
        ('Values', {
            'fields': ('current_value_display', 'suggested_value_display')
        }),
        ('Review', {
            'fields': ('status', 'admin_notes', 'reviewed_by', 'reviewed_at')
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        })
    )
    actions = ['approve_suggestions', 'reject_suggestions']

    def current_value_display(self, obj):
        if obj.current_value:
            return format_html('<div style="background-color: #fff2cc; padding: 10px; border-radius: 4px;"><strong>Current:</strong><br>{}</div>', obj.current_value)
        return "No current value"
    current_value_display.short_description = "Current Value"

    def suggested_value_display(self, obj):
        return format_html('<div style="background-color: #d4edda; padding: 10px; border-radius: 4px;"><strong>Suggested:</strong><br>{}</div>', obj.suggested_value)
    suggested_value_display.short_description = "Suggested Value"

    def approve_suggestions(self, request, queryset):
        approved_count = 0
        failed_count = 0
        
        for suggestion in queryset.filter(status='pending'):
            if self._apply_suggestion(suggestion, request.user):
                suggestion.status = 'approved'
                suggestion.reviewed_by = request.user
                suggestion.reviewed_at = timezone.now()
                suggestion.save()
                approved_count += 1
            else:
                failed_count += 1
                # Keep the suggestion as pending but add admin notes
                suggestion.admin_notes = f"Failed to apply automatically. Please review manually."
                suggestion.save()
        
        if approved_count:
            messages.success(request, f'Successfully approved and applied {approved_count} suggestion(s)')
        if failed_count:
            messages.error(request, f'{failed_count} suggestion(s) failed to apply. Check logs and admin notes for details.')
    approve_suggestions.short_description = "Approve selected suggestions"

    def reject_suggestions(self, request, queryset):
        rejected_count = 0
        for suggestion in queryset.filter(status='pending'):
            suggestion.status = 'rejected'
            suggestion.reviewed_by = request.user
            suggestion.reviewed_at = timezone.now()
            suggestion.save()
            rejected_count += 1
        
        if rejected_count:
            messages.success(request, f'Successfully rejected {rejected_count} suggestion(s)')
    reject_suggestions.short_description = "Reject selected suggestions"

    def _apply_suggestion(self, suggestion, reviewer):
        """Apply an approved suggestion to the place"""
        try:
            from django.contrib import messages
            import logging
            logger = logging.getLogger(__name__)
            
            place = suggestion.place
            field_name = suggestion.field_name
            new_value = suggestion.suggested_value
            
            logger.info(f"Applying suggestion: {field_name} = '{new_value}' for place '{place.name}' (ID: {place.pk})")

            # Handle location field specially (convert string to Point)
            if field_name == 'location':
                # Expect format like "lat,lng" or "(lat, lng)"
                import re
                coords = re.findall(r'-?\d+\.?\d*', new_value)
                if len(coords) >= 2:
                    lat, lng = float(coords[0]), float(coords[1])
                    new_value = Point(lng, lat, srid=4326)
                    logger.info(f"Converted location string to Point: {new_value}")
                else:
                    logger.error(f"Invalid location format: '{new_value}'. Expected 'lat,lng' format")
                    return False
            
            # Handle category field (validate against choices)
            elif field_name == 'category':
                valid_categories = [choice[0] for choice in HalalPlace.CATEGORY_CHOICES]
                if new_value not in valid_categories:
                    logger.error(f"Invalid category: '{new_value}'. Valid choices: {valid_categories}")
                    return False

            # Store old value for logging
            old_value = getattr(place, field_name)
            
            # Apply the change
            setattr(place, field_name, new_value)
            place.save()
            
            logger.info(f"Successfully applied suggestion: '{old_value}' -> '{new_value}' for {field_name}")
            return True
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error applying suggestion {suggestion.pk}: {str(e)}", exc_info=True)
            return False


@admin.register(PlaceImageSuggestion)
class PlaceImageSuggestionAdmin(admin.ModelAdmin):
    list_display = ('place', 'suggested_by', 'status', 'created_at', 'reviewed_by', 'image_preview')
    list_filter = ('status', 'created_at')
    search_fields = ('place__name', 'suggested_by__username', 'caption')
    readonly_fields = ('created_at', 'image_preview')
    raw_id_fields = ('place', 'suggested_by', 'reviewed_by')
    fieldsets = (
        ('Suggestion Info', {
            'fields': ('place', 'suggested_by', 'image', 'caption')
        }),
        ('Preview', {
            'fields': ('image_preview',)
        }),
        ('Review', {
            'fields': ('status', 'admin_notes', 'reviewed_by', 'reviewed_at')
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        })
    )
    actions = ['approve_image_suggestions', 'reject_image_suggestions']

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-width: 300px; max-height: 200px; border-radius: 4px;">', obj.image.url)
        return "No image"
    image_preview.short_description = "Image Preview"

    def approve_image_suggestions(self, request, queryset):
        approved_count = 0
        failed_count = 0
        
        for suggestion in queryset.filter(status='pending'):
            if self._apply_image_suggestion(suggestion, request.user):
                suggestion.status = 'approved'
                suggestion.reviewed_by = request.user
                suggestion.reviewed_at = timezone.now()
                suggestion.save()
                approved_count += 1
            else:
                failed_count += 1
                # Keep the suggestion as pending but add admin notes
                suggestion.admin_notes = f"Failed to apply automatically. Please review manually."
                suggestion.save()
        
        if approved_count:
            messages.success(request, f'Successfully approved and applied {approved_count} image suggestion(s)')
        if failed_count:
            messages.error(request, f'{failed_count} image suggestion(s) failed to apply. Check logs and admin notes for details.')
    approve_image_suggestions.short_description = "Approve selected image suggestions"

    def reject_image_suggestions(self, request, queryset):
        rejected_count = 0
        for suggestion in queryset.filter(status='pending'):
            suggestion.status = 'rejected'
            suggestion.reviewed_by = request.user
            suggestion.reviewed_at = timezone.now()
            suggestion.save()
            rejected_count += 1
        
        if rejected_count:
            messages.success(request, f'Successfully rejected {rejected_count} image suggestion(s)')
    reject_image_suggestions.short_description = "Reject selected image suggestions"

    def _apply_image_suggestion(self, suggestion, reviewer):
        """Apply an approved image suggestion to the place"""
        try:
            import logging
            logger = logging.getLogger(__name__)
            
            place = suggestion.place
            image_url = suggestion.image.url
            
            logger.info(f"Applying image suggestion for place '{place.name}' (ID: {place.pk}): {image_url}")
            
            # Add to the place's photo_urls array
            if place.photo_urls is None:
                place.photo_urls = []
                logger.info(f"Initialized empty photo_urls array for place {place.pk}")
            
            # Check if image URL already exists to avoid duplicates
            if image_url in place.photo_urls:
                logger.warning(f"Image URL already exists in place photos: {image_url}")
                return True  # Consider this a success since the image is already there
            
            # Add the new image URL to the array
            place.photo_urls.append(image_url)
            place.save()
            
            logger.info(f"Successfully added image to place {place.pk}. Total photos: {len(place.photo_urls)}")
            return True
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error applying image suggestion {suggestion.pk}: {str(e)}", exc_info=True)
            return False
