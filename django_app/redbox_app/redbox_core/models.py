import contextlib
import logging
import os
import textwrap
import uuid
from collections.abc import Collection, Sequence
from datetime import UTC, date, datetime, timedelta
from typing import override

import elastic_transport
from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.core import validators
from django.db import models
from django.db.models import Max, Min, Sum, UniqueConstraint
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django_q.models import OrmQ, Success
from django_q.tasks import async_task
from django_use_email_as_username.models import BaseUser, BaseUserManager
from langchain_core.documents import Document
from langchain_core.messages import AIMessage, AnyMessage, HumanMessage
from pytz import utc

import redbox.models.chain
from redbox.chains.components import get_tokeniser
from redbox.models.settings import get_settings
from redbox_app.redbox_core import error_messages
from redbox_app.redbox_core.utils import get_date_group, sanitise_string
from redbox_app.worker import ingest

logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

env = get_settings()
tokeniser = get_tokeniser()


def escape_curly_brackets(text: str) -> str:
    return text.replace("{", "{{").replace("}", "}}")


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
    context_window_size = models.PositiveIntegerField(help_text="size of the LLM context window")
    rate_limit = models.PositiveIntegerField(default=1000000, help_text="tokens per minute allowed by this model")

    class Meta:
        constraints = [UniqueConstraint(fields=["name", "provider"], name="unique_name_provider")]

    def __str__(self):
        return self.display or self.name

    def save(self, *args, **kwargs):
        if self.is_default:
            ChatLLMBackend.objects.filter(is_default=True).update(is_default=False)
        super().save(*args, **kwargs)

    @classmethod
    def active_context_window_sizes(cls) -> dict[str, int]:
        return {str(o): o.context_window_size for o in cls.objects.filter(enabled=True)}


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
        BORDERS_UNIT = "Borders Unit", _("Borders Unit")
        CENTRAL_COSTS = "Central Costs", _("Central Costs")
        CENTRAL_DIGITAL_AND_DATA_OFFICE = "Central Digital and Data Office", _("Central Digital and Data Office")
        CIVIL_SERVICE_COMMISSION = "Civil Service Commission", _("Civil Service Commission")
        CIVIL_SERVICE_HUMAN_RESOURCES = "Civil Service Human Resources", _("Civil Service Human Resources")
        CO_CHIEF_OPERATING_OFFICER = "CO Chief Operating Officer", _("CO Chief Operating Officer")
        CO_DIGITAL = "CO Digital", _("CO Digital")
        CO_HMT_COMMERCIAL = "CO HMT Commercial", _("CO HMT Commercial")
        CO_PEOPLE_AND_PLACES = "CO People and Places", _("CO People and Places")
        CO_STRATEGY_FINANCE_AND_PERFORMANCE = (
            "CO Strategy, Finance, and Performance",
            _("CO Strategy Finance, and Performance"),
        )
        COMMERCIAL_MODELS = "Commercial Models", _("Commercial Models")
        COP_PRESIDENCY = "COP Presidency", _("COP Presidency")
        COVID_INQUIRY = "Covid Inquiry", _("Covid Inquiry")
        CROWN_COMMERCIAL_SERVICE = "Crown Commercial Service", _("Crown Commercial Service")
        CS_MODERNISATION_AND_REFORM_UNIT = "CS Modernisation and Reform Unit", _("CS Modernisation and Reform Unit")
        DELIVERY_GROUP = "Delivery Group", _("Delivery Group")
        ECONOMIC_AND_DOMESTIC_SECRETARIAT = "Economic and Domestic Secretariat", _("Economic and Domestic Secretariat")
        EQUALITY_AND_HUMAN_RIGHTS_COMMISSION = (
            "Equality and Human Rights Commission",
            _("Equality and Human Rights Commission"),
        )
        EQUALITY_HUB = "Equality Hub", _("Equality Hub")
        FLEXIBLE_CS_POOL = "Flexible CS Pool", _("Flexible CS Pool")
        GEOSPATIAL_COMMISSION = "Geospatial Commission", _("Geospatial Commission")
        GOVERNMENT_BUSINESS_SERVICES = "Government Business Services", _("Government Business Services")
        GOVERNMENT_COMMERCIAL_AND_GRANTS_FUNCTION = (
            "Government Commercial and Grants Function",
            _("Government Commercial and Grants Function"),
        )
        GOVERNMENT_COMMUNICATION_SERVICE = "Government Communication Service", _("Government Communication Service")
        GOVERNMENT_DIGITAL_SERVICE = "Government Digital Service", _("Government Digital Service")
        GOVERNMENT_IN_PARLIAMENT = "Government in Parliament", _("Government in Parliament")
        GOVERNMENT_LEGAL_DEPARTMENT = "Government Legal Department", _("Government Legal Department")
        GOVERNMENT_PEOPLE_GROUP = "Government People Group", _("Government People Group")
        GOVERNMENT_PROPERTY_AGENCY = "Government Property Agency", _("Government Property Agency")
        GOVERNMENT_SECURITY_GROUP = "Government Security Group", _("Government Security Group")
        GRENFELL_INQUIRY = "Grenfell Inquiry", _("Grenfell Inquiry")
        INFECTED_BLOOD_INQUIRY = "Infected Blood Inquiry", _("Infected Blood Inquiry")
        INFRASTRUCTURE_AND_PROJECTS_AUTHORITY = (
            "Infrastructure and Projects Authority",
            _("Infrastructure and Projects Authority"),
        )
        INQUIRIES_SPONSORSHIP_TEAM = "Inquiries Sponsorship Team", _("Inquiries Sponsorship Team")
        INTELLIGENCE_AND_SECURITY_COMMITTEE = (
            "Intelligence and Security Committee",
            _("Intelligence and Security Committee"),
        )
        JOINT_INTELLIGENCE_ORGANISATION = "Joint Intelligence Organisation", _("Joint Intelligence Organisation")
        NATIONAL_SECURITY_SECRETARIAT = "National Security Secretariat", _("National Security Secretariat")
        OFFICE_FOR_VETERANS_AFFAIRS = "Office for Veterans' Affairs", _("Office for Veterans' Affairs")
        OFFICE_OF_GOVERNMENT_PROPERTY = "Office of Government Property", _("Office of Government Property")
        OFFICE_OF_THE_REGISTRAR_OF_CONSULTANT_LOBBYISTS = (
            "Office of the Registrar of Consultant Lobbyists",
            _("Office of the Registrar of Consultant Lobbyists"),
        )
        PRIME_MINISTERS_OFFICE = "Prime Minister's Office", _("Prime Minister's Office")
        PROPRIETY_AND_CONSTITUTION_GROUP = "Propriety and Constitution Group", _("Propriety and Constitution Group")
        PUBLIC_BODIES_AND_PRIORITY_PROJECTS_UNIT = (
            "Public Bodies and Priority Projects Unit",
            _("Public Bodies and Priority Projects Unit"),
        )
        PUBLIC_INQUIRY_RESPONSE_UNIT = "Public Inquiry Response Unit", _("Public Inquiry Response Unit")
        PUBLIC_SECTOR_FRAUD_AUTHORITY = "Public Sector Fraud Authority", _("Public Sector Fraud Authority")
        UKSV = "UKSV", _("UKSV")
        UNION_AND_CONSTITUTION_GROUP = "Union and Constitution Group", _("Union and Constitution Group")
        OTHER = "Other", _("Other")

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

    username = None
    password = models.CharField("password", max_length=128, blank=True, null=True)
    business_unit = models.CharField(null=True, blank=True, max_length=64, choices=BusinessUnit)
    grade = models.CharField(null=True, blank=True, max_length=3, choices=UserGrade)
    name = models.CharField(null=True, blank=True)
    ai_experience = models.CharField(null=True, blank=True, max_length=25, choices=AIExperienceLevel)
    profession = models.CharField(null=True, blank=True, max_length=4, choices=Profession)
    info_about_user = models.CharField(null=True, blank=True, help_text="user entered info from profile overlay")
    redbox_response_preferences = models.CharField(
        null=True,
        blank=True,
        help_text="user entered info from profile overlay, to be used in custom prompt",
    )
    is_developer = models.BooleanField(null=True, blank=True, default=False, help_text="is this user a developer?")

    # Additional fields for sign-up form
    # Page 1
    role = models.TextField(null=True, blank=True)
    # Archived (old Page 2)
    accessibility_options = models.CharField(null=True, blank=True, max_length=64, choices=AccessibilityOptions)
    accessibility_categories = models.CharField(null=True, blank=True, max_length=64, choices=AccessibilityCategories)
    accessibility_description = models.TextField(null=True, blank=True)
    # Archived (old Page 3)
    digital_confidence = models.CharField(null=True, blank=True, max_length=128, choices=DigitalConfidence)
    usage_at_work = models.CharField(null=True, blank=True, max_length=64, choices=RegularityAI)
    usage_outside_work = models.CharField(null=True, blank=True, max_length=64, choices=RegularityAI)
    how_useful = models.CharField(null=True, blank=True, max_length=64, choices=Usefulness)
    redbox_tasks = models.TextField(null=True, blank=True)
    # Archived (old Page 4)
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
    # Archived (old Page 5)
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
    # Page 3 (old Page 6)
    consent_research = models.BooleanField(null=True, blank=True, default=False)
    consent_interviews = models.BooleanField(null=True, blank=True, default=False)
    consent_feedback = models.BooleanField(null=True, blank=True, default=False)
    consent_condfidentiality = models.BooleanField(null=True, blank=True, default=False)
    consent_understand = models.BooleanField(null=True, blank=True, default=False)
    consent_agreement = models.BooleanField(null=True, blank=True, default=False)

    objects = BaseUserManager()

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.email}"

    def save(self, *args, **kwargs):
        self.email = self.email.lower()
        super().save(*args, **kwargs)

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


