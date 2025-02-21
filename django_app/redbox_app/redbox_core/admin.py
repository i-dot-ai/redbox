import logging
import textwrap

from django.contrib import admin
from django.contrib.auth import get_user_model
from import_export.admin import ExportMixin, ImportExportMixin

from . import models

logger = logging.getLogger(__name__)
User = get_user_model()


class DepartmentBusinessUnitAdmin(admin.ModelAdmin):
    pass


class ChatLLMBackendAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "provider",
        "is_default",
        "enabled",
    ]

    class Meta:
        model = models.ChatLLMBackend


class UserAdmin(ImportExportMixin, admin.ModelAdmin):
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


class ChatMessageAdmin(ExportMixin, admin.ModelAdmin):
    list_display = ["short_text", "role", "get_user", "chat", "created_at"]
    list_filter = ["role", "chat__user"]
    date_hierarchy = "created_at"
    search_fields = ["chat__user__email"]

    @admin.display(ordering="chat__user", description="User")
    def get_user(self, obj):
        return obj.chat.user

    @admin.display(description="text")
    def short_text(self, obj):
        return textwrap.shorten(obj.text, 128, placeholder="...")


class FileInline(admin.StackedInline):
    model = models.File
    ordering = ("modified_at",)
    extra = 0


class ChatMessageInline(admin.StackedInline):
    model = models.ChatMessage
    ordering = ("created_at",)
    fields = ["id", "created_at", "text", "role", "rating", "delay"]
    readonly_fields = ["id", "created_at", "text", "role", "rating", "delay"]
    extra = 0


class ChatAdmin(ExportMixin, admin.ModelAdmin):
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
    inlines = [ChatMessageInline, FileInline]
    list_display = ["name", "user", "created_at"]
    list_filter = ["chat_backend__name"]
    date_hierarchy = "created_at"
    search_fields = ["user__email"]


class FileAdmin(ExportMixin, admin.ModelAdmin):
    list_display = ["file_name", "chat__user", "token_count", "status", "created_at"]
    list_filter = ["chat__user", "status"]
    date_hierarchy = "created_at"
    actions = ["reupload"]
    search_fields = ["chat__user__email", "file_name"]


admin.site.register(models.DepartmentBusinessUnit, DepartmentBusinessUnitAdmin)
admin.site.register(User, UserAdmin)
admin.site.register(models.Chat, ChatAdmin)
admin.site.register(models.ChatLLMBackend, ChatLLMBackendAdmin)
admin.site.register(models.File, FileAdmin)
