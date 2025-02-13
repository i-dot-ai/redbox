from redbox_app.redbox_core.views.api_views import ChatMessageView
from redbox_app.redbox_core.views.auth_views import sign_in_link_sent_view, sign_in_view, signed_out_view
from redbox_app.redbox_core.views.chat_views import (
    ChatsTitleView,
    ChatsView,
    ChatsViewNew,
    DeleteChat,
    UpdateChatFeedback,
)
from redbox_app.redbox_core.views.demographics_views import (
    CheckDemographicsView,
    DemographicsView,
    UpdateDemographicsView,
)
from redbox_app.redbox_core.views.document_views import (
    UploadView,
    file_status_api_view,
    remove_doc_view,
)
from redbox_app.redbox_core.views.info_views import (
    accessibility_statement_view,
    cookies_view,
    privacy_notice_view,
    support_view,
)
from redbox_app.redbox_core.views.misc_views import SecurityTxtRedirectView, health, homepage_view
from redbox_app.redbox_core.views.signup_views import Signup1, Signup2, Signup3, Signup4

__all__ = [
    "ChatMessageView",
    "ChatsTitleView",
    "ChatsView",
    "ChatsViewNew",
    "CheckDemographicsView",
    "DemographicsView",
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
    "cookies_view",
    "sign_in_view",
    "sign_in_link_sent_view",
    "signed_out_view",
    "Signup1",
    "Signup2",
    "Signup3",
    "Signup4",
    "UpdateChatFeedback",
    "DeleteChat",
]
