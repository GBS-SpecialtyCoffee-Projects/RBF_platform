from django.conf import settings
from django.core.files.storage import FileSystemStorage
from storages.backends.s3boto3 import S3Boto3Storage

def get_profile_storage():
    if settings.DEBUG:
        return FileSystemStorage()
    else:
        return ProfileStorage()


class StaticStorage(S3Boto3Storage):
    location = 'static'
    default_acl = 'public-read'
    file_overwrite = True

class _MediaStorage(S3Boto3Storage):
    default_acl = 'public-read'
    file_overwrite = False

class ProfileStorage(_MediaStorage):
    location = 'media/farmer_profiles'

class ProfileStorageRoaster(_MediaStorage):
    location = 'media/roaster_profiles'

class PhotoStorage(_MediaStorage):
    location = 'media/farmer_photos'

class PhotoStorageRoaster(_MediaStorage):
    location = 'media/roaster_photos'



