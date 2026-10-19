from django.contrib.admin.views.decorators import staff_member_required
from django.core.files.storage import default_storage
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
import os
import uuid

ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
CONTENT_TYPE_EXTENSIONS = {
    'image/jpeg': '.jpg',
    'image/png': '.png',
    'image/gif': '.gif',
    'image/webp': '.webp',
}


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
            allowed_types = list(CONTENT_TYPE_EXTENSIONS)
            if file.content_type not in allowed_types:
                return JsonResponse({'error': 'Invalid file type'}, status=400)
            
            # Validate file size (max 5MB)
            if file.size > 5 * 1024 * 1024:
                return JsonResponse({'error': 'File too large'}, status=400)
            
            # Only keep the client extension if it is an image extension; otherwise
            # use the one for the validated content type (a .html name with an
            # image content type would otherwise be served from our origin).
            ext = os.path.splitext(file.name)[1].lower()
            if ext not in ALLOWED_EXTENSIONS:
                ext = CONTENT_TYPE_EXTENSIONS[file.content_type]
            filename = f"blog/uploads/{uuid.uuid4()}{ext}"
            
            # Save file
            saved_path = default_storage.save(filename, file)
            file_url = default_storage.url(saved_path)
            
            # Return success response
            return JsonResponse({
                'location': request.build_absolute_uri(file_url)
            })
            
        except Exception as e:
            return JsonResponse({'error': 'Upload failed'}, status=500)


tinymce_upload_view = TinyMCEImageUploadView.as_view()
