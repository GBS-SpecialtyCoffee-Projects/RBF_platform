# forms.py

from django import forms
from base.models import FarmerPhoto,Roaster, RoasterPhoto, User, Farmer, MeetingRequest,Story
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.contrib.auth import authenticate
from PIL import Image
from django_countries.widgets import CountrySelectWidget
from django_countries.fields import CountryField
from phonenumber_field.formfields import PhoneNumberField,SplitPhoneNumberField
from phonenumber_field.widgets import PhoneNumberPrefixWidget
import re

HARVEST_CHOICES = (
    ('spring','spring'),
    ('summer','summer'),
    ('autumn','autumn'),        
    ('winter','winter')   
)


class FarmerPhotoForm(forms.ModelForm):
    class Meta:
        model = FarmerPhoto
        fields = ['photo']
        widgets = {
            'photo': forms.FileInput(attrs={'class': 'form-control'}),
        }


class FarmerForm(forms.ModelForm):

    class Meta:
        model = Farmer

        fields = [
            'farm_name',  'bio', 'country', 'state', 'city',
            'firstname', 'lastname', 'middlename','country_code','phone_number',
            'farm_size' , 'annual_production', 'cultivars',
            'cup_scores_received', 'source_of_cup_scores', 'quality_report_link',
            'processing_method', 'processing_description', 'profile_picture',
            'preferred_communication_method', 'main_role','annual_production_unit','harvest_season','is_member_organization','member_organization_name'
        ]
        
        labels = {
            "farm_name": "Farm Name*",
            'bio': 'Bio*',
            'country': 'Farm Country*',
            'state': 'State/Province/Department*',
            'city': 'County/Municipality/City*',
            'firstname':'First Name*',
            'lastname': 'Last Name*',
            'middlename': 'Middle Name',
            'country_code': 'Code',
            'phone_number': 'Phone Number*',
            'farm_size': 'Farm Size(in hectares)',
            'harvest_season': 'Harvest Season',
            'annual_production': 'Annual Production',
            'cultivars': 'Cultivars/Varieties',
            'cup_scores_received': 'Cup Scores Received',
            'source_of_cup_scores': 'Source of Cup Scores',
            'quality_report_link': 'Quality Report Link',
            'processing_method': 'Processing Method',
            'processing_description': 'Processing Description',
            'profile_picture': 'Profile Picture',
            'preferred_communication_method': 'Preferred Communication Method',
            "farm_size_unit": "Farm Size Unit",
            "annual_production_unit": "Annual Production Unit",
            'is_member_organization': 'Are you a member of an organization that represents you commercially? (in which you have a voice and/or vote, not just a buyer, for example cooperatives, collectives, or associations)',
            'member_organization_name': "If yes,name the organization"
        }
        widgets = {
            'farm_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Farm Name','autocomplete':'off'},),
            # 'country': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Country','required':'true'}),
            'country': forms.Select(attrs={'class': 'form-control', 'placeholder': 'Country','required':'true','autocomplete':'off'},),
            'state': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'State','required':'true','autocomplete':'off'}),
            'city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'City','required':'true','autocomplete':'off'}),
            'bio': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Bio','required':'true','autocomplete':'off'}),
            'firstname': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name','required':'true','autocomplete':'off',}),
            'lastname': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name','required':'true','autocomplete':'off'}),
            'middlename': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Middle Name','autocomplete':'off'}),
            'country_code': forms.Select(attrs={'class': 'form-control', 'placeholder': 'Country Code','autocomplete':'off'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone Number','autocomplete':'off'}),
            'farm_size': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Farm Size','autocomplete':'off'}),
            'harvest_season': forms.CheckboxSelectMultiple(attrs={'class': 'form-check form-check-inline', 'placeholder': 'Harvest Season'}),
            'annual_production': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Annual Production','autocomplete':'off'}),
            'cultivars': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Cultivars','autocomplete':'off'}),
            'cup_scores_received': forms.CheckboxSelectMultiple(attrs={'class': 'form-check form-check-inline', 'placeholder': 'Cup Scores Received'}),
            'source_of_cup_scores': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Source of Cup Scores','autocomplete':'off'}),
            'quality_report_link': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'Quality Report Link','autocomplete':'off'}),
            'processing_method': forms.CheckboxSelectMultiple(attrs={'class': 'form-check form-check-inline', 'placeholder': 'Processing Method'}),
            'processing_description': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Processing Description','autocomplete':'off'}),
            'profile_picture': forms.FileInput(attrs={'class': 'form-control'}),
            'preferred_communication_method': forms.Select(attrs={'class': 'form-control', 'placeholder': 'Preferred Communication Method'}),
            'main_role': forms.Select(attrs={'class': 'form-control', 'placeholder': 'Main Role'}),
            # 'farm_size_unit': forms.Select(attrs={'class': 'form-control', 'placeholder': 'Farm Size Unit'}),
            'annual_production_unit': forms.Select(attrs={'class': 'form-control', 'placeholder': 'Annual Production Unit'}),
            'is_member_organization': forms.RadioSelect(attrs={'class': 'form-check form-check-inline', 'placeholder': 'Is Member Organization'}),
            'member_organization_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Member Organization Name','autocomplete':'off'}),
        }


