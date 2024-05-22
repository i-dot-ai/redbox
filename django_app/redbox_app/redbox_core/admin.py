from django.contrib import admin

from . import models


class UserResource(admin.ModelAdmin):
    fields = ["email", "is_superuser", "is_staff"]


class FileResource(admin.ModelAdmin):
    list_display = ["original_file_name", "user", "processing_status", "original_file", "core_file_uuid"]


admin.site.register(models.User, UserResource)
admin.site.register(models.File, FileResource)
admin.site.register(models.ChatHistory)
admin.site.register(models.ChatMessage)
