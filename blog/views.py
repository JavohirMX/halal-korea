from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q
from django.http import Http404
import logging

from .models import BlogPost, Category, Tag

logger = logging.getLogger(__name__)


def blog_home(request):
    """Blog home page with latest posts"""
    try:
        # Get current language
        current_language = request.LANGUAGE_CODE or 'en'
        
        # Get published posts for current language
        posts = BlogPost.objects.filter(
            status='published',
            language=current_language
        ).select_related('author', 'category').prefetch_related('tags')
        
        # Get featured post (latest one)
        featured_post = posts.first()
        
        # Get recent posts (excluding featured)
        recent_posts = posts[1:7] if posts.count() > 1 else []
        
        # Pagination for all posts
        paginator = Paginator(posts, 6)
        page = request.GET.get('page', 1)
        
        try:
            posts_page = paginator.page(page)
        except (PageNotAnInteger, EmptyPage):
            posts_page = paginator.page(1)
        
        # Get categories with post counts
        categories = Category.objects.filter(
            posts__status='published',
            posts__language=current_language
        ).distinct().order_by('name')
        
        context = {
            'featured_post': featured_post,
            'recent_posts': recent_posts,
            'posts': posts_page,
            'categories': categories,
            'page_title': 'Blog',
        }
        
        logger.info(f"Blog home page accessed by user: {request.user.username if request.user.is_authenticated else 'anonymous'}")
        return render(request, 'blog/home.html', context)
        
    except Exception as e:
        logger.error(f"Error in blog home view: {str(e)}", exc_info=True)
        return render(request, 'blog/home.html', {
            'posts': [],
            'categories': [],
            'page_title': 'Blog',
        })


def post_detail(request, slug):
    """Individual blog post detail view"""
    try:
        current_language = request.LANGUAGE_CODE or 'en'
        
        post = get_object_or_404(
            BlogPost,
            slug=slug,
            status='published',
            language=current_language
        )
        
        # Increment view count
        post.increment_view_count()
        
        # Get related posts (same category or tags)
        related_posts = BlogPost.objects.filter(
            Q(category=post.category) | Q(tags__in=post.tags.all()),
            status='published',
            language=current_language
        ).exclude(id=post.id).distinct()[:3]
        
        # Get related places
        related_places = post.related_places.select_related('place').all()
        
        context = {
            'post': post,
            'related_posts': related_posts,
            'related_places': related_places,
            'page_title': post.title,
            'meta_title': post.meta_title,
            'meta_description': post.meta_description,
        }
        
        logger.info(f"Blog post '{post.title}' viewed by user: {request.user.username if request.user.is_authenticated else 'anonymous'}")
        return render(request, 'blog/detail.html', context)
        
    except Exception as e:
        logger.error(f"Error in blog post detail view for slug '{slug}': {str(e)}", exc_info=True)
        raise Http404("Blog post not found")


def category_posts(request, slug):
    """Posts filtered by category"""
    try:
        current_language = request.LANGUAGE_CODE or 'en'
        category = get_object_or_404(Category, slug=slug)
        
        posts = BlogPost.objects.filter(
            category=category,
            status='published',
            language=current_language
        ).select_related('author', 'category').prefetch_related('tags')
        
        # Pagination
        paginator = Paginator(posts, 12)
        page = request.GET.get('page', 1)
        
        try:
            posts_page = paginator.page(page)
        except (PageNotAnInteger, EmptyPage):
            posts_page = paginator.page(1)
        
        context = {
            'posts': posts_page,
            'category': category,
            'page_title': f'{category.name} - Blog',
        }
        
        logger.info(f"Blog category '{category.name}' viewed by user: {request.user.username if request.user.is_authenticated else 'anonymous'}")
        return render(request, 'blog/category.html', context)
        
    except Exception as e:
        logger.error(f"Error in blog category view for slug '{slug}': {str(e)}", exc_info=True)
        raise Http404("Category not found")


