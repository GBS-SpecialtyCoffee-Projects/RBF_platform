from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Farmer, FarmerPhoto, MeetingRequest, RoasterPhoto,Roaster

class CustomUserAdmin(BaseUserAdmin):
    fieldsets = (
        (None, {'fields': ('username', 'email', 'password')}),
        ('Personal info', {'fields': ('firstname', 'middlename', 'lastname', 'phone_number', 'group')}),
        ('Permissions', {'fields': ('is_staff', 'is_superuser')}),
        ('Important dates', {'fields': ('last_login', 'date_joined', 'updated_date')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2'),
        }),
    )
    list_display = ('username', 'email', 'firstname', 'lastname', 'group', 'is_staff')
    search_fields = ('username', 'email', 'firstname', 'lastname')
    list_filter = ('group', 'is_staff')
    ordering = ('username',)
    filter_horizontal = ()  # Remove 'groups' and 'user_permissions'

admin.site.register(User, CustomUserAdmin)




@admin.register(Farmer)
class FarmerAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'farm_name', 'location', 'size', 'affiliation', 'created_at', 'updated_at')
    search_fields = ('farm_name', 'location', 'user__username')
    list_filter = ('affiliation', 'created_at')


@admin.register(FarmerPhoto)
class FarmerPhotoAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'photo', 'order')
    search_fields = ('user__username', 'photo')
    list_filter = ('user__username',)
    ordering = ('user', 'order')
    readonly_fields = ('photo',)

    def formfield_for_dbfield(self, db_field, **kwargs):
        if db_field.name == 'photo':
            kwargs['widget'] = admin.widgets.AdminFileWidget
        return super(FarmerPhotoAdmin, self).formfield_for_dbfield(db_field, **kwargs)

@admin.register(Roaster)
class RoasterAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'company_name', 'location', 'created_at', 'updated_at')
    search_fields = ('company_name', 'location', 'user__username')
    list_filter = ('location', 'created_at')

@admin.register(RoasterPhoto)
class RoasterPhotoAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'photo', 'order')
    search_fields = ('user__username', 'photo')
    list_filter = ('user__username',)
    ordering = ('user', 'order')
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
