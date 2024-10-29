import csv
import json
import logging

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.db.models import QuerySet
from django.http import HttpResponse
from django.shortcuts import render
from django_q.tasks import async_task
from import_export.admin import ExportMixin, ImportExportMixin

from redbox_app.worker import ingest

from . import models
from .serializers import UserSerializer

logger = logging.getLogger(__name__)
User = get_user_model()


class ChatLLMBackendAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "provider",
        "is_default",
    ]

    class Meta:
        model = models.ChatLLMBackend


class UserAdmin(ImportExportMixin, admin.ModelAdmin):
    def export_as_json(self, request, queryset: QuerySet):  # noqa:ARG002
        user_data = UserSerializer(many=True).to_representation(queryset)
        response = HttpResponse(json.dumps(user_data), content_type="text/json")
        response["Content-Disposition"] = "attachment; filename=data-export.json"

        return response

    export_as_json.short_description = "Export Selected"
    actions = ["export_as_json"]

    search_fields = ["email"]

    fieldsets = [
        (
            None,
            {
                "fields": [
                    "email",
                    "name",
                    "ai_experience",
                    "business_unit",
                    "grade",
                    "profession",
                    "is_superuser",
                    "is_staff",
                    "last_login",
                    "ai_settings",
                    "is_developer",
                ]
            },
        ),
        # Additional fields for sign-up form
        ("Page 1 - role", {"fields": ["role"]}),
        (
            "Page 2 - accessibility",
            {
                "classes": ["collapse"],
                "fields": [
                    "accessibility_options",
                    "accessibility_categories",
                    "accessibility_description",
                ],
            },
        ),
        (
            "Page 3 - use",
            {
                "classes": ["collapse"],
                "fields": [
                    "digital_confidence",
                    "usage_at_work",
                    "usage_outside_work",
                    "how_useful",
                ],
            },
        ),
        (
            "Page 4 - task",
            {
                "classes": ["collapse"],
                "fields": [
                    "task_1_description",
                    "task_1_regularity",
                    "task_1_duration",
                    "task_1_consider_using_ai",
                    "task_2_description",
                    "task_2_regularity",
                    "task_2_duration",
                    "task_2_consider_using_ai",
                    "task_3_description",
                    "task_3_regularity",
                    "task_3_duration",
                    "task_3_consider_using_ai",
                ],
            },
        ),
        (
            "Page 5 - role details",
            {
                "classes": ["collapse"],
                "fields": [
                    "role_regularity_summarise_large_docs",
                    "role_regularity_condense_multiple_docs",
                    "role_regularity_search_across_docs",
                    "role_regularity_compare_multiple_docs",
                    "role_regularity_specific_template",
                    "role_regularity_shorten_docs",
                    "role_regularity_write_docs",
                    "role_duration_summarise_large_docs",
                    "role_duration_condense_multiple_docs",
                    "role_duration_search_across_docs",
                    "role_duration_compare_multiple_docs",
                    "role_duration_specific_template",
                    "role_duration_shorten_docs",
                    "role_duration_write_docs",
                ],
            },
        ),
        (
            "Page 6 - consent",
            {
                "classes": ["collapse"],
                "fields": [
                    "consent_research",
                    "consent_interviews",
                    "consent_feedback",
                    "consent_condfidentiality",
                    "consent_understand",
                    "consent_agreement",
                ],
            },
        ),
    ]

    list_display = [
        "email",
        "business_unit",
        "grade",
        "profession",
        "is_developer",
        "last_login",
    ]
    list_filter = ["business_unit", "grade", "profession"]
    date_hierarchy = "last_login"

    @admin.display(ordering="ai_experience", description="AI Experience")
    def get_ai(self, obj: User):
        return obj.ai_experience

    class Meta:
        model = User
        fields = ["email"]
        import_id_fields = ["email"]


class FileAdmin(ExportMixin, admin.ModelAdmin):
    def reupload(self, _request, queryset):
        for file in queryset:
            logger.info("Re-uploading file to core-api: %s", file)
            async_task(ingest, file.id)
            logger.info("Successfully reuploaded file %s.", file)

    list_display = ["file_name", "user", "status", "created_at", "last_referenced"]
    list_filter = ["user", "status"]
    date_hierarchy = "created_at"
    actions = ["reupload"]
    search_fields = ["user__email"]


