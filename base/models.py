from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.conf import settings
from django.core.exceptions import ValidationError


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
    firstname = models.CharField(max_length=30)
    middlename = models.CharField(max_length=30, blank=True, null=True)
    lastname = models.CharField(max_length=30)
    username = models.CharField(max_length=30, unique=True)
    password = models.CharField(max_length=128)  # This is managed by AbstractBaseUser
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
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
    farm_name = models.CharField(max_length=255, blank=False, null=True)
    location = models.CharField(max_length=255, blank=False, null=True)
    bio = models.TextField(blank=False, null=True)
    size = models.CharField(max_length=255, blank=False, null=True)
    affiliation = models.CharField(max_length=255, blank=False, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.farm_name

    # def clean(self):
    #     if self.user.group != 'farmer':
    #         raise ValidationError('The user must be a farmer to add a FarmerProfile.')

class Roaster(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='roaster_profile')
    company_name = models.CharField(max_length=255, blank=False, null=True)
    location = models.CharField(max_length=255, blank=False, null=True)
    bio = models.TextField(blank=False, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    min_lot_size = models.PositiveIntegerField(blank=False, null=True)
    annual_throughput = models.PositiveIntegerField(blank=False, null=True)
    origins_interested = models.TextField(blank=False, null=True)
    coffee_types_interested = models.TextField(blank=False, null=True)

    def __str__(self):
        return self.company_name

    # def clean(self):
    #     if self.user.group != 'roaster':
    #         raise ValidationError('The user must be a roaster to add a RoasterProfile.')
# third table: farmerphoto is related with user by userid, one can only input data into it if user group is farmer
class FarmerPhoto(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='farmer_photos')
    photo = models.ImageField(upload_to='farmer_photos/')
    order = models.PositiveIntegerField()

    def __str__(self):
        return f"Photo {self.id} for {self.user.username}"

    # def clean(self):
    #     if self.user.group != 'farmer':
    #         raise ValidationError('The user must be a farmer to add a FarmerPhoto.')


class RoasterPhoto(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='roaster_photos')
    photo = models.ImageField(upload_to='roaster_photos/')
    order = models.PositiveIntegerField()

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