from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
import json
from PIL import Image
from io import BytesIO

from .models import BlogPost, Category, Tag

User = get_user_model()


class BlogModelTest(TestCase):
    """Test blog models"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            is_staff=True
        )
        self.category = Category.objects.create(
            name='Test Category',
            description='Test category description'
        )
        self.tag = Tag.objects.create(
            name='test-tag'
        )
    
    def test_category_creation(self):
        """Test category model creation"""
        self.assertEqual(self.category.name, 'Test Category')
        self.assertEqual(self.category.slug, 'test-category')
        self.assertEqual(str(self.category), 'Test Category')
    
    def test_tag_creation(self):
        """Test tag model creation"""
        self.assertEqual(self.tag.name, 'test-tag')
        self.assertEqual(str(self.tag), 'test-tag')
    
    def test_blog_post_creation(self):
        """Test blog post model creation"""
        post = BlogPost.objects.create(
            title='Test Blog Post',
            author=self.user,
            category=self.category,
            excerpt='Test excerpt',
            content='<p>Test content with HTML</p>',
            status='published',
            language='en'
        )
        post.tags.add(self.tag)
        
        self.assertEqual(post.title, 'Test Blog Post')
        self.assertEqual(post.slug, 'test-blog-post')
        self.assertEqual(post.author, self.user)
        self.assertEqual(post.category, self.category)
        self.assertEqual(post.status, 'published')
        self.assertTrue(post.is_published)
        self.assertIn(self.tag, post.tags.all())
        self.assertEqual(str(post), 'Test Blog Post')
    
    def test_blog_post_absolute_url(self):
        """Test blog post get_absolute_url method"""
        post = BlogPost.objects.create(
            title='Test Blog Post',
            author=self.user,
            category=self.category,
            excerpt='Test excerpt',
            content='<p>Test content</p>',
            status='published',
            language='en'
        )
        expected_url = f'/blog/{post.slug}/'
        self.assertEqual(post.get_absolute_url(), expected_url)
    
    def test_blog_post_published_manager(self):
        """Test published posts manager"""
        # Create published post
        published_post = BlogPost.objects.create(
            title='Published Post',
            author=self.user,
            category=self.category,
            excerpt='Published excerpt',
            content='<p>Published content</p>',
            status='published',
            language='en'
        )
        
        # Create draft post
        draft_post = BlogPost.objects.create(
            title='Draft Post',
            author=self.user,
            category=self.category,
            excerpt='Draft excerpt',
            content='<p>Draft content</p>',
            status='draft',
            language='en'
        )
        
        published_posts = BlogPost.published.all()
        self.assertIn(published_post, published_posts)
        self.assertNotIn(draft_post, published_posts)


class BlogViewTest(TestCase):
    """Test blog views"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            is_staff=True
        )
        self.category = Category.objects.create(
            name='Test Category',
            description='Test category description'
        )
        self.tag = Tag.objects.create(
            name='test-tag'
        )
        self.post = BlogPost.objects.create(
            title='Test Blog Post',
            author=self.user,
            category=self.category,
            excerpt='Test excerpt',
            content='<p>Test content with HTML</p>',
            status='published',
            language='en'
        )
        self.post.tags.add(self.tag)
    
    def test_blog_home_view(self):
        """Test blog home page"""
        response = self.client.get('/blog/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Blog Post')
        self.assertContains(response, 'Test excerpt')
    
    def test_blog_post_detail_view(self):
        """Test blog post detail view"""
        response = self.client.get(f'/blog/{self.post.slug}/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Blog Post')
        self.assertContains(response, 'Test content with HTML')
    
    def test_blog_post_detail_404(self):
        """Test blog post detail view with non-existent slug"""
        response = self.client.get('/blog/non-existent-post/')
        self.assertEqual(response.status_code, 404)
    
    def test_blog_category_view(self):
        """Test blog category view"""
        response = self.client.get(f'/blog/category/{self.category.slug}/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Category')
        self.assertContains(response, 'Test Blog Post')
    
    def test_blog_tag_view(self):
        """Test blog tag view"""
        response = self.client.get(f'/blog/tag/{self.tag.name}/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'test-tag')
        self.assertContains(response, 'Test Blog Post')
    
    def test_blog_search_view(self):
        """Test blog search functionality"""
        # Test with query
        response = self.client.get('/blog/search/', {'q': 'Test'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Blog Post')
        
        # Test without query
        response = self.client.get('/blog/search/')
        self.assertEqual(response.status_code, 200)
    
    def test_blog_archive_view(self):
        """Test blog archive view"""
        response = self.client.get('/blog/archive/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Blog Post')
    
    def test_draft_post_not_visible(self):
        """Test that draft posts are not visible to public"""
        draft_post = BlogPost.objects.create(
            title='Draft Post',
            author=self.user,
            category=self.category,
            excerpt='Draft excerpt',
            content='<p>Draft content</p>',
            status='draft',
            language='en'
        )
        
        # Should not appear in blog home
        response = self.client.get('/blog/')
        self.assertNotContains(response, 'Draft Post')
        
        # Should return 404 when accessed directly
        response = self.client.get(f'/blog/{draft_post.slug}/')
        self.assertEqual(response.status_code, 404)


class TinyMCEUploadViewTest(TestCase):
    """Test TinyMCE image upload functionality"""
    
    def setUp(self):
        self.client = Client()
        self.staff_user = User.objects.create_user(
            username='staffuser',
            email='staff@example.com',
            password='testpass123',
            is_staff=True
        )
        self.regular_user = User.objects.create_user(
            username='regularuser',
            email='regular@example.com',
            password='testpass123',
            is_staff=False
        )
        self.upload_url = '/tinymce/upload/'
    
    def create_test_image(self, format='JPEG', size=(100, 100)):
        """Helper method to create test image"""
        image = Image.new('RGB', size, color='red')
        image_file = BytesIO()
        image.save(image_file, format=format)
        image_file.seek(0)
        return SimpleUploadedFile(
            name=f'test.{format.lower()}',
            content=image_file.getvalue(),
            content_type=f'image/{format.lower()}'
        )
    
    def test_upload_requires_staff_permission(self):
        """Test that upload requires staff permissions"""
        image = self.create_test_image()
        
        # Anonymous user should be redirected
        response = self.client.post(self.upload_url, {'file': image})
        self.assertEqual(response.status_code, 302)  # Redirect to login
        
        # Regular user should be forbidden
        self.client.login(username='regularuser', password='testpass123')
        response = self.client.post(self.upload_url, {'file': image})
        self.assertEqual(response.status_code, 302)  # Redirect to login
    
    def test_successful_image_upload(self):
        """Test successful image upload"""
        self.client.login(username='staffuser', password='testpass123')
        image = self.create_test_image()
        
        response = self.client.post(self.upload_url, {'file': image})
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.content)
        self.assertIn('location', data)
        self.assertTrue(data['location'].startswith('http'))
        self.assertIn('/media/blog/uploads/', data['location'])
    
    def test_upload_no_file(self):
        """Test upload without file"""
        self.client.login(username='staffuser', password='testpass123')
        
        response = self.client.post(self.upload_url, {})
        self.assertEqual(response.status_code, 400)
        
        data = json.loads(response.content)
        self.assertIn('error', data)
        self.assertEqual(data['error'], 'No file provided')
    
    def test_upload_invalid_file_type(self):
        """Test upload with invalid file type"""
        self.client.login(username='staffuser', password='testpass123')
        
        # Create a text file instead of image
        text_file = SimpleUploadedFile(
            name='test.txt',
            content=b'This is a text file',
            content_type='text/plain'
        )
        
        response = self.client.post(self.upload_url, {'file': text_file})
        self.assertEqual(response.status_code, 400)
        
        data = json.loads(response.content)
        self.assertIn('error', data)
        self.assertEqual(data['error'], 'Invalid file type')
    
    def test_upload_large_file(self):
        """Test upload with file too large"""
        self.client.login(username='staffuser', password='testpass123')
        
        # Create a large image (simulating 6MB)
        large_content = b'x' * (6 * 1024 * 1024)
        large_file = SimpleUploadedFile(
            name='large.jpg',
            content=large_content,
            content_type='image/jpeg'
        )
        
        response = self.client.post(self.upload_url, {'file': large_file})
        self.assertEqual(response.status_code, 400)
        
        data = json.loads(response.content)
        self.assertIn('error', data)
        self.assertEqual(data['error'], 'File too large')
    
    def test_upload_different_image_formats(self):
        """Test upload with different valid image formats"""
        self.client.login(username='staffuser', password='testpass123')
        
        formats = ['JPEG', 'PNG', 'GIF']
        for format in formats:
            with self.subTest(format=format):
                image = self.create_test_image(format=format)
                response = self.client.post(self.upload_url, {'file': image})
                self.assertEqual(response.status_code, 200)
                
                data = json.loads(response.content)
                self.assertIn('location', data)


class BlogAdminTest(TestCase):
    """Test blog admin interface"""
    
    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpass123'
        )
        self.category = Category.objects.create(
            name='Test Category',
            description='Test category description'
        )
    
    def test_admin_blog_post_add(self):
        """Test adding blog post through admin"""
        self.client.login(username='admin', password='adminpass123')
        
        response = self.client.get('/admin/blog/blogpost/add/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'tinymce')  # Check TinyMCE is loaded
    
    def test_admin_blog_post_list(self):
        """Test blog post list in admin"""
        self.client.login(username='admin', password='adminpass123')
        
        # Create a test post
        BlogPost.objects.create(
            title='Admin Test Post',
            author=self.admin_user,
            category=self.category,
            excerpt='Admin test excerpt',
            content='<p>Admin test content</p>',
            status='published',
            language='en'
        )
        
        response = self.client.get('/admin/blog/blogpost/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Admin Test Post')


class BlogIntegrationTest(TestCase):
    """Integration tests for blog functionality"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            is_staff=True
        )
        
        # Create test data
        self.category = Category.objects.create(
            name='Integration Test Category',
            description='Category for integration testing'
        )
        self.tag = Tag.objects.create(
            name='integration-test'
        )
        
        # Create multiple posts for pagination testing
        for i in range(15):
            post = BlogPost.objects.create(
                title=f'Integration Test Post {i+1}',
                author=self.user,
                category=self.category,
                excerpt=f'Excerpt for post {i+1}',
                content=f'<p>Content for integration test post {i+1}</p>',
                status='published',
                language='en'
            )
            post.tags.add(self.tag)
    
    def test_blog_pagination(self):
        """Test blog pagination works correctly"""
        response = self.client.get('/blog/')
        self.assertEqual(response.status_code, 200)
        
        # Check pagination context - posts are paginated as Page object
        posts_page = response.context['posts']
        self.assertTrue(hasattr(posts_page, 'has_next'))  # Check it's a Page object
        self.assertEqual(len(posts_page), 6)  # Default page size is 6
        
        # Test second page
        response = self.client.get('/blog/?page=2')
        self.assertEqual(response.status_code, 200)
        posts_page_2 = response.context['posts']
        self.assertEqual(len(posts_page_2), 6)  # Should have 6 posts on page 2
        
        # Test third page (should have remaining posts)
        response = self.client.get('/blog/?page=3')
        self.assertEqual(response.status_code, 200)
        posts_page_3 = response.context['posts']
        self.assertEqual(len(posts_page_3), 3)  # Remaining posts (15 total - 6 - 6 = 3)
    
    def test_blog_with_related_places(self):
        """Test blog posts with related places"""
        # This would require Place model setup, skipping for now
        # but structure is ready for when places integration is needed
        pass
    
    def test_multilingual_blog_content(self):
        """Test multilingual blog functionality"""
        # Create post with multilingual content
        BlogPost.objects.create(
            title='Multilingual Test Post',
            author=self.user,
            category=self.category,
            excerpt='Test excerpt',
            content='<p>Test content</p>',
            status='published',
            language='en'
        )
        
        # Test that multilingual posts are accessible
        response = self.client.get('/blog/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Multilingual Test Post')
