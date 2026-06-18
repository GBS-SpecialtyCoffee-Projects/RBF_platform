from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone
from django_countries import countries
from rbf_platform.storage_backends import ProfileStorage,PhotoStorage, ProfileStorageRoaster,get_profile_storage, get_roaster_profile_storage, get_photo_storage
from PIL import Image
from phonenumbers import COUNTRY_CODE_TO_REGION_CODE

COUNTRY_CHOICES = [ (country.name, country.name) for country in countries ]


# For admin purpose
class UserManager(BaseUserManager):
    def create_user(self, email, password=None, username=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)  # This hashes the password
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        return self.create_user(email, password, **extra_fields)

# first table: User
class User(AbstractBaseUser, PermissionsMixin):
    GROUP_CHOICES = [
        ('farmer', 'Farmer'),
        ('roaster', 'Buyer')
    ]

    id = models.AutoField(primary_key=True)
    username = models.CharField(max_length=30, unique=True, blank=True, null=True)
    email = models.EmailField(unique=True)
    date_joined = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    last_login = models.DateTimeField(blank=True, null=True)
    group = models.CharField(max_length=30, choices=GROUP_CHOICES)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return self.email

# second table: Farmer is related with User by userid, one userid can only match one farmer profile

class Season(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
    
class ProcessingMethod(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
    
class CupScore(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
    
class Role(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class BuyerFunctions(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class Farmer(models.Model):
    SIZE_CHOICES = [
        ('hectare', 'Hectare'),
        ('acres', 'Acres'), 
    ]

    PROD_UNIT_CHOICES = [
        ('kilograms', 'Kilograms'),
    ]

    HARVEST_CHOICES = [
        ('spring','spring'),
        ('summer','summer'),
        ('autumn','autumn'),        
        ('winter','winter'),  
    ]
    # error for previous country code choices, but it doesnt need to be called anymore
    # COUNTRY_REGION_CODES = [ (f'{code}', f'{item} (+{code})') for code in COUNTRY_CODE_TO_REGION_CODE for item in COUNTRY_CODE_TO_REGION_CODE[code] ]

    PROCESSING_METHOD_CHOICES = [
        ('Washed','Washed'),
        ('Natural','Natural'),
        ('Honey','Honey'),
        ('Semi-Washed','Semi-Washed'),
        ('Controlled','Controlled'),
        ('Anaerobic','Anaerobic'),
    ]
    


    id = models.AutoField(primary_key=True)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='farmer_profile')
    firstname = models.CharField(max_length=255, blank=False, null=False)
    middlename = models.CharField(max_length=255, blank=True, null=True)
    lastname = models.CharField(max_length=255, blank=False, null=False)
    farm_name = models.CharField(max_length=255, blank=False, null=False)
    country = models.TextField(default='United States of America',choices=COUNTRY_CHOICES, blank=True, null=False)
    state = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=255, blank=True, null=True)
    farm_size = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, help_text="Size in hectares")
    farm_size_unit = models.CharField(max_length=255,choices=SIZE_CHOICES, blank=True, null=True)
    # harvest_season = models.CharField(max_length=255,choices=HARVEST_CHOICES, null=True)
    harvest_season = models.ManyToManyField(Season, blank=True)
    annual_production = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, help_text="Annual production in tons")
    annual_production_unit = models.CharField(max_length=255, choices=PROD_UNIT_CHOICES, default='kilograms', blank=True, null=True)
    cultivars = models.CharField(max_length=255, blank=True, null=True)
    country_code = models.CharField(max_length=255, blank=True, null=True, default='US (+1)')
    phone_number = models.CharField(max_length=255, blank=True, null=True)
    cup_scores_received = models.ManyToManyField(CupScore, blank=True)
    source_of_cup_scores = models.CharField(max_length=255, blank=True, null=True)
    quality_report_link = models.URLField(blank=True, null=True)
    processing_method = models.ManyToManyField(ProcessingMethod, blank=True)
    processing_description = models.TextField(blank=True, null=True)
    # profile_picture = models.ImageField(upload_to='farmer_profiles/', blank=True, null=True)
    profile_picture = models.ImageField(storage=get_profile_storage,blank=True, null=True)
    bio = models.TextField(blank=True, null=True)
    header_image = models.ImageField(storage=get_profile_storage, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    affiliation = models.CharField(max_length=255, blank=True, null=True)
    preferred_communication_method = models.CharField(max_length=50, choices=[('whatsapp', 'WhatsApp'), ('email', 'Email')], blank=True, null=True)
    main_role = models.CharField(max_length=50, choices=[('owner', 'Owner'), ('manager', 'Manager'), ('worker', 'Worker')], blank=True, null=True)  # deprecated — will be removed after data migration
    main_roles = models.ManyToManyField(Role, blank=True)

    profile_completed = models.BooleanField(
        default=False)  # this + all bools below are used to indicate required orientation task completion
    storytelling_workshop = models.BooleanField(default=False)
    video_pricing = models.BooleanField(default=False)
    video_intl = models.BooleanField(default=False)
    video_comm_tips = models.BooleanField(default=False)
    video_relationships = models.BooleanField(default=False)
    video_perceptions = models.BooleanField(default=False)
    is_details_filled = models.BooleanField(default=False)
    is_member_organization = models.BooleanField(default=False,choices=[(True, 'Yes'), (False, 'No')])
    member_organization_name = models.CharField(max_length=255, blank=True, null=True)
    is_profile_published = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.firstname} {self.lastname} - {self.farm_name}'
class Roaster(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='roaster_profile')
    firstname = models.CharField(max_length=255, blank=False, null=True)
    middlename = models.CharField(max_length=255, blank=True, null=True)
    lastname = models.CharField(max_length=255, blank=False, null=True)
    job_title = models.CharField(max_length=255, blank=False, null=True)
    company_name = models.CharField(max_length=255, blank=False, null=True)
    company_website = models.URLField(blank=True, null=True)
    company_socials = models.URLField(blank=True, null=True)
    country = models.TextField(default='United States of America',choices=COUNTRY_CHOICES, blank=True, null=False)
    state = models.CharField(max_length=100, blank=False, null=True)
    city = models.CharField(max_length=100, blank=False, null=True)
    bio = models.TextField(blank=True, null=True)
    company_functions = models.ManyToManyField(BuyerFunctions, blank=True)
    coffee_purchase_involvement = models.BooleanField(default=False, choices=[(True, 'Yes'), (False, 'No')])
    purchase_volume = models.DecimalField(max_digits=10,decimal_places=2, blank=False, null=True)
    company_description = models.TextField(blank=False, null=True)
    company_approach = models.TextField(blank=False, null=True)
    company_goals = models.TextField(blank=False, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    min_lot_size = models.PositiveIntegerField(blank=False, null=True)
    annual_throughput = models.PositiveIntegerField(blank=False, null=True)
    origins_interested = models.TextField(blank=True, null=True)
    coffee_types_interested = models.TextField(blank=True, null=True)
    cup_scores_interested = models.ManyToManyField(CupScore, blank=True, related_name='interested_roasters')
    profile_picture = models.ImageField(storage=get_roaster_profile_storage,blank=True, null=True)
    country_code = models.CharField(max_length=255, blank=True, null=True, default='US (+1)')
    phone_number = models.CharField(max_length=255, blank=True, null=True)
    header_image = models.ImageField(storage=get_roaster_profile_storage, blank=True, null=True)
    is_details_filled = models.BooleanField(default=False)
    sourcing_prefs_filled = models.BooleanField(default=False)

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
    photo = models.ImageField(storage=get_photo_storage, blank=True, null=True)
    #order = models.PositiveIntegerField(null=True, blank=True)

    # def __str__(self):
    #     return f"Photo {self.id} for {self.user.username}"
    
    # def save(self, *args, **kwargs):
    #     super().save(*args, **kwargs)

    #     if self.photo:
    #         self.photo.file.seek(0)
    #         img = Image.open(self.photo.path)
    #         max_size = (200, 200)  # Maximum width and height

    #         if img.height > max_size[1] or img.width > max_size[0]:
    #             img.thumbnail(max_size, Image.Resampling.LANCZOS)
    #             print(f"Resized image {self.photo.file} {img.format}")
    #             img.save(self.photo.path, format=f"{img.format}", quality=90)

    
    

    # def clean(self):
    #     if self.user.group != 'farmer':
    #         raise ValidationError('The user must be a farmer to add a FarmerPhoto.')


class RoasterPhoto(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='roaster_photos')
    photo = models.ImageField(storage=get_photo_storage, blank=True, null=True)

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
    proposed_date = models.DateTimeField(blank=True, null=True)
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

    def status_for(self, viewer):
        """Connection state of this request from `viewer`'s perspective."""
        if self.status == 'accepted':
            return 'connected'
        if self.requester_id == viewer.id:
            return 'sent'
        return 'incoming'

    @staticmethod
    def active_between(user_a, user_b):
        """Return the active (pending/accepted) request between two users, or None."""
        return MeetingRequest.objects.filter(
            models.Q(requester=user_a, requestee=user_b)
            | models.Q(requester=user_b, requestee=user_a),
            status__in=['pending', 'accepted'],
        ).first()

    @staticmethod
    def status_sets_for(user):
        """Return (connected, sent, incoming) sets of the other user's id for `user`."""
        connected, sent, incoming = set(), set(), set()
        rows = MeetingRequest.objects.filter(
            models.Q(requester=user) | models.Q(requestee=user),
            status__in=['pending', 'accepted'],
        ).values('requester_id', 'requestee_id', 'status')
        for row in rows:
            other = (
                row['requestee_id']
                if row['requester_id'] == user.id
                else row['requester_id']
            )
            if row['status'] == 'accepted':
                connected.add(other)
            elif row['requester_id'] == user.id:
                sent.add(other)
            else:
                incoming.add(other)
        return connected, sent, incoming


class Connection(models.Model):
    """First-class relationship between two users (a roaster and a farmer).

    One row per unordered pair (``user_a.id < user_b.id``) enforced by a unique
    constraint, with ``initiator`` recording who sent the request. Replaces the
    overloaded use of ``MeetingRequest`` for representing relationships.
    """

    PENDING = 'pending'
    ACTIVE = 'active'
    DECLINED = 'declined'
    WITHDRAWN = 'withdrawn'
    DISCONNECTED = 'disconnected'
    BLOCKED = 'blocked'
    STATUS_CHOICES = [
        (PENDING, 'Pending'),
        (ACTIVE, 'Active'),
        (DECLINED, 'Declined'),
        (WITHDRAWN, 'Withdrawn'),
        (DISCONNECTED, 'Disconnected'),
        (BLOCKED, 'Blocked'),
    ]
    # Statuses that block a new request between the same pair.
    LIVE_STATUSES = (PENDING, ACTIVE)
    # Cap only *outgoing pending* invites — a spam guard, not a relationship cap.
    MAX_PENDING_SENT = 25

    user_a = models.ForeignKey(User, on_delete=models.CASCADE, related_name='+')
    user_b = models.ForeignKey(User, on_delete=models.CASCADE, related_name='+')
    initiator = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='connections_initiated'
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=PENDING, db_index=True
    )
    message = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user_a', 'user_b'], name='uniq_connection_pair'),
        ]
        indexes = [models.Index(fields=['status'])]
        ordering = ['-updated_at']

    def __str__(self):
        return f"Connection({self.user_a_id}-{self.user_b_id}: {self.status})"

    # --- helpers -----------------------------------------------------------
    @staticmethod
    def _ordered(u1, u2):
        """Return the pair as (low_id_user, high_id_user)."""
        return (u1, u2) if u1.id < u2.id else (u2, u1)

    @classmethod
    def between(cls, u1, u2):
        """Return the Connection row for this unordered pair, or None."""
        a, b = cls._ordered(u1, u2)
        return cls.objects.filter(user_a=a, user_b=b).first()

    def other(self, user):
        return self.user_b if self.user_a_id == user.id else self.user_a

    @property
    def recipient(self):
        return self.other(self.initiator)

    def involves(self, user):
        return user.id in (self.user_a_id, self.user_b_id)

    def status_for(self, viewer):
        """Relationship state from ``viewer``'s perspective (for templates)."""
        if self.status == self.ACTIVE:
            return 'connected'
        if self.status == self.PENDING:
            return 'sent' if self.initiator_id == viewer.id else 'incoming'
        return 'none'

    # --- state machine -----------------------------------------------------
    @classmethod
    def request(cls, initiator, recipient, message=''):
        """Create or re-open a pending connection. Idempotent if already live."""
        conn = cls.between(initiator, recipient)
        if conn and conn.status in cls.LIVE_STATUSES:
            return conn  # already pending/active — no-op
        if conn is None:
            a, b = cls._ordered(initiator, recipient)
            conn = cls(user_a=a, user_b=b)
        conn.initiator = initiator
        conn.status = cls.PENDING
        if message:
            conn.message = message
        conn.save()
        return conn

    def accept(self):
        self.status = self.ACTIVE
        self.save(update_fields=['status', 'updated_at'])

    def decline(self):
        self.status = self.DECLINED
        self.save(update_fields=['status', 'updated_at'])

    def withdraw(self):
        self.status = self.WITHDRAWN
        self.save(update_fields=['status', 'updated_at'])

    def disconnect(self):
        self.status = self.DISCONNECTED
        self.save(update_fields=['status', 'updated_at'])

    # --- bulk lookups ------------------------------------------------------
    @classmethod
    def status_sets_for(cls, user):
        """Return (connected, sent, incoming) sets of the *other* user's id."""
        connected, sent, incoming = set(), set(), set()
        rows = cls.objects.filter(
            models.Q(user_a=user) | models.Q(user_b=user),
            status__in=cls.LIVE_STATUSES,
        ).values('user_a_id', 'user_b_id', 'initiator_id', 'status')
        for row in rows:
            other = row['user_b_id'] if row['user_a_id'] == user.id else row['user_a_id']
            if row['status'] == cls.ACTIVE:
                connected.add(other)
            elif row['initiator_id'] == user.id:
                sent.add(other)
            else:
                incoming.add(other)
        return connected, sent, incoming

    @classmethod
    def pending_sent_count(cls, user):
        """Outgoing pending invites — the figure the spam guard caps."""
        return cls.objects.filter(initiator=user, status=cls.PENDING).count()


