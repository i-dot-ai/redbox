from django.contrib import admin

from . import models


class FileResource(admin.ModelAdmin):
    list_display = ["original_file_name", "user", "processing_status", "original_file", "core_file_uuid"]


admin.site.register(models.User)
admin.site.register(models.File, FileResource)