class FarmerProfileForm(forms.ModelForm):
    class Meta:
        model = Farmer
        fields = [
            'farm_name','farm_size', 'harvest_season', 'annual_production', 'cultivars',
            'cup_scores_received', 'source_of_cup_scores', 'quality_report_link',
            'processing_method', 'processing_description', 'preferred_communication_method','country','state','city','member_organization_name'
        ]
        labels = {
            "farm_name": "Farm Name*",
            'farm_size': 'Farm Size',
            'harvest_season': 'Harvest Season',
            'annual_production': 'Annual Production',
            'cultivars': 'Cultivars/Varieties',
            'cup_scores_received': 'Cup Scores Received',
            'source_of_cup_scores': 'Source of Cup Scores',
            'quality_report_link': 'Quality Report Link',
            'processing_method': 'Processing Method',
            'processing_description': 'Processing Description',
            'preferred_communication_method': 'Preferred Communication Method',
            'country': 'Country',
            'state': 'State',
            'city': 'City',
            'member_organization_name': 'Member Organization Name',
            # 'profile_picture': 'Profile Picture',
        }
        widgets = {
            'farm_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Farm Name'}),
            'farm_size': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Farm Size'}),
            'harvest_season': forms.CheckboxSelectMultiple(attrs={'class': 'form-check form-check-inline', 'placeholder': 'Harvest Season'}),
            'annual_production': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Annual Production'}),
            'cultivars': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Cultivars'}),
            'cup_scores_received': forms.CheckboxSelectMultiple(attrs={'class': 'form-check form-check-inline', 'placeholder': 'Cup Scores Received'}),
            'source_of_cup_scores': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Source of Cup Scores'}),
            'quality_report_link': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'Quality Report Link'}),
            'processing_method': forms.CheckboxSelectMultiple(attrs={'class': 'form-check form-check-inline', 'placeholder': 'Processing Method'}),
            'processing_description': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Processing Description'}),
            'preferred_communication_method': forms.Select(attrs={'class': 'form-control', 'placeholder': 'Preferred Communication Method'}),
            'country': forms.Select(attrs={'class': 'form-control', 'placeholder': 'Country','required':'true','autocomplete':'off'},),
            'state': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'State','required':'true','autocomplete':'off'}),
            'city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'City','required':'true','autocomplete':'off'}),
            'member_organization_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Member Organization Name','required':'true','autocomplete':'off'}),

        }



class RoasterForm(forms.ModelForm):
    class Meta:
        model = Roaster
        fields = [
            'company_name', 'country', 'state', 'city', 'bio',
            'min_lot_size', 'annual_throughput',
            'origins_interested', 'coffee_types_interested', 'profile_picture'
        ]
        widgets = {
            'company_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Company Name'}),
            'country': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Country'}),
            'state': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'State'}),
            'city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'City'}),
            'bio': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Bio'}),
            'min_lot_size': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Minimum Lot Size'}),
            'annual_throughput': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Annual Throughput'}),
            'origins_interested': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Origins Interested'}),
            'coffee_types_interested': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Coffee Types Interested'}),
            'profile_picture': forms.FileInput(attrs={'class': 'form-control'}),
        }

class RoasterPhotoForm(forms.ModelForm):
    class Meta:
        model = RoasterPhoto
        fields = ['photo']
        widgets = {
            'photo': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }

User = get_user_model()



