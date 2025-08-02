from django.urls import path
from . import views

app_name = 'blog'

urlpatterns = [
    # Blog home
    path('', views.blog_home, name='home'),
    
    # Search (must come before slug pattern)
    path('search/', views.search_posts, name='search'),
    
    # Archive (must come before slug pattern)
    path('archive/', views.archive_posts, name='archive'),
    path('archive/<int:year>/', views.archive_posts, name='archive_year'),
    path('archive/<int:year>/<int:month>/', views.archive_posts, name='archive_month'),
    
    # Category filtering
    path('category/<slug:slug>/', views.category_posts, name='category'),
    
    # Tag filtering
    path('tag/<slug:slug>/', views.tag_posts, name='tag'),
    
    # Post detail (must come last as it's the most generic)
    path('<slug:slug>/', views.post_detail, name='detail'),
]
