import logging
import os
import uuid
from collections.abc import Collection, Sequence
from datetime import UTC, date, datetime, timedelta
from typing import override

import boto3
import jwt
from botocore.config import Config
from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.core import validators
from django.db import models
from django.db.models import Max, Min, Prefetch
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django_use_email_as_username.models import BaseUser, BaseUserManager
from redbox_app.redbox_core.utils import get_date_group
from yarl import URL

from redbox.models import Settings, prompts

logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

env = Settings()

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


class ModelName(models.TextChoices):
    GPT_35_TURBO = "gpt-35-turbo-16k", _("gpt-35-turbo-16k")
    GPT_4_TURBO = "gpt-4-turbo-2024-04-09", _("gpt-4-turbo-2024-04-09")
    GPT_4_OMNI = "gpt-4o", _("gpt-4o")
    GPT_4_OMNI_MINI = "gpt-4o-mini", _("gpt-4o-mini")
    CLAUDE_3_SONNET = "anthropic.claude-3-sonnet-20240229-v1:0", _(
        "claude-3-sonnet"
    )
    CLAUDE_3_HAIKU = "anthropic.claude-3-haiku-20240307-v1:0", _("claude-3-haiku")
    LLAMA_31 = "llama3.1", _("llama3.1")
    MIXTRAL = "mixtral", _("mixtral")
    ADA_002 = "text-embedding-ada-002", _("text-embedding-ada-002")

class AbstractAISettings(models.Model):
    chat_backend = models.CharField(
        max_length=64,
        choices=ModelName,
        help_text="LLM to use in chat",
        default=ModelName.GPT_4_OMNI_MINI,
    )
    temperature = models.FloatField(default=0, help_text="temperature for LLM")

    class Meta:
        abstract = True


class RegisteredModels(UUIDPrimaryKeyBase, TimeStampedModel):
    ai_settings = models.ForeignKey(
        "AISettings",
        on_delete=models.SET_DEFAULT,
        default="default",
        related_name="registered_models",
    )

    model = models.ForeignKey(
        "MLModel",
        on_delete=models.SET_DEFAULT,
        default="default",
        related_name="registered_aisettings",
    )

    default = models.BooleanField(
        default=False,
    )

    def save(self, *args, **kwargs):
        if self.default:
            RegisteredModels.objects.filter(
                ai_settings=self.ai_settings, default=True
            ).update(default=False)
        super().save(*args, **kwargs)


class MLModel(UUIDPrimaryKeyBase, TimeStampedModel):

    class Provider(models.TextChoices):
        AZURE = "azure", _("azure")
        BEDROCK = "bedrock", _("bedrock")
        OLLAMA = "ollama", _("ollama")
        OPEN_AI = "openai", _("open-ai")
        LOCAL_AI = "local-ai", _("local-ai")

    class Availability(
        models.TextChoices
    ):
        GENERAL = "general", _("general")
        PRIVATE = "private", _("private")
        DISABLED = "disabled", _("disabled")

    class ModelType(models.TextChoices):
        EMBEDDING = "embedding", _("embedding")
        CHAT = "chat", _("chat")

    name = models.CharField(
        max_length=64,
        choices=ModelName,
        help_text="LLM to use in chat",
        default=ModelName.GPT_4_OMNI_MINI,
    )

    provider = models.CharField(
        max_length=64,
        choices=Provider,
        help_text="Backend to use in chat",
        default=Provider.OPEN_AI,
    )

    availability = models.CharField(
        max_length=64,
        choices=Availability,
        help_text="Availability of Model",
        default=Availability.GENERAL,
    )

    model_type = models.CharField(
        max_length=64,
        choices=ModelType,
        help_text="The model type",
        default=ModelType.CHAT,
    )

    def __str__(self) -> str:
        return str(self.name) + str(self.provider)

