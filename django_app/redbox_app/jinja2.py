import datetime
import json
import logging

import humanize
import jinja2
import pytz
import requests
import waffle
from django.conf import settings
from django.templatetags.static import static
from django.urls import reverse
from django.utils.timezone import template_localtime
from markdown_it import MarkdownIt

logger = logging.getLogger(__name__)

# `js-default` setting required to sanitize inputs
# https://markdown-it-py.readthedocs.io/en/latest/security.html
markdown_converter = MarkdownIt("js-default")


def url(path, *args, **kwargs):
    if args and kwargs:
        message = "Use *args or **kwargs, not both."
        raise ValueError(message)
    return reverse(path, args=args, kwargs=kwargs)


def markdown(text, cls=None):
    """
    Converts the given text into markdown.
    The `replace` statement replaces the outer <p> tag with one that contains the given class, otherwise the markdown
    ends up double wrapped with <p> tags.
    Args:
        text: The text to convert to markdown
        cls (optional): The class to apply to the outermost <p> tag surrounding the markdown

    Returns:
        Text converted to markdown
    """
    html = markdown_converter.render(text).strip()
    return html.replace("<p>", f'<p class="{cls or ""}">', 1).replace("</p>", "", 1)


def humanise_expiry(delta: datetime.timedelta) -> str:
    if delta.total_seconds() > 0:
        return f"{humanize.naturaldelta(delta)}"
    else:
        return f"{humanize.naturaldelta(delta)} ago"


def humanize_timedelta(delta: datetime.timedelta):
    return humanize.naturaldelta(delta)


def humanize_short_timedelta(minutes=0, hours_limit=200, too_large_msg=""):
    if minutes > (hours_limit * 60):
        if not too_large_msg:
            return f"More than {hours_limit} hours"
        else:
            return too_large_msg
    else:
        delta = datetime.timedelta(minutes=minutes)
        return humanize.precisedelta(delta, minimum_unit="minutes")


def render_lit(html):
    try:
        lit_ssr_url = f"http://{settings.LIT_SSR_URL}:3002/"
        logger.info("using LIT_SSR_URL=%s", lit_ssr_url)
        response = requests.get(lit_ssr_url, timeout=1, params={"data": html})
        logger.info("status_code=%s", response.status_code)
        response.raise_for_status()
        return response.text  # noqa: TRY300
    except requests.RequestException:
        return html


def filter_docs(docs, messages, message_index):
    """
    Filter the documents based on the timestamp of the messages
    This ensures each document is displayed in the correct container / order
    """
    start_timestamp = datetime.datetime.now(pytz.timezone("Europe/London")) - datetime.timedelta(days=999)
    if message_index > 0:
        start_timestamp = messages[message_index - 1].created_at
    end_timestamp = datetime.datetime.now(pytz.timezone("Europe/London"))
    if message_index < messages.count():
        end_timestamp = messages[message_index].created_at
    filtered_docs = [doc for doc in docs if start_timestamp < doc.created_at < end_timestamp]
    return json.dumps(
        [{"id": str(doc.id), "file_name": doc.file_name, "file_status": doc.get_status_text()} for doc in filtered_docs]
    )


def to_json(value):
    return json.dumps(value)


def to_user_timezone(value):
    # Assuming the user's timezone is stored in a variable called 'user_timezone'
    # Replace 'Europe/London' with the actual timezone string for the user
    user_tz = pytz.timezone("Europe/London")
    return value.astimezone(user_tz).strftime("%H:%M %d/%m/%Y")


def environment(**options):
    extra_options = {}

    env = jinja2.Environment(  # nosec: B701 # noqa: S701
        **{
            "autoescape": True,
            **options,
            **extra_options,
        },
    )
    env.filters.update(
        {
            "static": static,
            "url": url,
            "humanise_expiry": humanise_expiry,
            "template_localtime": template_localtime,
            "to_user_timezone": to_user_timezone,
            "environment": settings.ENVIRONMENT.value,
            "security": settings.MAX_SECURITY_CLASSIFICATION.value,
            "waffle_flag": waffle.flag_is_active,
            "render_lit": render_lit,
            "filter_docs": filter_docs,
            "to_json": to_json,
        }
    )
    env.globals.update(
        {
            "static": static,
            "url": url,
            "humanise_expiry": humanise_expiry,
            "template_localtime": template_localtime,
            "to_user_timezone": to_user_timezone,
            "environment": settings.ENVIRONMENT.value,
            "security": settings.MAX_SECURITY_CLASSIFICATION.value,
            "waffle_flag": waffle.flag_is_active,
            "google_analytics_tag": settings.GOOGLE_ANALYTICS_TAG,
            "google_analytics_link": settings.GOOGLE_ANALYTICS_LINK,
        }
    )
    return env
