import logging
import os
import textwrap
import uuid
from collections.abc import Collection, Sequence
from datetime import UTC, date, datetime, timedelta
from typing import override

import jwt
from django.conf import settings
from django.contrib.auth.base_user import BaseUserManager as BaseSSOUserManager
from django.contrib.postgres.fields import ArrayField
from django.core import validators
from django.db import models
from django.db.models import Max, Min, Prefetch, UniqueConstraint
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

# from django_use_email_as_username.models import BaseUser, BaseUserManager
from django.contrib.auth.models import AbstractBaseUser, Group, PermissionsMixin
from yarl import URL

from redbox.models.settings import get_settings
from redbox_app.redbox_core.utils import get_date_group

logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

env = get_settings()

es_client = env.elasticsearch_client()


class UUIDPrimaryKeyBase(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(editable=False, auto_now_add=True)
    modified_at = models.DateTimeField(editable=False, auto_now=True)

    class Meta:
        abstract = True
        ordering = ["created_at"]


def sanitise_string(string: str | None) -> str | None:
    """We are seeing NUL (0x00) characters in user entered fields, and also in document citations.
    We can't save these characters, so we need to sanitise them."""
    return string.replace("\x00", "\ufffd") if string else string


class ChatLLMBackend(models.Model):
    """https://python.langchain.com/docs/how_to/chat_models_universal_init/"""

    class Providers(models.TextChoices):
        OPENAI = "openai"
        ANTHROPIC = "anthropic"
        AZURE_OPENAI = "azure_openai"
        GOOGLE_VERTEXAI = "google_vertexai"
        GOOGLE_GENAI = "google_genai"
        BEDROCK = "bedrock"
        BEDROCK_CONVERSE = "bedrock_converse"
        COHERE = "cohere"
        FIREWORKS = "fireworks"
        TOGETHER = "together"
        MISTRALAI = "mistralai"
        HUGGINGFACE = "huggingface"
        GROQ = "groq"
        OLLAMA = "ollama"

    name = models.CharField(
        max_length=128,
        help_text="The name of the model, e.g. “gpt-4o”, “claude-3-opus-20240229”.",
    )
    provider = models.CharField(max_length=128, choices=Providers, help_text="The model provider")
    description = models.TextField(null=True, blank=True, help_text="brief description of the model")
    is_default = models.BooleanField(default=False, help_text="is this the default llm to use.")
    enabled = models.BooleanField(default=True, help_text="is this model enabled.")
    display = models.CharField(max_length=128, null=True, blank=True, help_text="name to display in UI.")

    class Meta:
        constraints = [UniqueConstraint(fields=["name", "provider"], name="unique_name_provider")]

    def __str__(self):
        return self.display or self.name

    def save(self, *args, **kwargs):
        if self.is_default:
            ChatLLMBackend.objects.filter(is_default=True).update(is_default=False)
        super().save(*args, **kwargs)


class AbstractAISettings(models.Model):
    chat_backend = models.ForeignKey(ChatLLMBackend, on_delete=models.CASCADE, help_text="LLM to use in chat")
    temperature = models.FloatField(default=0, help_text="temperature for LLM")

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if not self.chat_backend_id:
            self.chat_backend = ChatLLMBackend.objects.get(is_default=True)
        return super().save(*args, **kwargs)


class AISettings(UUIDPrimaryKeyBase, TimeStampedModel, AbstractAISettings):
    label = models.CharField(max_length=50, unique=True)

    # LLM settings
    context_window_size = models.PositiveIntegerField(null=True, blank=True)
    llm_max_tokens = models.PositiveIntegerField(null=True, blank=True)

    # Prompts and LangGraph settings
    max_document_tokens = models.PositiveIntegerField(null=True, blank=True)
    self_route_enabled = models.BooleanField(null=True, blank=True)
    map_max_concurrency = models.PositiveIntegerField(null=True, blank=True)
    stuff_chunk_context_ratio = models.FloatField(null=True, blank=True)
    recursion_limit = models.PositiveIntegerField(null=True, blank=True)

    chat_system_prompt = models.TextField(null=True, blank=True)
    chat_question_prompt = models.TextField(null=True, blank=True)
    chat_with_docs_system_prompt = models.TextField(null=True, blank=True)
    chat_with_docs_question_prompt = models.TextField(null=True, blank=True)
    chat_with_docs_reduce_system_prompt = models.TextField(null=True, blank=True)
    retrieval_system_prompt = models.TextField(null=True, blank=True)
    retrieval_question_prompt = models.TextField(null=True, blank=True)
    agentic_retrieval_system_prompt = models.TextField(null=True, blank=True)
    agentic_retrieval_question_prompt = models.TextField(null=True, blank=True)
    agentic_give_up_system_prompt = models.TextField(null=True, blank=True)
    agentic_give_up_question_prompt = models.TextField(null=True, blank=True)
    condense_system_prompt = models.TextField(null=True, blank=True)
    condense_question_prompt = models.TextField(null=True, blank=True)
    chat_map_system_prompt = models.TextField(null=True, blank=True)
    chat_map_question_prompt = models.TextField(null=True, blank=True)
    reduce_system_prompt = models.TextField(null=True, blank=True)

    # Elsticsearch RAG and boost values
    rag_k = models.PositiveIntegerField(null=True, blank=True)
    rag_num_candidates = models.PositiveIntegerField(null=True, blank=True)
    rag_gauss_scale_size = models.PositiveIntegerField(null=True, blank=True)
    rag_gauss_scale_decay = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[validators.MinValueValidator(0.0)],
    )
    rag_gauss_scale_min = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[validators.MinValueValidator(1.0)],
    )
    rag_gauss_scale_max = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[validators.MinValueValidator(1.0)],
    )
    rag_desired_chunk_size = models.PositiveIntegerField(null=True, blank=True)
    elbow_filter_enabled = models.BooleanField(null=True, blank=True)
    match_boost = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    match_name_boost = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    match_description_boost = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    match_keywords_boost = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    knn_boost = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    similarity_threshold = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[
            validators.MinValueValidator(0.0),
            validators.MaxValueValidator(1.0),
        ],
    )

    def __str__(self) -> str:
        return str(self.label)


