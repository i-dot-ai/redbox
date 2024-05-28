import datetime

import humanize
import jinja2
from compressor.contrib.jinja2ext import CompressorExtension
from django.conf import settings
from django.templatetags.static import static
from django.urls import reverse
from markdown_it import MarkdownIt

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


def humanize_timedelta(minutes=0, hours_limit=200, too_large_msg=""):
    if minutes > (hours_limit * 60):
        if not too_large_msg:
            return f"More than {hours_limit} hours"
        else:
            return too_large_msg
    else:
        delta = datetime.timedelta(minutes=minutes)
        return humanize.precisedelta(delta, minimum_unit="minutes")


def environment(**options):
    extra_options = {}
    env = jinja2.Environment(  # nosec B701 # noqa S701
        **{
            "autoescape": True,
            "extensions": [CompressorExtension],
            **options,
            **extra_options,
        },
    )
    env.filters.update(
        {
            "static": static,
            "url": url,
            "humanize_timedelta": humanize_timedelta,
            "environment": settings.ENVIRONMENT,
            "security": settings.MAX_SECURITY_CLASSIFICATION.value,
        }
    )
    env.globals.update(
        {
            "static": static,
            "url": url,
            "humanize_timedelta": humanize_timedelta,
            "environment": settings.ENVIRONMENT,
            "security": settings.MAX_SECURITY_CLASSIFICATION.value,
        }
    )
    return env
