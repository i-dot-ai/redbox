from redbox_app.redbox_core.dash_apps import report_app
from redbox_app.redbox_core.views.auth_views import sign_in_link_sent_view, sign_in_view, signed_out_view
from redbox_app.redbox_core.views.chat_views import ChatsTitleView, ChatsView, DeleteChat, UpdateChatFeedback
from redbox_app.redbox_core.views.citation_views import CitationsView
from redbox_app.redbox_core.views.demographics_views import (
    CheckDemographicsView,
    DemographicsView,
    UpdateDemographicsView,
)
from redbox_app.redbox_core.views.document_views import (
    DocumentView,
    UploadView,
    file_status_api_view,
    remove_doc_view,
)
from redbox_app.redbox_core.views.info_views import accessibility_statement_view, privacy_notice_view, support_view
from redbox_app.redbox_core.views.misc_views import SecurityTxtRedirectView, health, homepage_view
from redbox_app.redbox_core.views.ratings_views import RatingsView
from redbox_app.redbox_core.views.signup_views import Signup1, Signup2

__all__ = [
    "ChatsTitleView",
    "ChatsView",
    "CitationsView",
    "CheckDemographicsView",
    "DemographicsView",
    "DocumentView",
    "RatingsView",
    "SecurityTxtRedirectView",
    "UploadView",
    "UpdateDemographicsView",
    "file_status_api_view",
    "health",
    "homepage_view",
    "remove_doc_view",
    "privacy_notice_view",
    "accessibility_statement_view",
    "support_view",
    "sign_in_view",
    "sign_in_link_sent_view",
    "signed_out_view",
    "Signup1",
    "Signup2",
    "report_app",
    "UpdateChatFeedback",
    "DeleteChat",
]