def tag_posts(request, slug):
    """Posts filtered by tag"""
    try:
        current_language = request.LANGUAGE_CODE or 'en'
        tag = get_object_or_404(Tag, slug=slug)
        
        posts = BlogPost.objects.filter(
            tags=tag,
            status='published',
            language=current_language
        ).select_related('author', 'category').prefetch_related('tags')
        
        # Pagination
        paginator = Paginator(posts, 12)
        page = request.GET.get('page', 1)
        
        try:
            posts_page = paginator.page(page)
        except (PageNotAnInteger, EmptyPage):
            posts_page = paginator.page(1)
        
        context = {
            'posts': posts_page,
            'tag': tag,
            'page_title': f'{tag.name} - Blog',
        }
        
        logger.info(f"Blog tag '{tag.name}' viewed by user: {request.user.username if request.user.is_authenticated else 'anonymous'}")
        return render(request, 'blog/tag.html', context)
        
    except Exception as e:
        logger.error(f"Error in blog tag view for slug '{slug}': {str(e)}", exc_info=True)
        raise Http404("Tag not found")


def search_posts(request):
    """Search blog posts"""
    try:
        query = request.GET.get('q', '').strip()
        current_language = request.LANGUAGE_CODE or 'en'
        
        posts = BlogPost.objects.filter(
            status='published',
            language=current_language
        )
        
        if query:
            posts = posts.filter(
                Q(title__icontains=query) |
                Q(excerpt__icontains=query) |
                Q(content__icontains=query) |
                Q(tags__name__icontains=query) |
                Q(category__name__icontains=query)
            ).distinct()
        
        posts = posts.select_related('author', 'category').prefetch_related('tags')
        
        # Pagination
        paginator = Paginator(posts, 12)
        page = request.GET.get('page', 1)
        
        try:
            posts_page = paginator.page(page)
        except (PageNotAnInteger, EmptyPage):
            posts_page = paginator.page(1)
        
        context = {
            'posts': posts_page,
            'query': query,
            'page_title': f'Search: {query}' if query else 'Search Blog',
        }
        
        logger.info(f"Blog search for '{query}' by user: {request.user.username if request.user.is_authenticated else 'anonymous'}")
        return render(request, 'blog/search.html', context)
        
    except Exception as e:
        logger.error(f"Error in blog search view: {str(e)}", exc_info=True)
        return render(request, 'blog/search.html', {
            'posts': [],
            'query': '',
            'page_title': 'Search Blog',
        })


def archive_posts(request, year=None, month=None):
    """Posts archive by year/month"""
    try:
        current_language = request.LANGUAGE_CODE or 'en'
        
        posts = BlogPost.objects.filter(
            status='published',
            language=current_language
        )
        
        if year:
            posts = posts.filter(published_at__year=year)
            if month:
                posts = posts.filter(published_at__month=month)
        
        posts = posts.select_related('author', 'category').prefetch_related('tags')
        
        # Pagination
        paginator = Paginator(posts, 12)
        page = request.GET.get('page', 1)
        
        try:
            posts_page = paginator.page(page)
        except (PageNotAnInteger, EmptyPage):
            posts_page = paginator.page(1)
        
        # Build page title
        if year and month:
            page_title = f'Archive: {year}/{month:02d}'
        elif year:
            page_title = f'Archive: {year}'
        else:
            page_title = 'Blog Archive'
        
        context = {
            'posts': posts_page,
            'year': year,
            'month': month,
            'page_title': page_title,
        }
        
        logger.info(f"Blog archive ({year}/{month}) viewed by user: {request.user.username if request.user.is_authenticated else 'anonymous'}")
        return render(request, 'blog/archive.html', context)
        
    except Exception as e:
        logger.error(f"Error in blog archive view: {str(e)}", exc_info=True)
        return render(request, 'blog/archive.html', {
            'posts': [],
            'page_title': 'Blog Archive',
        })
