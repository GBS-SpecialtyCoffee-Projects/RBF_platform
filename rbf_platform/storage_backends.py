from django.conf import settings
from storages.backends.s3boto3 import S3Boto3Storage


class StaticStorage(S3Boto3Storage):
    location = 'static'
    default_acl = 'public-read'

class ProfileStorage(S3Boto3Storage,):
    location = 'media/farmer_profiles'
    default_acl = 'public-read'
    file_overwrite = False

class PhotoStorage(S3Boto3Storage,):
    location = 'media/farmer_photos'
    default_acl = 'public-read'
    file_overwrite = False



