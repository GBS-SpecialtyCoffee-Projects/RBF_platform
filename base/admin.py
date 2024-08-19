from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Farmer, FarmerPhoto, MeetingRequest, RoasterPhoto,Roaster
from django.contrib.auth.models import Group


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
    list_display = ('username', 'email', 'group', 'is_staff')
    search_fields = ('username', 'email')
    list_filter = ('group', 'is_staff')
    ordering = ('username',)
    filter_horizontal = ()  # Remove 'groups' and 'user_permissions'

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
