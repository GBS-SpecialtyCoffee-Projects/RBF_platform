# forms.py

from django import forms
from .models import FarmerPhoto,Roaster, RoasterPhoto

class FarmerPhotoForm(forms.ModelForm):
    class Meta:
        model = FarmerPhoto
        fields = ['user', 'photo', 'order']

class RoasterForm(forms.ModelForm):
    class Meta:
        model = Roaster
        fields = ['user', 'company_name', 'location', 'bio']

class RoasterPhotoForm(forms.ModelForm):
    class Meta:
        model = RoasterPhoto
        fields = ['user', 'photo', 'order']