class Conversation(models.Model):
    roaster = models.ForeignKey(User, on_delete=models.CASCADE, related_name='conversations_as_roaster')
    farmer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='conversations_as_farmer')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('roaster', 'farmer')
        ordering = ['-updated_at']

    def __str__(self):
        return f"Conversation: {self.roaster.email} <-> {self.farmer.email}"

    def other_participant(self, user):
        return self.farmer if user == self.roaster else self.roaster

    def has_participant(self, user):
        return user == self.roaster or user == self.farmer


class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_messages_sent')
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Msg {self.id} from {self.sender.email} in conv {self.conversation_id}"


class Language (models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
    

class Story(models.Model):
    # language_list = [ (language.name,language.name) for language in Language.objects.all()]
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='farmer_stories')
    farmer = models.ForeignKey(Farmer, on_delete=models.SET_NULL, null=True, blank=True, related_name='farmer_stories')
    language = models.ForeignKey(Language, on_delete=models.SET_NULL, null=True, blank=True, related_name='story_languages')
    # language = models.CharField(max_length=255, choices=language_list, null=True, blank=True)
    story_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    

    # def __str__(self):
    #     return self.title


class Resource(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True)
    summary = models.CharField(max_length=500, blank=True)
    body = models.TextField()
    cover_image = models.ImageField(
        upload_to='resources/', blank=True, null=True,
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='authored_resources',
    )
    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class AuditAction(models.TextChoices):
    UPDATE_PROFILE = 'update_profile', 'Updated profile'
    UPDATE_STATUS = 'update_status', 'Updated status'
    UPLOAD_PHOTO = 'upload_photo', 'Uploaded photo'
    DELETE_PHOTO = 'delete_photo', 'Deleted photo'
    ADD_STORY = 'add_story', 'Added story'
    UPDATE_STORY = 'update_story', 'Updated story'
    PUBLISH_PROFILE = 'publish_profile', 'Published profile'
    REQUEST_MEETING = 'request_meeting', 'Requested meeting'
    MANAGE_MEETING = 'manage_meeting', 'Managed meeting request'
    CREATE_ACCOUNT = 'create_account', 'Created account'
    CREATE_ADMIN = 'create_admin', 'Created admin'
    TOGGLE_ADMIN = 'toggle_admin', 'Toggled admin access'
    COMPLETE_DETAILS = 'complete_details', 'Completed profile details'
    UPDATE_HEADER = 'update_header', 'Updated header image'


