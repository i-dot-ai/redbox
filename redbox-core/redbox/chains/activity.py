"""
Activity Log methods and classes
"""

from langchain_core.callbacks.manager import dispatch_custom_event

from redbox.models.graph import RedboxActivityEvent, RedboxEventType


def log_activity(activity_event: str | RedboxActivityEvent):
    if isinstance(activity_event, str):
        _log_activity(RedboxActivityEvent(message=activity_event))
    else:
        _log_activity(activity_event)


def _log_activity(event: RedboxActivityEvent):
    dispatch_custom_event(name=RedboxEventType.activity, data=event)
