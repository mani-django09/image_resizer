from django.urls import path
from .views import UploadView,home,GalleryView,CustomLoginView,dynamic_features

urlpatterns = [
    path('upload/', UploadView.as_view(), name='upload'),
    path('', home, name='home'),  # Home page URL
    path('gallery/', GalleryView.as_view(), name='gallery'),
    path('login/', CustomLoginView.as_view(), name='login'),  # Add this line
    path('dynamic-features/', dynamic_features, name='dynamic_features'),


]