class AuditLog(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
    )
    action = models.CharField(max_length=50, choices=AuditAction.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user} — {self.get_action_display()}'


class Forum(models.Model):
    """A hosted relationship-building forum (event) that staff set up.

    A forum has many time windows; users sign up and (in later phases)
    schedule meetings with their connections inside those windows.
    """

    IN_PERSON = 'in_person'
    VIRTUAL = 'virtual'
    HYBRID = 'hybrid'
    FORMAT_CHOICES = [
        (IN_PERSON, 'In person'),
        (VIRTUAL, 'Virtual'),
        (HYBRID, 'Hybrid'),
    ]

    DRAFT = 'draft'
    PUBLISHED = 'published'
    COMPLETED = 'completed'
    CANCELLED = 'cancelled'
    STATUS_CHOICES = [
        (DRAFT, 'Draft'),
        (PUBLISHED, 'Published'),
        (COMPLETED, 'Completed'),
        (CANCELLED, 'Cancelled'),
    ]

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    format = models.CharField(max_length=20, choices=FORMAT_CHOICES, default=HYBRID)
    location = models.CharField(max_length=255, blank=True)
    link = models.URLField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=DRAFT)
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='forums_created',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    @property
    def window_count(self):
        return self.windows.count()

    @property
    def is_open(self):
        """Whether the forum is currently open for signups."""
        return self.status == self.PUBLISHED

    @property
    def is_over(self):
        """True once the forum has windows and all of them have ended."""
        if not self.windows.exists():
            return False
        return not self.windows.filter(ends_at__gt=timezone.now()).exists()

    def is_signed_up(self, user):
        return self.signups.filter(user=user).exists()

    @property
    def next_window_start(self):
        """Start time of the soonest future window, or None."""
        window = self.windows.filter(starts_at__gt=timezone.now()).first()
        return window.starts_at if window else None

    @classmethod
    def next_upcoming(cls):
        """The soonest published forum that has a window starting in the
        future, or None if there isn't one."""
        return (
            cls.objects.filter(
                status=cls.PUBLISHED,
                windows__starts_at__gt=timezone.now(),
            )
            .distinct()
            .order_by('windows__starts_at')
            .first()
        )

    @classmethod
    def soonest_to_join(cls, viewer, other):
        """The soonest published forum with a future window that `other` is
        signed up for but `viewer` is not — used to nudge `viewer` to join the
        same forum so they can schedule a meeting. None if there isn't one."""
        return (
            cls.objects.filter(
                status=cls.PUBLISHED,
                windows__starts_at__gt=timezone.now(),
                signups__user=other,
            )
            .exclude(signups__user=viewer)
            .distinct()
            .order_by('windows__starts_at')
            .first()
        )