class SignupForm(forms.ModelForm):
    confirm_email = forms.EmailField(label="Confirm email address", widget=forms.EmailInput(attrs={'class': 'form-control'}))
    password1 = forms.CharField(label='Password', widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    password2 = forms.CharField(label='Confirm Password', widget=forms.PasswordInput(attrs={'class': 'form-control'}))

    class Meta:
        model = User
        fields = ['username', 'email', 'group', 'password1', 'password2']
        labels = {
            'username': 'Username',
            'email': 'Email',
            'group': 'Select Group',
            'password1': 'Password',
            'password2': 'Confirm Password',
        }
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'group': forms.Select(attrs={'class': 'form-control'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get('email')
        confirm_email = cleaned_data.get('confirm_email')
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')

        # Email confirmation check
        if email and confirm_email and email != confirm_email:
            self.add_error('confirm_email', "Emails don't match")

        # Password confirmation check
        if password1 and password2 and password1 != password2:
            self.add_error('password2', "Passwords don't match")

        # Password complexity check
        if password1:
            if len(password1) < 8:
                self.add_error('password1', "Password must be at least 8 characters long")
            if not re.search(r'[A-Z]', password1):
                self.add_error('password1', "Password must contain at least one uppercase letter")
            if not re.search(r'\d', password1):
                self.add_error('password1', "Password must contain at least one number")

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        if commit:
            user.save()

            # Create farmer or roaster based on group selection
            if self.cleaned_data['group'] == 'farmer':
                Farmer.objects.create(user=user)
            elif self.cleaned_data['group'] == 'roaster':
                Roaster.objects.create(user=user)

        return user



class SigninForm(forms.Form):
    email = forms.EmailField(label='Email', max_length=254, required=True)
    password = forms.CharField(label='Password', widget=forms.PasswordInput)

    def clean(self):
        email = self.cleaned_data.get('email')
        password = self.cleaned_data.get('password')
        if email and password:
            try:
                user = User.objects.get(email=email)
                if not user.check_password(password):
                    raise ValidationError('Invalid email or password.')
            except User.DoesNotExist:
                raise ValidationError('Invalid email or password.')
        return self.cleaned_data


    def authenticate_user(self):
        email = self.cleaned_data.get('email')
        password = self.cleaned_data.get('password')
        try:
            user = User.objects.get(email=email)
            if user.check_password(password):
                return user
        except User.DoesNotExist:
            return None

class PasswordResetForm(forms.Form):
    password = forms.CharField(label='New Password', widget=forms.PasswordInput(attrs={'class': 'form-control'}), required=True)
    confirm_password = forms.CharField(label='Confirm New Password', widget=forms.PasswordInput(attrs={'class': 'form-control'}), required=True)

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        # Password confirmation check
        if password != confirm_password:
            self.add_error('confirm_password', "Passwords do not match")

        # Password complexity check (same as in SignupForm)
        if password:
            if len(password) < 8:
                self.add_error('password', "Password must be at least 8 characters long")
            if not re.search(r'[A-Z]', password):
                self.add_error('password', "Password must contain at least one uppercase letter")
            if not re.search(r'\d', password):
                self.add_error('password', "Password must contain at least one number")

        return cleaned_data

class MeetingRequestForm(forms.ModelForm):
    class Meta:
        model = MeetingRequest
        fields = ['proposed_date', 'message']
        widgets = {
            'proposed_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'message': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Enter your message here'}),
        }


class RoasterProfileForm(forms.ModelForm):
    class Meta:
        model = Roaster
        fields = ['company_name',  'bio', 'min_lot_size', 'annual_throughput', 'origins_interested', 'coffee_types_interested']
        widgets = {
            'company_name': forms.TextInput(attrs={'class': 'form-control'}),
            'bio': forms.Textarea(attrs={'class': 'form-control'}),
            'min_lot_size': forms.TextInput(attrs={'class': 'form-control'}),
            'annual_throughput': forms.TextInput(attrs={'class': 'form-control'}),
            'origins_interested': forms.TextInput(attrs={'class': 'form-control'}),
            'coffee_types_interested': forms.TextInput(attrs={'class': 'form-control'}),
        }


class FarmerProfilePhotoForm(forms.ModelForm):
    class Meta:
        model = Farmer
        fields = ['profile_picture','firstname','lastname', 'city', 'state', 'country','country_code','phone_number']
        widgets = {
            'profile_picture': forms.FileInput(attrs={'class': 'form-control'}),
            'country': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Country'}),
            'state': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'State'}),
            'city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'City'}),
            'firstname': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'}),
            'lastname': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'}),
            'country_code': forms.Select(attrs={'class': 'form-control', 'placeholder': 'Code'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone Number'}),

        }


class RoasterInfoForm(forms.ModelForm):
    class Meta:
        model = Roaster
        fields = ['company_name', 'country', 'state', 'city', 'profile_picture']
        widgets = {
            'company_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Company Name'}),
            'country': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Country'}),
            'state': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'State'}),
            'city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'City'}),
            'profile_picture': forms.FileInput(attrs={'class': 'form-control'}),
        }

class RoasterBioForm(forms.ModelForm):
    class Meta:
        model = Roaster
        fields = ['bio']
        widgets = {
            'bio': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Write something about your company...'}),
        }