class AISettings(UUIDPrimaryKeyBase, TimeStampedModel, AbstractAISettings):
    label = models.CharField(max_length=50, unique=True)
    max_document_tokens = models.PositiveIntegerField(
        default=1_000_000, null=True, blank=True
    )
    context_window_size = models.PositiveIntegerField(default=128_000)
    llm_max_tokens = models.PositiveIntegerField(default=1024)
    rag_k = models.PositiveIntegerField(default=30)
    rag_num_candidates = models.PositiveIntegerField(default=10)
    rag_gauss_scale_size = models.PositiveIntegerField(default=3)
    rag_gauss_scale_decay = models.FloatField(default=0.5)
    rag_gauss_scale_min = models.FloatField(default=1.1)
    rag_gauss_scale_max = models.FloatField(default=2.0)
    rag_desired_chunk_size = models.PositiveIntegerField(default=300)
    elbow_filter_enabled = models.BooleanField(default=False)
    chat_system_prompt = models.TextField(default=prompts.CHAT_SYSTEM_PROMPT)
    chat_question_prompt = models.TextField(default=prompts.CHAT_QUESTION_PROMPT)
    stuff_chunk_context_ratio = models.FloatField(default=0.75)
    chat_with_docs_system_prompt = models.TextField(
        default=prompts.CHAT_WITH_DOCS_SYSTEM_PROMPT
    )
    chat_with_docs_question_prompt = models.TextField(
        default=prompts.CHAT_WITH_DOCS_QUESTION_PROMPT
    )
    chat_with_docs_reduce_system_prompt = models.TextField(
        default=prompts.CHAT_WITH_DOCS_REDUCE_SYSTEM_PROMPT
    )
    retrieval_system_prompt = models.TextField(default=prompts.RETRIEVAL_SYSTEM_PROMPT)
    retrieval_question_prompt = models.TextField(default=prompts.RETRIEVAL_QUESTION_PROMPT)
    agentic_retrieval_system_prompt = models.TextField(default=prompts.AGENTIC_RETRIEVAL_SYSTEM_PROMPT)
    agentic_retrieval_question_prompt = models.TextField(default=prompts.AGENTIC_RETRIEVAL_QUESTION_PROMPT)
    agentic_give_up_system_prompt = models.TextField(default=prompts.AGENTIC_GIVE_UP_SYSTEM_PROMPT)
    agentic_give_up_question_prompt = models.TextField(default=prompts.AGENTIC_GIVE_UP_QUESTION_PROMPT)
    condense_system_prompt = models.TextField(default=prompts.CONDENSE_SYSTEM_PROMPT)
    condense_question_prompt = models.TextField(
        default=prompts.CONDENSE_QUESTION_PROMPT
    )
    map_max_concurrency = models.PositiveIntegerField(default=128)
    chat_map_system_prompt = models.TextField(default=prompts.CHAT_MAP_SYSTEM_PROMPT)
    chat_map_question_prompt = models.TextField(
        default=prompts.CHAT_MAP_QUESTION_PROMPT
    )
    reduce_system_prompt = models.TextField(default=prompts.REDUCE_SYSTEM_PROMPT)
    match_boost = models.PositiveIntegerField(default=1)
    knn_boost = models.PositiveIntegerField(default=1)
    similarity_threshold = models.PositiveIntegerField(default=0)

    def __str__(self) -> str:
        return str(self.label)

    registered_models: models.QuerySet["RegisteredModels"]

    def get_default_model(self) -> MLModel:
        """Gets the model registered to the config"""
        default_model_setting = self.registered_models.filter(default=True).first()
        return default_model_setting.model if default_model_setting else None


