import csv

from django.contrib import admin
from django.http import HttpResponse
from import_export.admin import ImportMixin

from . import models


class UserAdmin(admin.ModelAdmin):
    fields = ["email", "business_unit", "grade", "profession", "is_superuser", "is_staff", "last_login"]
    list_display = ["email", "business_unit", "grade", "profession", "is_superuser", "is_staff", "last_login"]
    list_filter = ["business_unit", "grade", "profession"]
    date_hierarchy = "last_login"


class BusinessUnitAdmin(ImportMixin, admin.ModelAdmin):
    fields = ["name"]
    list_display = ["name"]

    class Meta:
        model = models.BusinessUnit
        fields = ["name"]
        import_id_fields = ["name"]


class FileAdmin(admin.ModelAdmin):
    list_display = ["original_file_name", "user", "status", "created_at", "last_referenced"]
    list_filter = ["user", "status"]
    date_hierarchy = "created_at"


class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ["chat_history", "get_user", "text", "role", "created_at"]
    list_filter = ["role", "chat_history__users"]
    date_hierarchy = "created_at"

    @admin.display(ordering="chat_history__users", description="User")
    def get_user(self, obj):
        return obj.chat_history.users


class ChatMessageInline(admin.StackedInline):
    model = models.ChatMessage
    ordering = ("modified_at",)
    readonly_fields = ["modified_at", "source_files"]
    extra = 1


class ChatHistoryAdmin(admin.ModelAdmin):
    def export_as_csv(self, request, queryset):  # noqa:ARG002
        history_field_names = [field.name for field in models.ChatHistory._meta.fields]  # noqa:SLF001
        message_field_names = [field.name for field in models.ChatMessage._meta.fields]  # noqa:SLF001

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = "attachment; filename=chathistory.csv"
        writer = csv.writer(response)

        writer.writerow(history_field_names + message_field_names)
        for chat_history in queryset:
            for chat_message in chat_history.chatmessage_set.all():
                writer.writerow(
                    [getattr(chat_history, field) for field in history_field_names]
                    + [getattr(chat_message, field) for field in message_field_names]
                )

        return response

    export_as_csv.short_description = "Export Selected"
    fields = ["name", "users"]
    inlines = [ChatMessageInline]
    list_display = ["name", "users", "created_at"]
    list_filter = ["users"]
    date_hierarchy = "created_at"
    actions = ["export_as_csv"]


admin.site.register(models.User, UserAdmin)
admin.site.register(models.File, FileAdmin)
admin.site.register(models.ChatHistory, ChatHistoryAdmin)
admin.site.register(models.ChatMessage, ChatMessageAdmin)
admin.site.register(models.BusinessUnit, BusinessUnitAdmin)
