from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.files.storage import default_storage
import json
import uuid
from PIL import Image
from io import BytesIO

User = get_user_model()


class TinyMCEUploadViewDetailedTest(TestCase):
    """Detailed tests for TinyMCE upload functionality"""
    
    def setUp(self):
        self.client = Client()
        self.staff_user = User.objects.create_user(
            username='staffuser',
            email='staff@example.com',
            password='testpass123',
            is_staff=True
        )
        self.superuser = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpass123'
        )
        self.regular_user = User.objects.create_user(
            username='regularuser',
            email='regular@example.com',
            password='testpass123',
            is_staff=False
        )
        self.upload_url = '/tinymce/upload/'
    
    def create_test_image(self, format='JPEG', size=(100, 100), color='red'):
        """Helper method to create test image with specific properties"""
        image = Image.new('RGB', size, color=color)
        image_file = BytesIO()
        image.save(image_file, format=format)
        image_file.seek(0)
        return SimpleUploadedFile(
            name=f'test_image.{format.lower()}',
            content=image_file.getvalue(),
            content_type=f'image/{format.lower()}'
        )
    
    def test_upload_permissions(self):
        """Test various user permission levels"""
        image = self.create_test_image()
        
        # Test anonymous user
        response = self.client.post(self.upload_url, {'file': image})
        self.assertEqual(response.status_code, 302)  # Redirect to login
        
        # Test regular user (not staff)
        self.client.login(username='regularuser', password='testpass123')
        response = self.client.post(self.upload_url, {'file': image})
        self.assertEqual(response.status_code, 302)  # Redirect to login
        
        # Test staff user
        self.client.login(username='staffuser', password='testpass123')
        response = self.client.post(self.upload_url, {'file': image})
        self.assertEqual(response.status_code, 200)
        
        # Test superuser
        self.client.login(username='admin', password='adminpass123')
        response = self.client.post(self.upload_url, {'file': image})
        self.assertEqual(response.status_code, 200)
    
    def test_image_format_validation(self):
        """Test different image formats"""
        self.client.login(username='staffuser', password='testpass123')
        
        # Test valid formats
        valid_formats = [
            ('JPEG', 'image/jpeg'),
            ('PNG', 'image/png'),
            ('GIF', 'image/gif'),
        ]
        
        for format_name, content_type in valid_formats:
            with self.subTest(format=format_name):
                image = self.create_test_image(format=format_name)
                response = self.client.post(self.upload_url, {'file': image})
                self.assertEqual(response.status_code, 200)
                
                data = json.loads(response.content)
                self.assertIn('location', data)
                self.assertTrue(data['location'].startswith('http'))
    
    def test_invalid_file_types(self):
        """Test uploading invalid file types"""
        self.client.login(username='staffuser', password='testpass123')
        
        # Test text file
        text_file = SimpleUploadedFile(
            name='test.txt',
            content=b'This is a text file',
            content_type='text/plain'
        )
        response = self.client.post(self.upload_url, {'file': text_file})
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertEqual(data['error'], 'Invalid file type')
        
        # Test PDF file
        pdf_file = SimpleUploadedFile(
            name='test.pdf',
            content=b'%PDF-1.4 fake pdf content',
            content_type='application/pdf'
        )
        response = self.client.post(self.upload_url, {'file': pdf_file})
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertEqual(data['error'], 'Invalid file type')
    
    def test_file_size_validation(self):
        """Test file size limits"""
        self.client.login(username='staffuser', password='testpass123')
        
        # Test file within size limit (small image)
        small_image = self.create_test_image(size=(50, 50))
        response = self.client.post(self.upload_url, {'file': small_image})
        self.assertEqual(response.status_code, 200)
        
        # Test oversized file (simulate large file)
        # Create a file that's definitely over 5MB
        large_content = b'x' * (6 * 1024 * 1024)  # 6MB
        large_file = SimpleUploadedFile(
            name='large.jpg',
            content=large_content,
            content_type='image/jpeg'
        )
        response = self.client.post(self.upload_url, {'file': large_file})
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertEqual(data['error'], 'File too large')
    
    def test_successful_upload_response_format(self):
        """Test the format of successful upload response"""
        self.client.login(username='staffuser', password='testpass123')
        image = self.create_test_image()
        
        response = self.client.post(self.upload_url, {'file': image})
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.content)
        self.assertIn('location', data)
        
        # Check URL format
        location = data['location']
        self.assertTrue(location.startswith('http'))
        self.assertIn('/media/blog/uploads/', location)
        
        # Check that filename has UUID format
        filename = location.split('/')[-1]
        name_part = filename.split('.')[0]
        # Should be a valid UUID4 format
        try:
            uuid.UUID(name_part, version=4)
        except ValueError:
            self.fail(f"Filename {name_part} is not a valid UUID4")
    
    def test_file_storage_location(self):
        """Test that files are stored in correct location"""
        self.client.login(username='staffuser', password='testpass123')
        image = self.create_test_image()
        
        response = self.client.post(self.upload_url, {'file': image})
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.content)
        location = data['location']
        
        # Extract the media path
        media_path = location.split('/media/')[-1]
        
        # Check if file exists in storage
        self.assertTrue(default_storage.exists(media_path))
        
        # Clean up - remove the test file
        default_storage.delete(media_path)
    
    def test_csrf_exemption(self):
        """Test that CSRF is properly exempted for the upload view"""
        # This view should work without CSRF token since it's exempt
        self.client.login(username='staffuser', password='testpass123')
        
        # Force CSRF protection by using enforce_csrf_checks
        with self.settings(CSRF_USE_SESSIONS=True):
            image = self.create_test_image()
            response = self.client.post(self.upload_url, {'file': image})
            self.assertEqual(response.status_code, 200)
    
    def test_missing_file_parameter(self):
        """Test request without file parameter"""
        self.client.login(username='staffuser', password='testpass123')
        
        response = self.client.post(self.upload_url, {})
        self.assertEqual(response.status_code, 400)
        
        data = json.loads(response.content)
        self.assertEqual(data['error'], 'No file provided')
    
    def test_get_request_not_allowed(self):
        """Test that GET requests are not supported"""
        self.client.login(username='staffuser', password='testpass123')
        
        response = self.client.get(self.upload_url)
        self.assertEqual(response.status_code, 405)  # Method not allowed
    
    def test_multiple_file_upload_scenario(self):
        """Test uploading multiple files sequentially"""
        self.client.login(username='staffuser', password='testpass123')
        
        uploaded_locations = []
        
        # Upload 3 different images
        for i in range(3):
            image = self.create_test_image(color=['red', 'green', 'blue'][i])
            response = self.client.post(self.upload_url, {'file': image})
            self.assertEqual(response.status_code, 200)
            
            data = json.loads(response.content)
            uploaded_locations.append(data['location'])
        
        # Verify all files have different names (UUID should ensure this)
        filenames = [loc.split('/')[-1] for loc in uploaded_locations]
        self.assertEqual(len(filenames), len(set(filenames)))  # All unique
        
        # Clean up uploaded files
        for location in uploaded_locations:
            media_path = location.split('/media/')[-1]
            if default_storage.exists(media_path):
                default_storage.delete(media_path)
    
    def test_file_extension_preservation(self):
        """Test that file extensions are preserved correctly"""
        self.client.login(username='staffuser', password='testpass123')
        
        test_cases = [
            ('JPEG', '.jpeg'),
            ('PNG', '.png'),
            ('GIF', '.gif'),
        ]
        
        for format_name, expected_ext in test_cases:
            with self.subTest(format=format_name):
                image = self.create_test_image(format=format_name)
                response = self.client.post(self.upload_url, {'file': image})
                self.assertEqual(response.status_code, 200)
                
                data = json.loads(response.content)
                location = data['location']
                filename = location.split('/')[-1]
                
                self.assertTrue(filename.endswith(expected_ext))
                
                # Clean up
                media_path = location.split('/media/')[-1]
                if default_storage.exists(media_path):
                    default_storage.delete(media_path)