class User(BaseUser, UUIDPrimaryKeyBase):
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
        CFIN = "CFIN", _("Corporate finance")
        CF = "CF", _("Counter fraud")
        DDT = "DDT", _("Digital, data and technology")
        EC = "EC", _("Economics")
        FIN = "FIN", _("Finance")
        FEDG = "FEDG", _("Fraud, error, debts and grants")
        HR = "HR", _("Human resources")
        IA = "IA", _("Intelligence analysis")
        IAUD = "IAUD", _("Internal audit")
        IT = "IT", _("International trade")
        KIM = "KIM", _("Knowledge and information management")
        LG = "LG", _("Legal")
        MD = "MD", _("Medical")
        OP = "OP", _("Occupational psychology")
        OD = "OD", _("Operational delivery")
        OR = "OR", _("Operational research")
        PL = "PL", _("Planning")
        PI = "PI", _("Planning inspection")
        POL = "POL", _("Policy")
        PD = "PD", _("Project delivery")
        PR = "PR", _("Property")
        SE = "SE", _("Science and engineering")
        SC = "SC", _("Security")
        SR = "SR", _("Social research")
        ST = "ST", _("Statistics")
        TX = "TX", _("Tax")
        VET = "VET", _("Veterinary")
        OT = "OT", _("Other")

    class BusinessUnit(models.TextChoices):
        PRIME_MINISTERS_OFFICE = "Prime Minister's Office", _("Prime Minister's Office")
        DELIVERY_GROUP = "Delivery Group", _("Delivery Group")
        NATIONAL_SECURITY_SECRETARIAT = "National Security Secretariat", _(
            "National Security Secretariat"
        )
        ECONOMIC_AND_DOMESTIC_SECRETARIAT = "Economic and Domestic Secretariat", _(
            "Economic and Domestic Secretariat"
        )
        PROPRIETY_AND_CONSTITUTION_GROUP = "Propriety and Constitution Group", _(
            "Propriety and Constitution Group"
        )
        GOVERNMENT_IN_PARLIAMENT = "Government in Parliament", _(
            "Government in Parliament"
        )
        JOINT_INTELLIGENCE_ORGANISATION = "Joint Intelligence Organisation", _(
            "Joint Intelligence Organisation"
        )
        INTELLIGENCE_AND_SECURITY_COMMITTEE = (
            "Intelligence and Security Committee",
            _("Intelligence and Security Committee"),
        )
        GOVERNMENT_DIGITAL_SERVICE = "Government Digital Service", _(
            "Government Digital Service"
        )
        CENTRAL_DIGITAL_AND_DATA_OFFICE = "Central Digital and Data Office", _(
            "Central Digital and Data Office"
        )
        GOVERNMENT_COMMUNICATION_SERVICE = "Government Communication Service", _(
            "Government Communication Service"
        )
        GOVERNMENT_PEOPLE_GROUP = "Government People Group", _(
            "Government People Group"
        )
        GOVERNMENT_SECURITY_GROUP = "Government Security Group", _(
            "Government Security Group"
        )
        UKSV = "UKSV", _("UKSV")
        GOVERNMENT_COMMERCIAL_AND_GRANTS_FUNCTION = (
            "Government Commercial and Grants Function",
            _("Government Commercial and Grants Function"),
        )
        CIVIL_SERVICE_HUMAN_RESOURCES = "Civil Service Human Resources", _(
            "Civil Service Human Resources"
        )
        INFRASTRUCTURE_AND_PROJECTS_AUTHORITY = (
            "Infrastructure and Projects Authority",
            _("Infrastructure and Projects Authority"),
        )
        OFFICE_OF_GOVERNMENT_PROPERTY = "Office of Government Property", _(
            "Office of Government Property"
        )
        GOVERNMENT_BUSINESS_SERVICES = "Government Business Services", _(
            "Government Business Services"
        )
        BORDERS_UNIT = "Borders Unit", _("Borders Unit")
        EQUALITY_HUB = "Equality Hub", _("Equality Hub")
        PUBLIC_SECTOR_FRAUD_AUTHORITY = "Public Sector Fraud Authority", _(
            "Public Sector Fraud Authority"
        )
        CO_CHIEF_OPERATING_OFFICER = "CO Chief Operating Officer", _(
            "CO Chief Operating Officer"
        )
        FLEXIBLE_CS_POOL = "Flexible CS Pool", _("Flexible CS Pool")
        CO_PEOPLE_AND_PLACES = "CO People and Places", _("CO People and Places")
        CO_STRATEGY_FINANCE_AND_PERFORMANCE = (
            "CO Strategy, Finance, and Performance",
            _("CO Strategy Finance, and Performance"),
        )
        CENTRAL_COSTS = "Central Costs", _("Central Costs")
        CO_HMT_COMMERCIAL = "CO HMT Commercial", _("CO HMT Commercial")
        CO_DIGITAL = "CO Digital", _("CO Digital")
        PUBLIC_BODIES_AND_PRIORITY_PROJECTS_UNIT = (
            "Public Bodies and Priority Projects Unit",
            _("Public Bodies and Priority Projects Unit"),
        )
        PUBLIC_INQUIRY_RESPONSE_UNIT = "Public Inquiry Response Unit", _(
            "Public Inquiry Response Unit"
        )
        CS_MODERNISATION_AND_REFORM_UNIT = "CS Modernisation and Reform Unit", _(
            "CS Modernisation and Reform Unit"
        )
        OFFICE_FOR_VETERANS_AFFAIRS = "Office for Veterans' Affairs", _(
            "Office for Veterans' Affairs"
        )
        GRENFELL_INQUIRY = "Grenfell Inquiry", _("Grenfell Inquiry")
        INFECTED_BLOOD_INQUIRY = "Infected Blood Inquiry", _("Infected Blood Inquiry")
        COVID_INQUIRY = "Covid Inquiry", _("Covid Inquiry")
        CIVIL_SERVICE_COMMISSION = "Civil Service Commission", _(
            "Civil Service Commission"
        )
        EQUALITY_AND_HUMAN_RIGHTS_COMMISSION = (
            "Equality and Human Rights Commission",
            _("Equality and Human Rights Commission"),
        )
        GOVERNMENT_PROPERTY_AGENCY = "Government Property Agency", _(
            "Government Property Agency"
        )
        OFFICE_OF_THE_REGISTRAR_OF_CONSULTANT_LOBBYISTS = (
            "Office of the Registrar of Consultant Lobbyists",
            _("Office of the Registrar of Consultant Lobbyists"),
        )
        CROWN_COMMERCIAL_SERVICE = "Crown Commercial Service", _(
            "Crown Commercial Service"
        )
        UNION_AND_CONSTITUTION_GROUP = "Union and Constitution Group", _(
            "Union and Constitution Group"
        )
        GEOSPATIAL_COMMISSION = "Geospatial Commission", _("Geospatial Commission")
        COMMERCIAL_MODELS = "Commercial Models", _("Commercial Models")
        COP_PRESIDENCY = "COP Presidency", _("COP Presidency")
        INQUIRIES_SPONSORSHIP_TEAM = "Inquiries Sponsorship Team", _(
            "Inquiries Sponsorship Team"
        )
        OTHER = "Other", _("Other")

    class AIExperienceLevel(models.TextChoices):
        CURIOUS_NEWCOMER = "Curious Newcomer", _("I haven't used Generative AI tools")
        CAUTIOUS_EXPLORER = "Cautious Explorer", _(
            "I have a little experience using Generative AI tools"
        )
        ENTHUSIASTIC_EXPERIMENTER = (
            "Enthusiastic Experimenter",
            _(
                "I occasionally use Generative AI tools but am still experimenting with their capabilities"
            ),
        )
        EXPERIENCED_NAVIGATOR = (
            "Experienced Navigator",
            _(
                "I use Generative AI tools regularly and have a good understanding of their strengths and limitations"
            ),
        )
        AI_ALCHEMIST = (
            "AI Alchemist",
            _(
                "I have extensive experience with Generative AI tools and can leverage them effectively in various "
                "contexts"
            ),
        )

    username = None
    verified = models.BooleanField(default=False, blank=True, null=True)
    invited_at = models.DateTimeField(default=None, blank=True, null=True)
    invite_accepted_at = models.DateTimeField(default=None, blank=True, null=True)
    last_token_sent_at = models.DateTimeField(editable=False, blank=True, null=True)
    password = models.CharField("password", max_length=128, blank=True, null=True)
    business_unit = models.CharField(
        null=True, blank=True, max_length=64, choices=BusinessUnit
    )
    grade = models.CharField(null=True, blank=True, max_length=3, choices=UserGrade)
    name = models.CharField(null=True, blank=True)
    ai_experience = models.CharField(null=True, blank=True, max_length=25, choices=AIExperienceLevel)
    profession = models.CharField(null=True, blank=True, max_length=4, choices=Profession)
    info_about_user = models.CharField(null=True, blank=True, help_text="user entered info from profile overlay")
    redbox_response_preferences = models.CharField(
        null=True, blank=True, help_text="user entered info from profile overlay, to be used in custom prompt"
    )
    ai_settings = models.ForeignKey(AISettings, on_delete=models.SET_DEFAULT, default="default", to_field="label")
    is_developer = models.BooleanField(null=True, blank=True, default=False, help_text="is this user a developer?")
    objects = BaseUserManager()

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


