from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.conf import settings
from django.core.exceptions import ValidationError
from PIL import Image


# For admin purpose
class UserManager(BaseUserManager):
    def create_user(self, username, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)  # This hashes the password
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        return self.create_user(username, email, password, **extra_fields)

# first table: User
class User(AbstractBaseUser, PermissionsMixin):
    GROUP_CHOICES = [
        ('farmer', 'Farmer'),
        ('roaster', 'Roaster')
    ]

    id = models.AutoField(primary_key=True)
    username = models.CharField(max_length=30, unique=True)
    email = models.EmailField(unique=True)
    date_joined = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    last_login = models.DateTimeField(blank=True, null=True)
    group = models.CharField(max_length=30, choices=GROUP_CHOICES)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email']

    objects = UserManager()

    def __str__(self):
        return self.username

# second table: Farmer is related with User by userid, one userid can only match one farmer profile

class Farmer(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='farmer_profile')
    firstname = models.CharField(max_length=255, blank=False, null=False)
    middlename = models.CharField(max_length=255, blank=True, null=True)
    lastname = models.CharField(max_length=255, blank=False, null=False)
    farm_name = models.CharField(max_length=255, blank=False, null=False)
    country = models.CharField(max_length=255, blank=True, null=True)
    state = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=255, blank=True, null=True)
    farm_size = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, help_text="Size in hectares")
    harvest_season = models.CharField(max_length=255, blank=True, null=True)
    annual_production = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, help_text="Annual production in tons")
    cultivars = models.CharField(max_length=255, blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    cup_scores_received = models.TextField(blank=True, null=True)
    source_of_cup_scores = models.CharField(max_length=255, blank=True, null=True)
    quality_report_link = models.URLField(blank=True, null=True)
    processing_method = models.CharField(max_length=255, blank=True, null=True)
    processing_description = models.TextField(blank=True, null=True)
    profile_picture = models.ImageField(upload_to='farmer_profiles/', blank=True, null=True)
    bio = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    affiliation = models.CharField(max_length=255, blank=True, null=True)
    preferred_communication_method = models.CharField(max_length=50, choices=[('whatsapp', 'WhatsApp'), ('email', 'Email')], blank=True, null=True)
    main_role = models.CharField(max_length=50, choices=[('owner', 'Owner'), ('manager', 'Manager'), ('worker', 'Worker')], blank=True, null=True)

    profile_completed = models.BooleanField(
        default=False)  # this + all bools below are used to indicate required orientation task completion
    storytelling_workshop = models.BooleanField(default=False)
    video_pricing = models.BooleanField(default=False)
    video_intl = models.BooleanField(default=False)
    video_comm_tips = models.BooleanField(default=False)
    video_relationships = models.BooleanField(default=False)
    video_perceptions = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.firstname} {self.lastname} - {self.farm_name}'
class Roaster(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='roaster_profile')
    company_name = models.CharField(max_length=255, blank=False, null=True)
    country = models.CharField(max_length=100, blank=False, null=True)
    state = models.CharField(max_length=100, blank=False, null=True)
    city = models.CharField(max_length=100, blank=False, null=True)
    bio = models.TextField(blank=False, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    min_lot_size = models.PositiveIntegerField(blank=False, null=True)
    annual_throughput = models.PositiveIntegerField(blank=False, null=True)
    origins_interested = models.TextField(blank=False, null=True)
    coffee_types_interested = models.TextField(blank=False, null=True)
    profile_picture = models.ImageField(upload_to='roaster_profiles/', blank=True, null=True)

    def save(self, *args, **kwargs):
        try:
            # Get the existing roaster object from the database
            old_profile = Roaster.objects.get(pk=self.pk)
            if old_profile.profile_picture and self.profile_picture != old_profile.profile_picture:
                # If a new profile picture is being uploaded, delete the old one
                old_profile.profile_picture.delete(save=False)
        except Roaster.DoesNotExist:
            # No old profile exists, nothing to delete
            pass

        super(Roaster, self).save(*args, **kwargs)
    def __str__(self):
        return self.company_name    # def clean(self):
    #     if self.user.group != 'roaster':
    #         raise ValidationError('The user must be a roaster to add a RoasterProfile.')
# third table: farmerphoto is related with user by userid, one can only input data into it if user group is farmer
class FarmerPhoto(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='farmer_photos')
    photo = models.ImageField(upload_to='farmer_photos/', null=True, blank=True)
    #order = models.PositiveIntegerField(null=True, blank=True)

    def __str__(self):
        return f"Photo {self.id} for {self.user.username}"
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        if self.photo:
            self.photo.file.seek(0)
            img = Image.open(self.photo.path)
            max_size = (200, 200)  # Maximum width and height

            if img.height > max_size[1] or img.width > max_size[0]:
                img.thumbnail(max_size, Image.Resampling.LANCZOS)
                print(f"Resized image {self.photo.file} {img.format}")
                img.save(self.photo.path, format=f"{img.format}", quality=90)

    
    

    # def clean(self):
    #     if self.user.group != 'farmer':
    #         raise ValidationError('The user must be a farmer to add a FarmerPhoto.')


class RoasterPhoto(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='roaster_photos')
    photo = models.ImageField(upload_to='roaster_photos/')

    def __str__(self):
        return f"Photo {self.id} for {self.user.username}"

    # def clean(self):
    #     if self.user.group != 'roaster':
    #         raise ValidationError('The user must be a roaster to add a RoasterPhoto.')

#Table 4: meeting request, a mutual table for both farmer and roaster
class MeetingRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected')
    ]

    id = models.AutoField(primary_key=True)
    requester = models.ForeignKey(User, on_delete=models.CASCADE, related_name='meeting_requests_made')
    requestee = models.ForeignKey(User, on_delete=models.CASCADE, related_name='meeting_requests_received')
    proposed_date = models.DateTimeField()
    message = models.TextField(blank=True, null=True)  # Add this line to include the message field
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Meeting request from {self.requester.username} to {self.requestee.username}"

    # def clean(self):
    #     if self.requester.group == self.requestee.group:
    #         raise ValidationError('Meeting requests must be between a farmer and a roaster.')

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
