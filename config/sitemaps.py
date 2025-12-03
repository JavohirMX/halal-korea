# config/sitemaps.py
from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from blog.models import BlogPost
from places.models import HalalPlace


class StaticViewSitemap(Sitemap):
    """Sitemap for static pages"""
    priority = 0.8
    changefreq = 'weekly'
    protocol = 'https'

    def items(self):
        return [
            ('places:home', 1.0),
            ('places:explore', 0.9),
            ('places:about', 0.6),
            ('places:donate', 0.5),
            ('places:submit_place', 0.6),
            ('places:legal', 0.3),
            ('blog:home', 0.7),
            ('prayer_times:prayer_times', 0.8),
        ]

    def location(self, item):
        return reverse(item[0])

    def priority(self, item):
        return item[1]

    def lastmod(self, item):
        # Return None for static pages as they don't have lastmod
        return None


class PlaceSitemap(Sitemap):
    """Sitemap for halal places"""
    changefreq = 'weekly'
    priority = 0.8
    protocol = 'https'
    limit = 1000  # Split sitemap into chunks for large sites

    def items(self):
        return HalalPlace.objects.filter(status='approved').select_related().order_by('-updated_at')

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
