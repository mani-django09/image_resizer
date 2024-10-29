from django import forms

class ImageUploadForm(forms.Form):
    image_file = forms.ImageField(label='Choose Image')
    quality = forms.IntegerField(
        min_value=1,
        max_value=100,
        initial=80,
        widget=forms.NumberInput(attrs={'type': 'range', 'class': 'quality-slider'})
    )
    preserve_exif = forms.BooleanField(required=False, initial=True)
    auto_rotate = forms.BooleanField(required=False, initial=True)