from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.conf import settings
from django.core.files.storage import default_storage
from django.views.generic import View
from django.contrib.auth.views import LoginView
from django.contrib.auth.mixins import LoginRequiredMixin
from .forms import ImageUploadForm
from PIL import Image, ExifTags
import io
import os
import logging
from typing import Tuple
import magic

logger = logging.getLogger(__name__)

class ImageProcessingError(Exception):
    """Custom exception for image processing errors"""
    pass

def get_mime_type(file) -> str:
    """Determine MIME type of uploaded file using python-magic"""
    mime = magic.Magic(mime=True)
    file.seek(0)
    mime_type = mime.from_buffer(file.read(2048))
    file.seek(0)
    return mime_type

def process_image_orientation(image: Image.Image) -> Image.Image:
    """Process image orientation based on EXIF data"""
    if not hasattr(image, '_getexif') or not image._getexif():
        return image
    
    try:
        for orientation in ExifTags.TAGS.keys():
            if ExifTags.TAGS[orientation] == 'Orientation':
                break
        
        exif = dict(image._getexif().items())
        if orientation in exif:
            if exif[orientation] == 3:
                return image.rotate(180, expand=True)
            elif exif[orientation] == 6:
                return image.rotate(270, expand=True)
            elif exif[orientation] == 8:
                return image.rotate(90, expand=True)
    except Exception as e:
        logger.warning(f"Error processing image orientation: {str(e)}")
    
    return image

def compress_image(
    image: Image.Image,
    max_dimension: int = 3000,
    quality: int = 85,
    preserve_exif: bool = True
) -> Tuple[bytes, dict]:
    """Compress image while maintaining aspect ratio"""
    ratio = min(max_dimension / float(image.size[0]), 
                max_dimension / float(image.size[1]))
    
    if ratio < 1:  # Only resize if image is larger than max dimension
        new_size = tuple(int(dim * ratio) for dim in image.size)
        image = image.resize(new_size, Image.Resampling.LANCZOS)
    
    if image.mode in ('RGBA', 'P'):
        image = image.convert('RGB')
    
    output_buffer = io.BytesIO()
    save_params = {
        'format': 'JPEG',
        'quality': quality,
        'optimize': True
    }
    
    if preserve_exif and hasattr(image, 'info') and 'exif' in image.info:
        save_params['exif'] = image.info['exif']
    
    image.save(output_buffer, **save_params)
    
    compressed_data = output_buffer.getvalue()
    stats = {
        'final_width': image.size[0],
        'final_height': image.size[1],
        'compressed_size': len(compressed_data)
    }
    
    return compressed_data, stats

class UploadView(View):
    """Class-based view for handling image uploads and compression"""
    form_class = ImageUploadForm
    template_name = 'image_app/upload.html'  # Updated template path

    def get(self, request, *args, **kwargs):
        form = self.form_class()
        return render(request, self.template_name, {'form': form})

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST, request.FILES)
        
        try:
            if not form.is_valid():
                raise ImageProcessingError(dict(form.errors.items()))

            image_file = request.FILES['image_file']
            
            # Check file size and validate MIME type here if needed
            
            quality = form.cleaned_data['quality']
            preserve_exif = form.cleaned_data['preserve_exif']
            auto_rotate = form.cleaned_data['auto_rotate']
            
            # Open and process image
            with Image.open(image_file) as image:
                if auto_rotate:
                    image = process_image_orientation(image)
                
                compressed_data, stats = compress_image(
                    image,
                    quality=quality,
                    preserve_exif=preserve_exif
                )
            
            # Generate unique filename
            base_filename = os.path.splitext(image_file.name)[0]
            output_filename = f"{base_filename}_compressed_{quality}.jpg"
            
            # Prepare response for download
            response = HttpResponse(compressed_data, content_type='image/jpeg')
            response['Content-Disposition'] = f'attachment; filename="{output_filename}"'
            response['Content-Length'] = len(compressed_data)

            return response

        except ImageProcessingError as e:
            logger.warning(f"Image processing error: {str(e)}")
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
        
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}", exc_info=True)
            return JsonResponse({'success': False, 'error': "An unexpected error occurred."}, status=500)

class GalleryView(LoginRequiredMixin, View):
    """View for displaying compressed images gallery"""
    template_name = 'compressor/gallery.html'
    login_url = 'login'

    def get(self, request, *args, **kwargs):
        compressed_files = []
        storage = default_storage
        compressed_dir = 'compressed'
        
        if storage.exists(compressed_dir):
            for filename in storage.listdir(compressed_dir)[1]:  # [1] contains files
                if filename.lower().endswith(('.jpg', '.jpeg')):
                    file_url = storage.url(os.path.join(compressed_dir, filename))
                    compressed_files.append({
                        'url': file_url,
                        'name': filename
                    })

        return render(request, self.template_name, {'images': compressed_files})

class CustomLoginView(LoginView):
    """Custom login view"""
    template_name = 'compressor/login.html'  # Updated template path
    redirect_authenticated_user = True

def home(request):
    """Home page view"""
    return render(request, 'compressor/home.html')  # Updated template path


from django import forms

class ImageUploadForm(forms.Form):
    image_file = forms.FileField()
    quality = forms.IntegerField(min_value=1, max_value=100, initial=80)
    preserve_exif = forms.BooleanField(required=False)
    auto_rotate = forms.BooleanField(required=False)

    def clean_image_file(self):
        image_file = self.cleaned_data.get('image_file')
        if image_file.size > settings.MAX_UPLOAD_SIZE:
            raise forms.ValidationError(f"File too large. Maximum size is {settings.MAX_UPLOAD_SIZE/1048576}MB")
        return image_file
def dynamic_features(request):
    return render(request, 'dynamic_features.html')