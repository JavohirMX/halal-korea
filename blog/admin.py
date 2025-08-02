from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
import logging

from .models import BlogPost, Category, Tag, RelatedPlace

logger = logging.getLogger(__name__)


class RelatedPlaceInline(admin.TabularInline):
    """Inline admin for related places"""
    model = RelatedPlace
    extra = 1
    autocomplete_fields = ['place']


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'post_count', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('created_at',)
    
    def post_count(self, obj):
        return obj.posts.filter(status='published').count()
    post_count.short_description = 'Published Posts'


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'post_count')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}
    
    def post_count(self, obj):
        return obj.posts.filter(status='published').count()
    post_count.short_description = 'Published Posts'


@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = (
        'title', 'author', 'category', 'status', 'language', 
        'view_count', 'published_at', 'created_at'
    )
    list_filter = (
        'status', 'language', 'category', 'created_at', 
        'published_at', 'author'
    )
    search_fields = ('title', 'excerpt', 'content')
    prepopulated_fields = {'slug': ('title',)}
    filter_horizontal = ('tags',)
    readonly_fields = ('view_count', 'created_at', 'updated_at', 'slug_preview')
    inlines = [RelatedPlaceInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'title', 'slug', 'slug_preview', 'author', 'category', 
                'tags', 'status', 'language'
            )
        }),
        ('Content', {
            'fields': ('excerpt', 'content', 'featured_image')
        }),
        ('SEO & Meta', {
            'fields': ('meta_title', 'meta_description'),
            'classes': ('collapse',)
        }),
        ('Publishing', {
            'fields': ('published_at',),
            'classes': ('collapse',)
        }),
        ('Analytics', {
            'fields': ('view_count', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('author', 'category').prefetch_related('tags')
    
    def save_model(self, request, obj, form, change):
        # Set author to current user if creating new post
        if not change:
            obj.author = request.user
        super().save_model(request, obj, form, change)
        
        # Log the action
        action = 'updated' if change else 'created'
        logger.info(f"Blog post '{obj.title}' {action} by admin {request.user.username}")
    
    def slug_preview(self, obj):
        if obj.slug:
            return format_html(
                '<a href="{}" target="_blank" class="button">View Post</a>',
                obj.get_absolute_url()
            )
        return "Save to generate preview link"
    slug_preview.short_description = 'Preview'
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        # Set default author to current user
        if not obj:
            form.base_fields['author'].initial = request.user
        return form
    
    actions = ['make_published', 'make_draft', 'make_archived']
    
    def make_published(self, request, queryset):
        count = 0
        for post in queryset:
            if post.status != 'published':
                post.status = 'published'
                if not post.published_at:
                    post.published_at = timezone.now()
                post.save()
                count += 1
        self.message_user(request, f'{count} posts were successfully published.')
    make_published.short_description = "Mark selected posts as published"
    
    def make_draft(self, request, queryset):
        count = queryset.update(status='draft')
        self.message_user(request, f'{count} posts were moved to draft.')
    make_draft.short_description = "Mark selected posts as draft"
    
    def make_archived(self, request, queryset):
        count = queryset.update(status='archived')
        self.message_user(request, f'{count} posts were archived.')
    make_archived.short_description = "Mark selected posts as archived"


@admin.register(RelatedPlace)
class RelatedPlaceAdmin(admin.ModelAdmin):
    list_display = ('blog_post', 'place', 'added_at')
    list_filter = ('added_at', 'blog_post__category')
    search_fields = ('blog_post__title', 'place__name')
    autocomplete_fields = ['blog_post', 'place']
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('blog_post', 'place')