class StatusEnum(models.TextChoices):
    complete = "complete"
    deleted = "deleted"
    errored = "errored"
    processing = "processing"


INACTIVE_STATUSES = [StatusEnum.deleted, StatusEnum.errored]


class InactiveFileError(ValueError):
    def __init__(self, file):
        super().__init__(f"{file.pk} is inactive, status is {file.status}")


class File(UUIDPrimaryKeyBase, TimeStampedModel):
    status = models.CharField(choices=StatusEnum.choices, null=False, blank=False)
    original_file = models.FileField(storage=settings.STORAGES["default"]["BACKEND"])
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    original_file_name = models.TextField(max_length=2048, blank=True, null=True)
    core_file_uuid = models.UUIDField(null=True)
    last_referenced = models.DateTimeField(blank=True, null=True)
    ingest_error = models.TextField(
        max_length=2048,
        blank=True,
        null=True,
        help_text="error, if any, encountered during ingest",
    )

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.original_file_name} {self.user}"

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
                body={
                    "query": {"term": {"metadata.file_name.keyword": self.unique_name}}
                },
            )

    def update_status_from_core(self, status_label):
        match status_label:
            case "complete":
                self.status = StatusEnum.complete
            case "failed":
                self.status = StatusEnum.errored
            case _:
                self.status = StatusEnum.processing
        self.save()

    @property
    def file_type(self) -> str:
        name = self.original_file.name
        return name.split(".")[-1]

    @property
    def url(self) -> URL | None:
        #  In dev environment, get pre-signed url from minio
        if settings.ENVIRONMENT.uses_minio:
            s3 = boto3.client(
                "s3",
                endpoint_url="http://localhost:9000",
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_S3_SECRET_ACCESS_KEY,
                config=Config(signature_version="s3v4"),
                region_name=settings.AWS_S3_REGION_NAME,
            )

            url = s3.generate_presigned_url(
                ClientMethod="get_object",
                Params={
                    "Bucket": settings.AWS_STORAGE_BUCKET_NAME,
                    "Key": self.name,
                },
            )
            return URL(url)

        if not self.original_file:
            logger.error(
                "attempt to access non-existent file %s", self.pk, stack_info=True
            )
            return None

        return URL(self.original_file.url)

    @property
    def name(self) -> str:
        # User-facing name
        try:
            return self.original_file_name or self.original_file.name
        except ValueError as e:
            logger.exception(
                "attempt to access non-existent file %s", self.pk, exc_info=e
            )

    @property
    def unique_name(self) -> str:
        # Name used when processing files that exist in S3
        if self.status in INACTIVE_STATUSES:
            logger.exception("Attempt to access unique_name for inactive file %s with status %s", self.pk, self.status)
            raise InactiveFileError(self)
        return self.original_file.name

    def get_status_text(self) -> str:
        return next(
            (status[1] for status in StatusEnum.choices if self.status == status[0]),
            "Unknown",
        )

    @property
    def expires_at(self) -> datetime:
        return self.last_referenced + timedelta(seconds=settings.FILE_EXPIRY_IN_SECONDS)

    @property
    def expires(self) -> timedelta:
        return self.expires_at - datetime.now(tz=UTC)

    def __lt__(self, other):
        return self.id < other.id

    @classmethod
    def get_completed_and_processing_files(
        cls, user: User
    ) -> tuple[Sequence["File"], Sequence["File"]]:
        """Returns all files that are completed and processing for a given user."""

        completed_files = cls.objects.filter(
            user=user, status=StatusEnum.complete
        ).order_by("-created_at")
        processing_files = cls.objects.filter(
            user=user, status=StatusEnum.processing
        ).order_by("-created_at")
        return completed_files, processing_files

    @classmethod
    def get_ordered_by_citation_priority(
        cls, chat_message_id: uuid.UUID
    ) -> Sequence["File"]:
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
        null=True, blank=True, help_text="Did Redbox do what you needed it to in this chat?"
    )
    feedback_saved_time = models.BooleanField(null=True, blank=True, help_text="Did Redbox help save you time?")
    feedback_improved_work = models.BooleanField(
        null=True, blank=True, help_text="Did Redbox help to improve your work?"
    )
    feedback_notes = models.TextField(null=True, blank=True, help_text="Do you want to tell us anything further?")

    def __str__(self) -> str:  # pragma: no cover
        return self.name or ""

    @override
    def save(
        self, force_insert=False, force_update=False, using=None, update_fields=None
    ):
        self.name = sanitise_string(self.name)

        if self.chat_backend is None:
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
        return self.chatmessage_set.aggregate(newest_date=Max("created_at"))[
            "newest_date"
        ].date()

    @property
    def date_group(self):
        return get_date_group(self.newest_message_date)