class SSOUserManager(BaseSSOUserManager):
    use_in_migrations = True

    def _create_user(self, username, password, **extra_fields):
        """Create and save a User with the given email and password."""
        if not username:
            raise ValueError("The given email must be set")
        # email = self.normalize_email(email)
        User = self.model(email=username, **extra_fields)
        User.set_password(password)
        User.save(using=self._db)
        return User

    def create_user(self, username, password=None, **extra_fields):
        """Create and save a regular User with the given email and password."""
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(username, password, **extra_fields)

    def create_superuser(self, username, password=None, **extra_fields):
        """Create and save a SuperUser with the given email and password."""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self._create_user(username, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin, UUIDPrimaryKeyBase):
    class UserGrade(models.TextChoices):
        AA = "AA", _("AA")
        AO = "AO", _("AO")
        DEPUTY_DIRECTOR = "DD", _("Deputy Director")
        DIRECTOR = "D", _("Director")
        DIRECTOR_GENERAL = "DG", _("Director General")
        EO = "EO", _("EO")
        G6 = "G6", _("G6")
        G7 = "G7", _("G7")
        HEO = "HEO", _("HEO")
        PS = "PS", _("Permanent Secretary")
        SEO = "SEO", _("SEO")
        OT = "OT", _("Other")

    class Profession(models.TextChoices):
        AN = "AN", _("Analysis")
        CM = "CMC", _("Commercial")
        COM = "COM", _("Communications")
        CON = "CON", _("Consular")
        CF = "CF", _("Counter Fraud")
        DM = "DM", _("Debt Management")
        DDT = "DDT", _("Digital, Data and Technology")
        FIN = "FIN", _("Finance")
        GM = "GM", _("Grants Management")
        HR = "HR", _("Human Resources")
        IA = "IA", _("Intelligence Analysis")
        IAU = "IAU", _("Internal Audit")
        IT = "IT", _("International Trade")
        KIM = "KIM", _("Knowledge and Information Management")
        LG = "LG", _("Legal")
        OD = "OD", _("Operational Delivery")
        POL = "POL", _("Policy")
        PD = "PD", _("Project Delivery")
        PROP = "PROP", _("Property")
        SC = "SC", _("Security")
        SE = "SE", _("Science and Engineering")
        OT = "OT", _("Other")

    class BusinessUnit(models.TextChoices):
        COMPETITION_MARKETS_AND_REGULATORY_REFORM = "Competition, Markets and Regulatory Reform (CMRR)", _("Competition, Markets and Regulatory Reform (CMRR)")
        CORPORATE_SERVICES_GROUP = "Corporate Services Group (CSG)", _("Corporate Services Group (CSG)")
        TRADE_POLICY_IMPLEMENTATION_AND_NEGOTIATIONS = "Trade Policy Implementation and Negotiations (TPIN)", _("Trade Policy Implementation and Negotiations (TPIN)")
        ECONOMIC_SECURITY_AND_TRADE_RELATIONS = "Economic Security and Trade Relations (ESTR)", _("Economic Security and Trade Relations (ESTR)")
        STRATEGY_AND_INVESTMENT = "Strategy and Investment", _("Strategy and Investment")
        DOMESTIC_AND_INTERNATIONAL_MARKETS_AND_EXPORTS_GROUP = "Domestic and International Markets and Exports Group (DIME) UK Teams", _("Domestic and International Markets and Exports Group (DIME) UK Teams")
        BUSINESS_GROUP = "Business Group", _("Business Group")
        OVERSEAS_REGIONS = "Overseas Regions", _("Overseas Regions")
        INDUSTRIAL_STRATEGY_UNIT = "Industrial Strategy Unit", _("Industrial Strategy Unit")
        DIGITAL_DATA_AND_TECHNOLOGY = "Digital, Data and Technology (DDaT)", _("Digital, Data and Technology (DDaT)")

    class AIExperienceLevel(models.TextChoices):
        CURIOUS_NEWCOMER = "Curious Newcomer", _("I haven't used Generative AI tools")
        CAUTIOUS_EXPLORER = "Cautious Explorer", _("I have a little experience using Generative AI tools")
        ENTHUSIASTIC_EXPERIMENTER = (
            "Enthusiastic Experimenter",
            _("I occasionally use Generative AI tools but am still experimenting with their capabilities"),
        )
        EXPERIENCED_NAVIGATOR = (
            "Experienced Navigator",
            _("I use Generative AI tools regularly and have a good understanding of their strengths and limitations"),
        )
        AI_ALCHEMIST = (
            "AI Alchemist",
            _(
                "I have extensive experience with Generative AI tools and can leverage them effectively in various "
                "contexts"
            ),
        )

    class AccessibilityOptions(models.TextChoices):
        YES = "Yes", _("Yes")
        NO = "No", _("No")
        PREFER_NOT_TO_SAY = "Prefer not to say", _("Prefer not to say")

    class AccessibilityCategories(models.TextChoices):
        SIGHT = "Sight", _("I'm blind, partially sighted or colour blind")
        HEARING = "Hearing", _("I'm deaf or hard of hearing")
        MOBILITY = "Mobility", _("I have difficulty using a mouse or keyboard")
        THINKING_AND_UNDERSTANDING = (
            "Thinking and understanding",
            _("I have autism, dyslexia, ADHD, a mental health condition"),
        )
        TEMPORARY = "Temporary", _("I have an injury")
        INVISIBLE_CONDITION = "Invisible condition", _("This could be menopause, a mental health condition")

    class DigitalConfidence(models.TextChoices):
        CONFIDENT = (
            "I feel confident using new technologies and digital products",
            _("I feel confident using new technologies and digital products"),
        )
        NEED_HELP = (
            "When using new technologies and digital products I tend to need some help",
            _("When using new technologies and digital products I tend to need some help"),
        )
        DONT_WANT = (
            "I don't use new technologies and I don't want to learn how to use them",
            _("I don't use new technologies and I don't want to learn how to use them"),
        )

    class RegularityAI(models.TextChoices):
        NOT_USED = "I have not used GenAI", _("I have not used GenAI")
        EVERYDAY = "Everyday", _("Everyday")
        WEEKLY = "Weekly - a few times per week", _("Weekly - a few times per week")
        MONTHLY = "Monthly - a few times per month", _("Monthly - a few times per month")
        NOT_MUCH = "Not much at all - tried once or twice", _("Not much at all - tried once or twice")

    class Usefulness(models.TextChoices):
        NOT_USED = "I have not used GenAI", _("I have not used GenAI")
        NOT_ENOUGH = (
            "I have not used GenAI enough to say if it's useful or not",
            _("I have not used GenAI enough to say if it's useful or not"),
        )
        NOT_FIGURED_OUT = (
            "I have not figured out how to best use GenAI",
            _("I have not figured out how to best use GenAI"),
        )
        FEW_THINGS = (
            "I have found a few things GenAI really helps me with",
            _("I have found a few things GenAI really helps me with"),
        )
        MANY_THINGS = (
            "GenAI has proved useful for many different tasks",
            _("GenAI has proved useful for many different tasks"),
        )

    class ConsiderUsingAI(models.TextChoices):
        NO = "No", _("No")
        MAYBE = "Maybe (or unsure)", _("Maybe (or unsure)")
        YES = "Yes", _("Yes")
        ALREADY_DO = "Yes! I already use GenAI for this", _("Yes! I already use GenAI for this")

    class RegularityTasks(models.TextChoices):
        DONT_DO = "I do not do this task", _("I do not do this task")
        EVERYDAY = "Everyday", _("Everyday")
        WEEKLY = "Weekly", _("Weekly")
        MONTHLY = "Monthly", _("Monthly")
        QUARTERLY = "Quarterly", _("Quarterly")
        YEARLY = "Yearly", _("Yearly")

    class DurationTasks(models.TextChoices):
        DONT_DO = "I do not do this task", _("I do not do this task")
        UP_TO_15_MINS = "1 to 15 minutes", _("1 to 15 minutes")
        UP_TO_60_MINS = "15 to 60 minutes", _("15 to 60 minutes")
        UP_TO_4_HOURS = "1 to 4 hours", _("1 to 4 hours")
        UP_TO_8_HOURS = "4 to 8 hours", _("4 to 8 hours")
        UP_TO_2_DAYS = "1 to 2 days", _("1 to 2 days")
        MORE_THAN_2_DAYS = "More than 2 days", _("More than 2 days")
        MORE_THAN_1_WEEK = "More than a week", _("More than a week")

    username = models.EmailField(unique=True, default="default@default.com")
    email = models.EmailField(unique=True)
    password = models.CharField("password", max_length=128, blank=True, null=True)
    first_name = models.CharField(max_length=48)
    last_name = models.CharField(max_length=48)
    business_unit = models.CharField(null=True, blank=True, max_length=100, choices=BusinessUnit)
    grade = models.CharField(null=True, blank=True, max_length=3, choices=UserGrade)
    name = models.CharField(null=True, blank=True)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_superuser = models.BooleanField(default=False)
    ai_experience = models.CharField(null=True, blank=True, max_length=25, choices=AIExperienceLevel)
    profession = models.CharField(null=True, blank=True, max_length=4, choices=Profession)
    info_about_user = models.CharField(null=True, blank=True, help_text="user entered info from profile overlay")
    redbox_response_preferences = models.CharField(
        null=True,
        blank=True,
        help_text="user entered info from profile overlay, to be used in custom prompt",
    )
    ai_settings = models.ForeignKey(AISettings, on_delete=models.SET_DEFAULT, default="default", to_field="label")
    is_developer = models.BooleanField(null=True, blank=True, default=False, help_text="is this user a developer?")

    # Additional fields for sign-up form
    # Page 1
    role = models.TextField(null=True, blank=True)
    # Page 2
    accessibility_options = models.CharField(null=True, blank=True, max_length=64, choices=AccessibilityOptions)
    accessibility_categories = models.CharField(null=True, blank=True, max_length=64, choices=AccessibilityCategories)
    accessibility_description = models.TextField(null=True, blank=True)
    # Page 3
    digital_confidence = models.CharField(null=True, blank=True, max_length=128, choices=DigitalConfidence)
    usage_at_work = models.CharField(null=True, blank=True, max_length=64, choices=RegularityAI)
    usage_outside_work = models.CharField(null=True, blank=True, max_length=64, choices=RegularityAI)
    how_useful = models.CharField(null=True, blank=True, max_length=64, choices=Usefulness)
    redbox_tasks = models.TextField(null=True, blank=True)
    # Page 4
    task_1_description = models.TextField(null=True, blank=True)
    task_1_regularity = models.TextField(null=True, blank=True)
    task_1_duration = models.TextField(null=True, blank=True)
    task_1_consider_using_ai = models.CharField(null=True, blank=True, max_length=64, choices=ConsiderUsingAI)
    task_2_description = models.TextField(null=True, blank=True)
    task_2_regularity = models.TextField(null=True, blank=True)
    task_2_duration = models.TextField(null=True, blank=True)
    task_2_consider_using_ai = models.CharField(null=True, blank=True, max_length=64, choices=ConsiderUsingAI)
    task_3_description = models.TextField(null=True, blank=True)
    task_3_regularity = models.TextField(null=True, blank=True)
    task_3_duration = models.TextField(null=True, blank=True)
    task_3_consider_using_ai = models.CharField(null=True, blank=True, max_length=64, choices=ConsiderUsingAI)
    # Page 5
    role_regularity_summarise_large_docs = models.CharField(
        null=True, blank=True, max_length=32, choices=RegularityTasks
    )
    role_regularity_condense_multiple_docs = models.CharField(
        null=True, blank=True, max_length=32, choices=RegularityTasks
    )
    role_regularity_search_across_docs = models.CharField(null=True, blank=True, max_length=32, choices=RegularityTasks)
    role_regularity_compare_multiple_docs = models.CharField(
        null=True, blank=True, max_length=32, choices=RegularityTasks
    )
    role_regularity_specific_template = models.CharField(null=True, blank=True, max_length=32, choices=RegularityTasks)
    role_regularity_shorten_docs = models.CharField(null=True, blank=True, max_length=32, choices=RegularityTasks)
    role_regularity_write_docs = models.CharField(null=True, blank=True, max_length=32, choices=RegularityTasks)
    role_duration_summarise_large_docs = models.CharField(null=True, blank=True, max_length=32, choices=DurationTasks)
    role_duration_condense_multiple_docs = models.CharField(null=True, blank=True, max_length=32, choices=DurationTasks)
    role_duration_search_across_docs = models.CharField(null=True, blank=True, max_length=32, choices=DurationTasks)
    role_duration_compare_multiple_docs = models.CharField(null=True, blank=True, max_length=32, choices=DurationTasks)
    role_duration_specific_template = models.CharField(null=True, blank=True, max_length=32, choices=DurationTasks)
    role_duration_shorten_docs = models.CharField(null=True, blank=True, max_length=32, choices=DurationTasks)
    role_duration_write_docs = models.CharField(null=True, blank=True, max_length=32, choices=DurationTasks)
    # Page 6
    consent_research = models.BooleanField(null=True, blank=True, default=False)
    consent_interviews = models.BooleanField(null=True, blank=True, default=False)
    consent_feedback = models.BooleanField(null=True, blank=True, default=False)
    consent_condfidentiality = models.BooleanField(null=True, blank=True, default=False)
    consent_understand = models.BooleanField(null=True, blank=True, default=False)
    consent_agreement = models.BooleanField(null=True, blank=True, default=False)

    user_permissions = models.ManyToManyField(
        "auth.Permission",
        verbose_name="user permissions",
        blank=True,
        related_name="sso_user_set",
    )
    groups = models.ManyToManyField(Group, verbose_name="groups", blank=True, related_name="sso_user_set")

    USERNAME_FIELD = "username"

    REQUIRED_FIELDS = []

    objects = SSOUserManager()

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.email}"

    def save(self, *args, **kwargs):
        self.email = self.email.lower()
        super().save(*args, **kwargs)

    def get_bearer_token(self) -> str:
        """the bearer token expected by the core-api"""
        user_uuid = str(self.id)
        bearer_token = jwt.encode({"user_uuid": user_uuid}, key=settings.SECRET_KEY)
        return f"Bearer {bearer_token}"

    def get_initials(self) -> str:
        try:
            if self.name:
                if " " in self.name:
                    first_name, last_name = self.name.split(" ")
                else:
                    first_name = self.name
                    last_name = " "
            else:
                name_part = self.email.split("@")[0]
                first_name, last_name = name_part.split(".")
            return first_name[0].upper() + last_name[0].upper()
        except (IndexError, AttributeError, ValueError):
            return ""


