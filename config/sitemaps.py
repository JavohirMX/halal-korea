# config/sitemaps.py
from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from blog.models import BlogPost
from places.models import HalalPlace


class StaticViewSitemap(Sitemap):
    """Sitemap for static pages"""
    priority = 0.8
    changefreq = 'daily'
    protocol = 'https'

    def items(self):
        return [
            'places:home',
            'places:explore', 
            'places:about',
            'places:donate',
            'places:submit_place',
            'places:legal',
            'blog:home',
            'prayer_times:prayer_times',
        ]

    def location(self, item):
        return reverse(item)

    def lastmod(self, item):
        # Return None for static pages as they don't have lastmod
        return None


class PlaceSitemap(Sitemap):
    """Sitemap for halal places"""
    changefreq = 'weekly'
    priority = 0.9
    protocol = 'https'

    def items(self):
        return HalalPlace.objects.filter(status='approved').order_by('-updated_at')

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return obj.get_absolute_url()


class BlogPostSitemap(Sitemap):
    """Sitemap for blog posts"""
    changefreq = 'monthly'
    priority = 0.7
    protocol = 'https'

    def items(self):
        return BlogPost.published.all().order_by('-published_at')

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return obj.get_absolute_url()


# Dictionary of all sitemaps
sitemaps = {
    'static': StaticViewSitemap,
    'places': PlaceSitemap,
    'blog': BlogPostSitemap,
}