class Chat(UUIDPrimaryKeyBase, TimeStampedModel):
    name = models.TextField(max_length=1024, null=False, blank=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    archived = models.BooleanField(default=False, null=True, blank=True)
    chat_backend = models.ForeignKey(ChatLLMBackend, on_delete=models.CASCADE, help_text="LLM to use in chat")
    temperature = models.FloatField(default=0, help_text="temperature for LLM")

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
            self.chat_backend = ChatLLMBackend.objects.get(is_default=True)

        if self.temperature is None:
            self.temperature = 0

        super().save(force_insert, force_update, using, update_fields)

    @classmethod
    def get_ordered_by_last_message_date(
        cls, user: User, exclude_chat_ids: Collection[uuid.UUID] | None = None
    ) -> Sequence["Chat"]:
        """Returns all chat histories for a given user, ordered by the date of the latest message."""
        exclude_chat_ids = exclude_chat_ids or []
        return (
            cls.objects.filter(user=user, archived=False, chatmessage__isnull=False)
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

    def to_langchain(self) -> redbox.models.chain.RedboxState:
        chat_backend = redbox.models.chain.ChatLLMBackend(
            name=self.chat_backend.name,
            provider=self.chat_backend.provider,
            description=self.chat_backend.description,
            context_window_size=self.chat_backend.context_window_size,
        )

        return redbox.models.chain.RedboxState(
            documents=[Document(str(f.text), metadata={"uri": f.original_file.name}) for f in self.file_set.all()],
            messages=[message.to_langchain() for message in self.chatmessage_set.order_by("created_at")],
            chat_backend=chat_backend,
        )

    def context_window_size(self) -> int:
        return self.chat_backend.context_window_size

    def token_count(self) -> int:
        def f(obj):
            return obj.aggregate(Sum("token_count"))["token_count__sum"] or 0

        return f(self.file_set) + f(self.chatmessage_set)


class InactiveFileError(ValueError):
    def __init__(self, file):
        super().__init__(f"{file.pk} is inactive, status is {file.status}")


def build_s3_key(instance, filename: str) -> str:
    """the s3-key is the primary key for a file,
    this needs to be unique so that if a user uploads a file with the same name as
    1. an existing file that they own, then it is overwritten
    2. an existing file that another user owns then a new file is created
    """
    return f"{instance.chat.user.email}/{filename}"


class File(UUIDPrimaryKeyBase, TimeStampedModel):
    class Status(models.TextChoices):
        complete = "complete"
        errored = "errored"
        processing = "processing"

    status = models.CharField(choices=Status.choices, null=False, blank=False)
    original_file = models.FileField(
        storage=settings.STORAGES["default"]["BACKEND"],
        upload_to=build_s3_key,
    )
    last_referenced = models.DateTimeField(blank=True, null=True)
    ingest_error = models.TextField(
        max_length=2048,
        blank=True,
        null=True,
        help_text="error, if any, encountered during ingest",
    )
    chat = models.ForeignKey(
        Chat,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        help_text="chat that this document belongs to, which may be nothing for now",
    )
    text = models.TextField(null=True, blank=True, help_text="text extracted from file")
    token_count = models.PositiveIntegerField(null=True, blank=True, help_text="number of tokens in extracted text")
    task = models.ForeignKey(
        OrmQ, on_delete=models.SET_NULL, null=True, blank=True, help_text="pending text extraction task"
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
        self.original_file.delete(save=False)
        super().delete()

    @property
    def url(self) -> str:
        return self.original_file.url

    @property
    def file_name(self) -> str:
        # could have a stronger (regex?) way of stripping the users email address?
        if "/" in self.original_file.name:
            return self.original_file.name.split("/")[1]

        logger.error("expected filename=%s to start with the user's email address", self.original_file.name)
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

    def ingest(self, sync: bool = False):
        task = async_task(ingest, self.id, task_name=self.file_name, group="ingest", sync=sync)
        if sync:
            result = Success.objects.get(pk=task)
            self.status = self.Status.complete if result.success else self.Status.errored
        else:
            self.task = next(item for item in OrmQ.objects.all() if item.task["id"] == task)
        self.save()

    @classmethod
    def get_completed_and_processing_files(cls, chat_id: uuid.UUID) -> tuple[Sequence["File"], Sequence["File"]]:
        """Returns all files that are completed and processing for a given user."""

        completed_files = cls.objects.filter(chat_id=chat_id, status=File.Status.complete).order_by("-created_at")
        processing_files = cls.objects.filter(chat_id=chat_id, status=File.Status.processing).order_by("-created_at")
        return completed_files, processing_files

    @classmethod
    def get_ordered_by_citation_priority(cls, chat_message_id: uuid.UUID) -> Sequence["File"]:
        """Returns all files that are cited in a given chat message, ordered by citation priority."""
        return (
            cls.objects.filter(citation__chat_message_id=chat_message_id)
            .annotate(min_created_at=Min("citation__created_at"))
            .order_by("min_created_at")
        )

    def position_in_queue(self) -> int:
        if not self.task_id:
            return -1
        return OrmQ.objects.filter(lock__lt=self.task.lock).count()


class ChatMessage(UUIDPrimaryKeyBase, TimeStampedModel):
    class Role(models.TextChoices):
        ai = "ai"
        user = "user"
        system = "system"

    chat = models.ForeignKey(Chat, on_delete=models.CASCADE)
    text = models.TextField(max_length=32768, null=False, blank=False)
    role = models.CharField(choices=Role.choices, null=False, blank=False)

    rating = models.PositiveIntegerField(
        blank=True,
        null=True,
        validators=[validators.MinValueValidator(1), validators.MaxValueValidator(5)],
    )
    rating_text = models.TextField(blank=True, null=True)
    rating_chips = ArrayField(models.CharField(max_length=32), null=True, blank=True)
    token_count = models.PositiveIntegerField(null=True, blank=True, help_text="number of tokens in the message")
    delay = models.FloatField(default=0, help_text="by how much was this message delayed in seconds")

    def __str__(self) -> str:  # pragma: no cover
        return textwrap.shorten(self.text, width=20, placeholder="...")

    @property
    def associated_file_token_count(self):
        """count token of all files created before this chat
        that would have been used in the creation of this message
        """
        if self.role == self.Role.ai:
            return 0

        return self.chat.file_set.filter(
            created_at__lt=datetime.now(tz=utc),
        ).aggregate(Sum("token_count"))["token_count__sum"] or 0

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        self.text = sanitise_string(self.text)
        self.rating_text = sanitise_string(self.rating_text)
        self.token_count = self.associated_file_token_count + len(tokeniser.encode(self.text))
        super().save(force_insert, force_update, using, update_fields)
        self.log()

    @classmethod
    def get_messages(cls, chat_id: uuid.UUID) -> Sequence["ChatMessage"]:
        """Returns all chat messages for a given chat history, ordered by citation priority."""
        return cls.objects.filter(chat_id=chat_id).order_by("created_at")

    def to_langchain(self) -> AnyMessage:
        if self.role == self.Role.ai:
            return AIMessage(content=escape_curly_brackets(self.text))
        return HumanMessage(content=escape_curly_brackets(self.text))

    def log(self):
        n_selected_files = self.chat.file_set.count()
        elastic_log_msg = {
            "@timestamp": self.created_at.isoformat(),
            "id": str(self.id),
            "chat_id": str(self.chat.id),
            "user_id": str(self.chat.user.id),
            "department": self.chat.user.email.split("@")[-1],
            "user_business_unit": self.chat.user.business_unit,
            "user_grade": self.chat.user.grade,
            "user_profession": self.chat.user.profession,
            "user_ai_experience": self.chat.user.ai_experience,
            "route": "chat_with_docs" if n_selected_files else "chat",
            "role": self.role,
            "token_count": self.token_count,
            "rating": int(self.rating) if self.rating else None,
            "rating_text": str(self.rating_text),
            "rating_chips": list(map(str, self.rating_chips)) if self.rating_chips else None,
            "chat_feedback_achieved": self.chat.feedback_achieved,
            "chat_feedback_saved_time": self.chat.feedback_saved_time,
            "chat_feedback_improved_work": self.chat.feedback_improved_work,
            "n_selected_files": n_selected_files,
            "delay_seconds": self.delay,
        }
        if es_client := env.elasticsearch_client():
            try:
                es_client.create(
                    index=env.elastic_chat_mesage_index,
                    id=uuid.uuid4(),
                    document=elastic_log_msg,
                )
            except elastic_transport.ConnectionError:
                contextlib.suppress(elastic_transport.ConnectionError)


def get_unique_chat_title(title: str, user: User, number: int = 0) -> str:
    original_title = sanitise_string(title[: settings.CHAT_TITLE_LENGTH])
    new_title = original_title
    if number > 0:
        new_title = f"{original_title} ({number})"
    if Chat.objects.filter(name=new_title, user=user).exists():
        return get_unique_chat_title(original_title, user, number + 1)
    return new_title


def get_chat_session(user: User, chat_id: uuid.UUID, data: dict) -> tuple[Chat, float]:
    """create or update a Chat, and return a delay (seconds) to handle large traffic"""
    chat = Chat.objects.get(id=chat_id)

    if chat_backend_id := data.get("llm"):
        chat.chat_backend = ChatLLMBackend.objects.get(id=chat_backend_id)
        chat.save()

    if temperature := data.get("temperature", 0):
        chat.temperature = temperature
        chat.save()

    # Update session name if this is the first message
    if not chat.chatmessage_set.exists():
        chat.name = get_unique_chat_title(data.get("message", ""), user)
        chat.save()

    token_count_this_message = chat.token_count()

    active_context_window_sizes = ChatLLMBackend.active_context_window_sizes()

    if token_count_this_message > max(active_context_window_sizes.values()):
        raise ValueError(error_messages.FILES_TOO_LARGE)

    if token_count_this_message > chat.context_window_size():
        details = "\n".join(
            f"* `{k}`: {v} tokens" for k, v in active_context_window_sizes.items() if v >= token_count_this_message
        )
        msg = f"{error_messages.FILES_TOO_LARGE}.\nTry one of the following models:\n{details}"
        raise ValueError(msg)

    ChatMessage.objects.create(
        chat=chat,
        text=data.get("message", ""),
        role=ChatMessage.Role.user,
    )

    tokens_used_in_last_min = (
        ChatMessage.objects.filter(
            chat__chat_backend=chat.chat_backend,
            created_at__gt=datetime.now(tz=utc) - timedelta(minutes=1),
        ).aggregate(Sum("token_count"))["token_count__sum"]
        or 0
    )

    delay = token_count_this_message / (chat.chat_backend.rate_limit - tokens_used_in_last_min)

    delay = max(delay, 0)  # should never happen but just in case!

    return chat, delay * 60