class CitationInline(admin.StackedInline):
    model = models.Citation
    ordering = ("modified_at",)

    extra = 0


class ChatMessageActivityEventInline(admin.StackedInline):
    model = models.ActivityEvent
    ordering = ("modified_at",)

    extra = 0


class ChatMessageTokenUseInline(admin.StackedInline):
    model = models.ChatMessageTokenUse
    ordering = ("modified_at",)

    extra = 0


class ChatMessageTokenUseAdmin(ExportMixin, admin.ModelAdmin):
    list_display = ["chat_message", "use_type", "model_name", "token_count"]
    list_filter = ["use_type", "model_name"]


class ChatMessageAdmin(ExportMixin, admin.ModelAdmin):
    list_display = ["short_text", "role", "get_user", "chat", "route", "created_at"]
    list_filter = ["role", "route", "chat__user"]
    date_hierarchy = "created_at"
    inlines = [CitationInline, ChatMessageTokenUseInline, ChatMessageActivityEventInline]
    readonly_fields = ["selected_files", "source_files"]
    search_fields = ["chat__user__email"]

    @admin.display(ordering="chat__user", description="User")
    def get_user(self, obj):
        return obj.chat.user

    @admin.display(description="text")
    def short_text(self, obj):
        max_length = 128
        if len(obj.text) < max_length:
            return obj.text
        return obj.text[: max_length - 3] + "..."


class ChatMessageInline(admin.StackedInline):
    model = models.ChatMessage
    ordering = ("modified_at",)
    fields = ["text", "role", "route", "rating"]
    readonly_fields = ["text", "role", "route", "rating"]
    extra = 1
    show_change_link = True  # allows users to click through to look at Citations


class ChatAdmin(ExportMixin, admin.ModelAdmin):
    def export_as_csv(self, request, queryset: QuerySet):  # noqa:ARG002
        history_field_names: list[str] = [field.name for field in models.Chat._meta.fields]  # noqa:SLF001
        message_field_names: list[str] = [field.name for field in models.ChatMessage._meta.fields]  # noqa:SLF001

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = "attachment; filename=chat.csv"
        writer = csv.writer(response)

        writer.writerow(["history_" + n for n in history_field_names] + ["message_" + n for n in message_field_names])
        chat_message: models.ChatMessage
        for chat in queryset:
            for chat_message in chat.chatmessage_set.all():
                row = [getattr(chat, field) for field in history_field_names] + [
                    getattr(chat_message, field) for field in message_field_names
                ]
                writer.writerow(row)

        return response

    export_as_csv.short_description = "Export Selected"
    fieldsets = [
        (
            None,
            {
                "fields": ["name", "user"],
            },
        ),
        (
            "Feedback",
            {
                "classes": ["collapse"],
                "fields": ["feedback_achieved", "feedback_saved_time", "feedback_improved_work", "feedback_notes"],
            },
        ),
        (
            "AI Settings",
            {
                "classes": ["collapse"],
                "fields": ["chat_backend", "temperature"],
            },
        ),
    ]
    inlines = [ChatMessageInline]
    list_display = ["name", "user", "created_at"]
    list_filter = ["user"]
    date_hierarchy = "created_at"
    actions = ["export_as_csv"]
    search_fields = ["user__email"]


def reporting_dashboard(request):
    return render(request, "report.html", {}, using="django")


admin.site.register(User, UserAdmin)
admin.site.register(models.File, FileAdmin)
admin.site.register(models.Chat, ChatAdmin)
admin.site.register(models.ChatMessage, ChatMessageAdmin)
admin.site.register(models.AISettings)
admin.site.register(models.ChatMessageTokenUse, ChatMessageTokenUseAdmin)
admin.site.register(models.ChatLLMBackend, ChatLLMBackendAdmin)
admin.site.register_view("report/", view=reporting_dashboard, name="Site report")
