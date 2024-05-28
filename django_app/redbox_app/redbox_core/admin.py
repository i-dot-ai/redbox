from django.contrib import admin

from . import models


class UserResource(admin.ModelAdmin):
    fields = ["email", "is_superuser", "is_staff", "last_login"]
    list_display = ["email", "is_superuser", "is_staff", "last_login"]


class FileResource(admin.ModelAdmin):
    list_display = ["original_file_name", "user", "status"]


class ChatMessageInline(admin.StackedInline):
    model = models.ChatMessage
    extra = 1


class ChatHistoryAdmin(admin.ModelAdmin):
    inlines = [ChatMessageInline]
    list_display = ["name", "users"]
    list_filter = ["users"]


admin.site.register(models.User, UserResource)
admin.site.register(models.File, FileResource)
admin.site.register(models.ChatHistory, ChatHistoryAdmin)