class RoasterSourcingForm(forms.ModelForm):
    class Meta:
        model = Roaster
        fields = [
            'min_lot_size',
            'annual_throughput',
            'coffee_types_interested',
            'origins_interested'
        ]
        widgets = {
            'min_lot_size': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Minimum Lot Size'}),
            'annual_throughput': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Annual Throughput'}),
            'coffee_types_interested': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Coffee Types Interested'}),
            'origins_interested': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Origins Interested'}),
        }

class FarmerStoryForm(forms.ModelForm):
    class Meta:
        model = Story
        fields = ['language', 'story_text']
        widgets = {
            'story_text': forms.Textarea(attrs={'id': 'edit_story_modal', 'class': 'form-control'}),
            'language': forms.HiddenInput(attrs={'id': 'edit_story_lang', 'class': 'form-control'}),
        }

class FarmerAddStoryForm(forms.ModelForm):
    class Meta:
        model = Story
        fields = ['language', 'story_text']
        widgets = {
            'story_text': forms.Textarea(attrs={'id': 'add_story_modal', 'class': 'form-control'}),
            'language': forms.HiddenInput(attrs={'id': 'add_story_lang', 'class': 'form-control'}),
        }



class OrientationTasksForm(forms.ModelForm):
    class Meta:
        model = Farmer
        fields = ['profile_completed',
                  'storytelling_workshop',
                  'video_pricing',
                  'video_intl',
                  'video_comm_tips',
                  'video_relationships',
                  'video_perceptions']
        widgets = {
            'profile_completed': forms.CheckboxInput(attrs={
                'class': 'form-check-input',  # Bootstrap 5 checkbox class
                'id': 'profileCheck'
            }),
            'storytelling_workshop': forms.CheckboxInput(attrs={
                'class': 'form-check-input',  # Bootstrap 5 checkbox class
                'id': 'storytellingCheck'
            }),
            'video_pricing': forms.CheckboxInput(attrs={
                'class': 'form-check-input'}),
            'video_intl': forms.CheckboxInput(attrs={
                'class': 'form-check-input'}),
            'video_comm_tips': forms.CheckboxInput(attrs={
                'class': 'form-check-input'}),
            'video_relationships': forms.CheckboxInput(attrs={
                'class': 'form-check-input'}),
            'video_perceptions': forms.CheckboxInput(attrs={
                'class': 'form-check-input'}),
        }


class StoryTellingCheck(forms.ModelForm):
    class Meta:
        model = Farmer
        fields = ['storytelling_workshop']
        widgets = {'storytelling_workshop': forms.CheckboxInput(attrs={
                'class': 'form-check-input',  # Bootstrap 5 checkbox class
                'id': 'StoryTellingCheck'})} 
        
class VideoPricingCheck(forms.ModelForm):
    class Meta:
        model = Farmer
        fields = ['video_pricing']
        widgets = {'video_pricing': forms.CheckboxInput(attrs={
                'class': 'form-check-input',  # Bootstrap 5 checkbox class
                'id': 'VideoPricingCheck'})}
        

class VideoIntlCheck(forms.ModelForm):
    class Meta:
        model = Farmer
        fields = ['video_intl']
        widgets = {'video_intl': forms.CheckboxInput(attrs={
                'class': 'form-check-input',  # Bootstrap 5 checkbox class
                'id': 'VideoIntlCheck'})}
        
class VideoCommTipsCheck(forms.ModelForm):
    class Meta:
        model = Farmer
        fields = ['video_comm_tips']
        widgets = {'video_comm_tips': forms.CheckboxInput(attrs={
                'class': 'form-check-input',  # Bootstrap 5 checkbox class
                'id': 'VideoCommTipsCheck'})}

class VideoRelationshipsCheck(forms.ModelForm):
    class Meta:
        model = Farmer
        fields = ['video_relationships']
        widgets = {'video_relationships': forms.CheckboxInput(attrs={
                'class': 'form-check-input',  # Bootstrap 5 checkbox class
                'id': 'VideoRelationshipsCheck'})}
        
class VideoPerceptionsCheck(forms.ModelForm):
    class Meta:
        model = Farmer
        fields = ['video_perceptions']
        widgets = {'video_perceptions': forms.CheckboxInput(attrs={
                'class': 'form-check-input',  # Bootstrap 5 checkbox class
                'id': 'VideoPerceptionsCheck'})}
        
class StoryForm(forms.ModelForm):
    class Meta:
        model = Story
        fields = ['story_text','language']
        widgets = {
            'story_text': forms.Textarea(attrs={'class': 'form-control'}),
            'language': forms.Select(attrs={'class': 'form-control'}),
        }
        labels = {
            "story_text": "Story text",
            'language': 'Story Language',}