class ChatRoleEnum(models.TextChoices):
    ai = "ai"
    user = "user"
    system = "system"


class Citation(UUIDPrimaryKeyBase, TimeStampedModel):
    file = models.ForeignKey(File, on_delete=models.CASCADE)
    chat_message = models.ForeignKey("ChatMessage", on_delete=models.CASCADE)
    text = models.TextField(null=True, blank=True)
    page_numbers = ArrayField(
        models.PositiveIntegerField(),
        null=True,
        blank=True,
        help_text="location of citation in document",
    )

    def __str__(self):
        return f"{self.file}: {self.text or ''}"

    def save(
        self, force_insert=False, force_update=False, using=None, update_fields=None
    ):
        self.text = sanitise_string(self.text)
        super().save(force_insert, force_update, using, update_fields)


class ChatMessage(UUIDPrimaryKeyBase, TimeStampedModel):
    chat = models.ForeignKey(Chat, on_delete=models.CASCADE)
    text = models.TextField(max_length=32768, null=False, blank=False)
    role = models.CharField(choices=ChatRoleEnum.choices, null=False, blank=False)
    route = models.CharField(max_length=25, null=True, blank=True)
    selected_files = models.ManyToManyField(
        File, related_name="+", symmetrical=False, blank=True
    )
    source_files = models.ManyToManyField(File, through=Citation)

    rating = models.PositiveIntegerField(
        blank=True,
        null=True,
        validators=[validators.MinValueValidator(1), validators.MaxValueValidator(5)],
    )
    rating_text = models.TextField(blank=True, null=True)
    rating_chips = ArrayField(models.CharField(max_length=32), null=True, blank=True)

    def __str__(self) -> str:  # pragma: no cover
        return self.text[:20] + "..."

    def save(
        self, force_insert=False, force_update=False, using=None, update_fields=None
    ):
        self.text = sanitise_string(self.text)
        self.rating_text = sanitise_string(self.rating_text)

        super().save(force_insert, force_update, using, update_fields)

    @classmethod
    def get_messages_ordered_by_citation_priority(
        cls, chat_id: uuid.UUID
    ) -> Sequence["ChatMessage"]:
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


class ChatMessageTokenUse(UUIDPrimaryKeyBase, TimeStampedModel):
    class UseTypeEnum(models.TextChoices):
        INPUT = "input", _("input")
        OUTPUT = "output", _("output")

    chat_message = models.ForeignKey(ChatMessage, on_delete=models.CASCADE)
    use_type = models.CharField(
        max_length=10,
        choices=UseTypeEnum,
        help_text="input or output tokens",
        default=UseTypeEnum.INPUT,
    )
    model_name = models.CharField(max_length=50, null=True, blank=True)
    token_count = models.PositiveIntegerField(null=True, blank=True)

    def __str__(self) -> str:
        return f"{self.model_name} {self.use_type}"