class ForumWindow(models.Model):
    """One available time block within a Forum."""

    forum = models.ForeignKey(
        Forum, on_delete=models.CASCADE, related_name='windows',
    )
    label = models.CharField(max_length=120, blank=True)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()

    class Meta:
        ordering = ['starts_at']

    def __str__(self):
        return f'{self.forum.title}: {self.starts_at:%b %d %H:%M}'

    def clean(self):
        if self.starts_at and self.ends_at and self.ends_at <= self.starts_at:
            raise ValidationError('Window end time must be after its start time.')


class ForumSignup(models.Model):
    """A user's signup to attend a Forum."""

    forum = models.ForeignKey(
        Forum, on_delete=models.CASCADE, related_name='signups',
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='forum_signups',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ('forum', 'user')

    def __str__(self):
        return f'{self.user} → {self.forum.title}'


class ForumMeeting(models.Model):
    """A proposed/confirmed meeting between two connected users during a
    specific ForumWindow that both are signed up for."""

    PROPOSED = 'proposed'
    CONFIRMED = 'confirmed'
    DECLINED = 'declined'
    CANCELLED = 'cancelled'
    STATUS_CHOICES = [
        (PROPOSED, 'Proposed'),
        (CONFIRMED, 'Confirmed'),
        (DECLINED, 'Declined'),
        (CANCELLED, 'Cancelled'),
    ]
    LIVE_STATUSES = (PROPOSED, CONFIRMED)

    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name='meetings',
    )
    window = models.ForeignKey(
        ForumWindow, on_delete=models.CASCADE, related_name='meetings',
    )
    proposed_by = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='forum_meetings_proposed',
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=PROPOSED, db_index=True,
    )
    meeting_link = models.CharField(max_length=500, blank=True)
    invite_sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f'Meeting({self.conversation_id} @ window {self.window_id}: {self.status})'

    @property
    def forum(self):
        return self.window.forum

    @property
    def invitee(self):
        """The participant who must respond (not the proposer)."""
        return self.conversation.other_participant(self.proposed_by)

    # --- state machine -----------------------------------------------------
    def confirm(self):
        self.status = self.CONFIRMED
        self.save(update_fields=['status', 'updated_at'])

    def decline(self):
        self.status = self.DECLINED
        self.save(update_fields=['status', 'updated_at'])

    def cancel(self):
        self.status = self.CANCELLED
        self.save(update_fields=['status', 'updated_at'])

    @classmethod
    def proposable_windows(cls, conversation):
        """Future windows the pair can meet in: from published forums *both* are
        signed up for, minus windows already holding a live meeting in this
        conversation. Past windows (and so ended forums) are excluded."""
        roaster_forums = ForumSignup.objects.filter(
            user=conversation.roaster, forum__status=Forum.PUBLISHED,
        ).values_list('forum_id', flat=True)
        shared_forum_ids = ForumSignup.objects.filter(
            user=conversation.farmer, forum_id__in=roaster_forums,
        ).values_list('forum_id', flat=True)
        taken = cls.objects.filter(
            conversation=conversation, status__in=cls.LIVE_STATUSES,
        ).values_list('window_id', flat=True)
        return (
            ForumWindow.objects.filter(
                forum_id__in=shared_forum_ids, starts_at__gt=timezone.now(),
            )
            .exclude(id__in=taken)
            .select_related('forum')
        )

    @classmethod
    def for_display(cls, conversation):
        """Meetings to show in a conversation, excluding any whose forum has
        fully ended (no window ending in the future)."""
        return (
            conversation.meetings.filter(
                window__forum__windows__ends_at__gt=timezone.now(),
            )
            .select_related('window', 'window__forum', 'proposed_by')
            .distinct()
        )

    @classmethod
    def confirmed_upcoming(cls):
        """Confirmed meetings whose window is still in the future — the ones
        platform admins need to set up a call for."""
        return (
            cls.objects.filter(
                status=cls.CONFIRMED, window__starts_at__gt=timezone.now(),
            )
            .select_related(
                'conversation', 'conversation__roaster', 'conversation__farmer',
                'window', 'window__forum',
            )
            .order_by('window__starts_at')
        )