class InactiveFileError(ValueError):
    def __init__(self, file):
        super().__init__(f"{file.pk} is inactive, status is {file.status}")


def build_s3_key(instance, filename: str) -> str:
    """the s3-key is the primary key for a file,
    this needs to be unique so that if a user uploads a file with the same name as
    1. an existing file that they own, then it is overwritten
    2. an existing file that another user owns then a new file is created
    """
    return f"{instance.user.email}/{filename}"


class File(UUIDPrimaryKeyBase, TimeStampedModel):
    class Status(models.TextChoices):
        complete = "complete"
        deleted = "deleted"
        errored = "errored"
        processing = "processing"

    INACTIVE_STATUSES = [Status.deleted, Status.errored]

    status = models.CharField(choices=Status.choices, null=False, blank=False)
    original_file = models.FileField(
        storage=settings.STORAGES["default"]["BACKEND"],
        upload_to=build_s3_key,
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    original_file_name = models.TextField(max_length=2048, blank=True, null=True)  # delete me
    last_referenced = models.DateTimeField(blank=True, null=True)
    ingest_error = models.TextField(
        max_length=2048,
        blank=True,
        null=True,
        help_text="error, if any, encountered during ingest",
    )

    def __str__(self) -> str:  # pragma: no cover
        return self.file_name

    def save(self, *args, **kwargs):
        if not self.last_referenced:
            if self.created_at:
                #  Needed to populate the initial last_referenced field for existing Files
                self.last_referenced = self.created_at
            else:
                self.last_referenced = timezone.now()
        super().save(*args, **kwargs)

    @override
    def delete(self, using=None, keep_parents=False):
        #  Needed to make sure no orphaned files remain in the storage
        self.delete_from_s3()
        super().delete()

    def delete_from_s3(self):
        """Manually deletes the file from S3 storage."""
        self.original_file.delete(save=False)

    def delete_from_elastic(self):
        index = env.elastic_chunk_alias
        if es_client.indices.exists(index=index):
            es_client.delete_by_query(
                index=index,
                body={"query": {"term": {"metadata.file_name.keyword": self.unique_name}}},
            )

    @property
    def file_type(self) -> str:
        name = self.file_name
        return name.split(".")[-1]

    @property
    def url(self) -> str:
        return self.original_file.url

    @property
    def file_name(self) -> str:
        if self.original_file_name:  # delete me?
            return self.original_file_name

        # could have a stronger (regex?) way of stripping the users email address?
        if "/" in self.original_file.name:
            return self.original_file.name.split("/")[1]

        logger.error("expected filename=%s to start with the user's email address", self.original_file.name)
        return self.original_file.name

    @property
    def unique_name(self) -> str:
        """primary key for accessing file in s3"""
        if self.status in File.INACTIVE_STATUSES:
            logger.exception("Attempt to access s3-key for inactive file %s with status %s", self.pk, self.status)
            raise InactiveFileError(self)
        return self.original_file.name

    def get_status_text(self) -> str:
        permanent_error = "Error"
        temporary_error = "Error, please try again"
        if self.ingest_error:
            temporary_error_substrings = [
                "ConnectionError",
                "RateLimitError",
                "ConnectTimeout",
                "openai.InternalServerError",
            ]
            for substring in temporary_error_substrings:
                if substring in self.ingest_error:
                    return temporary_error
            return permanent_error
        return dict(File.Status.choices).get(self.status, permanent_error)

    @property
    def expires_at(self) -> datetime:
        return self.last_referenced + timedelta(seconds=settings.FILE_EXPIRY_IN_SECONDS)

    @property
    def expires(self) -> timedelta:
        return self.expires_at - datetime.now(tz=UTC)

    def __lt__(self, other):
        return self.id < other.id

    @classmethod
    def get_completed_and_processing_files(cls, user: User) -> tuple[Sequence["File"], Sequence["File"]]:
        """Returns all files that are completed and processing for a given user."""

        completed_files = cls.objects.filter(user=user, status=File.Status.complete).order_by("-created_at")
        processing_files = cls.objects.filter(user=user, status=File.Status.processing).order_by("-created_at")
        return completed_files, processing_files

    @classmethod
    def get_ordered_by_citation_priority(cls, chat_message_id: uuid.UUID) -> Sequence["File"]:
        """Returns all files that are cited in a given chat message, ordered by citation priority."""
        return (
            cls.objects.filter(citation__chat_message_id=chat_message_id)
            .annotate(min_created_at=Min("citation__created_at"))
            .order_by("min_created_at")
            .prefetch_related(
                Prefetch(
                    "citation_set",
                    queryset=Citation.objects.filter(chat_message_id=chat_message_id),
                )
            )
        )


class Chat(UUIDPrimaryKeyBase, TimeStampedModel, AbstractAISettings):
    name = models.TextField(max_length=1024, null=False, blank=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    archived = models.BooleanField(default=False, null=True, blank=True)

    # Exit feedback - this is separate to the ratings for individual ChatMessages
    feedback_achieved = models.BooleanField(
        null=True,
        blank=True,
        help_text="Did Redbox do what you needed it to in this chat?",
    )
    feedback_saved_time = models.BooleanField(null=True, blank=True, help_text="Did Redbox help save you time?")
    feedback_improved_work = models.BooleanField(
        null=True, blank=True, help_text="Did Redbox help to improve your work?"
    )
    feedback_notes = models.TextField(null=True, blank=True, help_text="Do you want to tell us anything further?")

    def __str__(self) -> str:  # pragma: no cover
        return self.name or ""

    @override
    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        self.name = sanitise_string(self.name)

        if self.chat_backend_id is None:
            self.chat_backend = self.user.ai_settings.chat_backend

        if self.temperature is None:
            self.temperature = self.user.ai_settings.temperature

        super().save(force_insert, force_update, using, update_fields)

    @classmethod
    def get_ordered_by_last_message_date(
        cls, user: User, exclude_chat_ids: Collection[uuid.UUID] | None = None
    ) -> Sequence["Chat"]:
        """Returns all chat histories for a given user, ordered by the date of the latest message."""
        exclude_chat_ids = exclude_chat_ids or []
        return (
            cls.objects.filter(user=user, archived=False)
            .exclude(id__in=exclude_chat_ids)
            .annotate(latest_message_date=Max("chatmessage__created_at"))
            .order_by("-latest_message_date")
        )

    @property
    def newest_message_date(self) -> date:
        return self.chatmessage_set.aggregate(newest_date=Max("created_at"))["newest_date"].date()

    @property
    def date_group(self):
        return get_date_group(self.newest_message_date)


class Citation(UUIDPrimaryKeyBase, TimeStampedModel):
    class Origin(models.TextChoices):
        WIKIPEDIA = "Wikipedia", _("wikipedia")
        USER_UPLOADED_DOCUMENT = "UserUploadedDocument", _("user uploaded document")
        GOV_UK = "GOV.UK", _("gov.uk")

        @classmethod
        def try_parse(cls, value):
            try:
                return cls(value)
            except ValueError:
                logger.warning("failed to parse %s to Origin", value)
                return None

    file = models.ForeignKey(
        File,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="file for internal citation",
    )
    url = models.URLField(null=True, blank=True, help_text="url for external")
    chat_message = models.ForeignKey("ChatMessage", on_delete=models.CASCADE)
    text = models.TextField(null=True, blank=True)
    page_numbers = ArrayField(
        models.PositiveIntegerField(),
        null=True,
        blank=True,
        help_text="location of citation in document",
    )
    source = models.CharField(
        max_length=32,
        choices=Origin,
        help_text="source of citation",
        default=Origin.USER_UPLOADED_DOCUMENT,
        null=True,
        blank=True,
    )
    text_in_answer = models.TextField(
        null=True,
        blank=True,
        help_text="the part of the answer the citation refers too - useful for adding in footnotes",
    )

    def __str__(self):
        text = self.text or "..."
        return textwrap.shorten(text, width=128, placeholder="...")

    def save(self, *args, force_insert=False, force_update=False, using=None, update_fields=None):
        if self.source == self.Origin.USER_UPLOADED_DOCUMENT:
            if self.file is None:
                msg = "file must be specified for a user-uploaded-document"
                raise ValueError(msg)

            if self.url is not None:
                msg = "url should not be specified for a user-uploaded-document"
                raise ValueError(msg)

        if self.source != self.Origin.USER_UPLOADED_DOCUMENT:
            if self.url is None:
                msg = "url must be specified for an external citation"
                raise ValueError(msg)

            if self.file is not None:
                msg = "file should not be specified for an external citation"
                raise ValueError(msg)

        self.text = sanitise_string(self.text)

        super().save(*args, force_insert, force_update, using, update_fields)

    @property
    def uri(self) -> URL:
        """returns the url of either the external citation or the user-uploaded document"""
        return URL(self.url or self.file.url)


class ChatMessage(UUIDPrimaryKeyBase, TimeStampedModel):
    class Role(models.TextChoices):
        ai = "ai"
        user = "user"
        system = "system"

    chat = models.ForeignKey(Chat, on_delete=models.CASCADE)
    text = models.TextField(max_length=32768, null=False, blank=False)
    role = models.CharField(choices=Role.choices, null=False, blank=False)
    route = models.CharField(max_length=25, null=True, blank=True)
    selected_files = models.ManyToManyField(File, related_name="+", symmetrical=False, blank=True)
    source_files = models.ManyToManyField(File, through=Citation)

    rating = models.PositiveIntegerField(
        blank=True,
        null=True,
        validators=[validators.MinValueValidator(1), validators.MaxValueValidator(5)],
    )
    rating_text = models.TextField(blank=True, null=True)
    rating_chips = ArrayField(models.CharField(max_length=32), null=True, blank=True)

    def __str__(self) -> str:  # pragma: no cover
        return textwrap.shorten(self.text, width=20, placeholder="...")

    def save(self, *args, force_insert=False, force_update=False, using=None, update_fields=None):
        self.text = sanitise_string(self.text)
        self.rating_text = sanitise_string(self.rating_text)

        super().save(*args, force_insert, force_update, using, update_fields)

    @classmethod
    def get_messages_ordered_by_citation_priority(cls, chat_id: uuid.UUID) -> Sequence["ChatMessage"]:
        """Returns all chat messages for a given chat history, ordered by citation priority."""
        return (
            cls.objects.filter(chat_id=chat_id)
            .order_by("created_at")
            .prefetch_related(
                Prefetch(
                    "source_files",
                    queryset=File.objects.all()
                    .annotate(min_created_at=Min("citation__created_at"))
                    .order_by("min_created_at"),
                )
            )
        )

    def log(self):
        token_sum = sum(token_use.token_count for token_use in self.chatmessagetokenuse_set.all())
        elastic_log_msg = {
            "@timestamp": self.created_at.isoformat(),
            "id": str(self.id),
            "chat_id": str(self.chat.id),
            "user_id": str(self.chat.user.id),
            "text": str(self.text),
            "route": str(self.route),
            "role": str(self.role),
            "token_count": token_sum,
            "rating": int(self.rating) if self.rating else None,
            "rating_text": str(self.rating_text),
            "rating_chips": list(map(str, self.rating_chips)) if self.rating_chips else None,
        }
        es_client.create(
            index=env.elastic_chat_mesage_index,
            id=uuid.uuid4(),
            body=elastic_log_msg,
        )

    def unique_citation_uris(self) -> list[tuple[str, str]]:
        """a unique set of names and hrefs for all citations"""

        def get_display(citation):
            if not citation.file:
                return str(citation.uri)
            return citation.file.file_name

        return sorted(
            {(get_display(citation), citation.uri, citation.text_in_answer) for citation in self.citation_set.all()}
        )


class ChatMessageTokenUse(UUIDPrimaryKeyBase, TimeStampedModel):
    class UseType(models.TextChoices):
        INPUT = "input", _("input")
        OUTPUT = "output", _("output")

    chat_message = models.ForeignKey(ChatMessage, on_delete=models.CASCADE)
    use_type = models.CharField(
        max_length=10,
        choices=UseType,
        help_text="input or output tokens",
        default=UseType.INPUT,
    )
    model_name = models.CharField(max_length=50, null=True, blank=True)
    token_count = models.PositiveIntegerField(null=True, blank=True)

    def __str__(self) -> str:
        return f"{self.model_name} {self.use_type}"


class ActivityEvent(UUIDPrimaryKeyBase, TimeStampedModel):
    chat_message = models.ForeignKey(ChatMessage, on_delete=models.CASCADE)
    message = models.TextField()

    def __str__(self) -> str:
        return self.message
