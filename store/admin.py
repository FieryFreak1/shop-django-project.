# store/admin.py

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import AdminProfile, CustomUser


admin.site.register(AdminProfile)

class CustomUserAdmin(UserAdmin):

    pass


admin.site.register(CustomUser, CustomUserAdmin)