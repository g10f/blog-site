from django.contrib import admin

from oidc.models import UserProfile, RoleGroup


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    search_fields = ("user__username",)
    ordering = ("user",)
    list_display = ('user', 'subject')


@admin.register(RoleGroup)
class RoleGroupAdmin(admin.ModelAdmin):
    search_fields = ("group__name", "role")
    ordering = ("group",)
    list_display = ('group', 'role', 'is_superuser', 'is_staff')
