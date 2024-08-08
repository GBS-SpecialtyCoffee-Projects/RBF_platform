# forms.py

from django import forms
from base.models import FarmerPhoto,Roaster, RoasterPhoto, User, Farmer, MeetingRequest
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.contrib.auth import authenticate

class FarmerPhotoForm(forms.ModelForm):
    class Meta:
        model = FarmerPhoto
        fields = ['photo', 'order']

class FarmerForm(forms.ModelForm):
    class Meta:
        model = Farmer
        fields = ['farm_name', 'location', 'bio', 'size', 'affiliation']



class RoasterForm(forms.ModelForm):
    class Meta:
        model = Roaster
        fields = ['company_name', 'location', 'bio',
            'min_lot_size', 'annual_throughput',
            'origins_interested', 'coffee_types_interested']


class RoasterPhotoForm(forms.ModelForm):
    class Meta:
        model = RoasterPhoto

        fields = [ 'photo', 'order']

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

        if email and confirm_email and email != confirm_email:
            self.add_error('confirm_email', "Emails don't match")

        if password1 and password2 and password1 != password2:
            self.add_error('password2', "Passwords don't match")

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
    password = forms.CharField(label='New Password', widget=forms.PasswordInput, required=True)
    confirm_password = forms.CharField(label='Confirm New Password', widget=forms.PasswordInput, required=True)

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password != confirm_password:
            raise ValidationError("Passwords do not match.")


        return cleaned_data


class MeetingRequestForm(forms.ModelForm):
    class Meta:
        model = MeetingRequest
        fields = ['proposed_date', 'message']
        widgets = {
            'proposed_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'message': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Enter your message here'}),
        }


class FarmerProfileForm(forms.ModelForm):
    class Meta:
        model = Farmer
        fields = ['farm_name', 'location', 'bio', 'size', 'affiliation']
        widgets = {
            'farm_name': forms.TextInput(attrs={'class': 'form-control'}),
            'location': forms.TextInput(attrs={'class': 'form-control'}),
            'bio': forms.Textarea(attrs={'class': 'form-control'}),
            'size': forms.TextInput(attrs={'class': 'form-control'}),
            'affiliation': forms.TextInput(attrs={'class': 'form-control'}),
        }

class RoasterProfileForm(forms.ModelForm):
    class Meta:
        model = Roaster
        fields = ['company_name', 'location', 'bio', 'min_lot_size', 'annual_throughput', 'origins_interested', 'coffee_types_interested']
        widgets = {
            'company_name': forms.TextInput(attrs={'class': 'form-control'}),
            'location': forms.TextInput(attrs={'class': 'form-control'}),
            'bio': forms.Textarea(attrs={'class': 'form-control'}),
            'min_lot_size': forms.TextInput(attrs={'class': 'form-control'}),
            'annual_throughput': forms.TextInput(attrs={'class': 'form-control'}),
            'origins_interested': forms.TextInput(attrs={'class': 'form-control'}),
            'coffee_types_interested': forms.TextInput(attrs={'class': 'form-control'}),
        }


class FarmerProfilePhotoForm(forms.ModelForm):
    class Meta:
        model = Farmer
        fields = ['profile_picture']
        widgets = {
            'profile_picture': forms.FileInput(attrs={'class': 'form-control'}),
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

