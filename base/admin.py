# admin.py

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Farmer, FarmerPhoto, MeetingRequest, RoasterPhoto, Roaster
from django.contrib.auth.models import Group
from django.db.models import Count
from django.utils.safestring import mark_safe

class CustomUserAdmin(BaseUserAdmin):
    fieldsets = (
        (None, {'fields': ('username', 'email', 'password')}),
        ('Personal info', {'fields': ('group',)}),
        ('Permissions', {'fields': ('is_staff', 'is_superuser')}),
        ('Important dates', {'fields': ('last_login', 'date_joined', 'updated_date')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2'),
        }),
    )
    list_display = ('username', 'email', 'group', 'is_staff', 'display_summary_stats')
    search_fields = ('username', 'email')
    list_filter = ('group', 'is_staff')
    ordering = ('username',)

    def display_summary_stats(self, obj=None):
        # This will display summary data as a row in the list display
        total_users = User.objects.count()
        total_farmers = Farmer.objects.count()
        total_roasters = Roaster.objects.count()
        active_users = User.objects.filter(last_login__isnull=False).count()
        inactive_users = total_users - active_users

        # Meeting Requests Summary
        meeting_requests_summary = MeetingRequest.objects.values('status').annotate(count=Count('status'))
        meeting_requests_summary_display = ", ".join([f"{item['status']}: {item['count']}" for item in meeting_requests_summary])

        return f"Users: {total_users}, Farmers: {total_farmers}, Roasters: {total_roasters}, " \
               f"Active: {active_users}, Inactive: {inactive_users}, " \
               f"Meeting Requests: {meeting_requests_summary_display}"

    display_summary_stats.short_description = 'Summary Statistics'

# Registering the CustomUserAdmin
admin.site.register(User, CustomUserAdmin)
admin.site.unregister(Group)


@admin.register(Farmer)
class FarmerAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'farm_name', 'country', 'state', 'city',  'created_at', 'updated_at')
    search_fields = ('farm_name', 'country','state','city', 'user__username')
    list_filter = ('affiliation', 'created_at')


@admin.register(FarmerPhoto)
class FarmerPhotoAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'photo', )
    search_fields = ('user__username', 'photo')
    list_filter = ('user__username',)
    ordering = ('user', )
    readonly_fields = ('photo',)

    def formfield_for_dbfield(self, db_field, **kwargs):
        if db_field.name == 'photo':
            kwargs['widget'] = admin.widgets.AdminFileWidget
        return super(FarmerPhotoAdmin, self).formfield_for_dbfield(db_field, **kwargs)

@admin.register(Roaster)
class RoasterAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'company_name',  'created_at', 'updated_at')
    search_fields = ('company_name', 'country','state','city', 'user__username')
    list_filter = ('created_at',)

@admin.register(RoasterPhoto)
class RoasterPhotoAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'photo', )
    search_fields = ('user__username', 'photo')
    list_filter = ('user__username',)
    ordering = ('user', )
    readonly_fields = ('photo',)

    def formfield_for_dbfield(self, db_field, **kwargs):
        if db_field.name == 'photo':
            kwargs['widget'] = admin.widgets.AdminFileWidget
        return super(RoasterPhotoAdmin, self).formfield_for_dbfield(db_field, **kwargs)

@admin.register(MeetingRequest)
class MeetingRequestAdmin(admin.ModelAdmin):
    list_display = ('requester', 'requestee', 'proposed_date', 'status', 'created_at', 'updated_at')
    search_fields = ('requester__username', 'requestee__username', 'status')
    list_filter = ('status', 'created_at')
    ordering = ('created_at',)
