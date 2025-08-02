import os
from django.contrib.admin.views.decorators import staff_member_required
from django.core.files.storage import default_storage
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
import uuid


@method_decorator(staff_member_required, name='dispatch')
@method_decorator(csrf_exempt, name='dispatch')
class TinyMCEImageUploadView(View):
    """Handle image uploads for TinyMCE editor"""
    
    def post(self, request):
        try:
            if 'file' not in request.FILES:
                return JsonResponse({'error': 'No file provided'}, status=400)
            
            file = request.FILES['file']
            
            # Validate file type
            allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
            if file.content_type not in allowed_types:
                return JsonResponse({'error': 'Invalid file type'}, status=400)
            
            # Validate file size (max 5MB)
            if file.size > 5 * 1024 * 1024:
                return JsonResponse({'error': 'File too large'}, status=400)
            
            # Generate unique filename
            ext = os.path.splitext(file.name)[1]
            filename = f"blog/uploads/{uuid.uuid4()}{ext}"
            
            # Save file
            saved_path = default_storage.save(filename, file)
            file_url = default_storage.url(saved_path)
            
            # Return success response
            return JsonResponse({
                'location': request.build_absolute_uri(file_url)
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


tinymce_upload_view = TinyMCEImageUploadView.as_view()
