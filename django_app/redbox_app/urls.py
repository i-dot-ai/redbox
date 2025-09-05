from adminplus.sites import AdminSitePlus
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic.base import RedirectView
from rest_framework import routers

from redbox_app.redbox_core import views
from redbox_app.redbox_core.views import api_views
from redbox_app.redbox_core.views.api_views import ChatViewSet, rate_chat_message

admin.site = AdminSitePlus()
admin.autodiscover()

auth_urlpatterns = [
    path("accounts/", include("allauth.urls")),
    path("log-in/", RedirectView.as_view(url="/accounts/oidc/gds/login/?process=login"), name="log-in"),
    path("sign-in/", RedirectView.as_view(url="/log-in/")),
    path("logged-out/", views.signed_out_view, name="logged-out"),
    path("sign-up-page-1", views.Signup1.as_view(), name="sign-up-page-1"),
    path("sign-up-page-2", views.Signup2.as_view(), name="sign-up-page-2"),
    path("sign-up-page-3", views.Signup3.as_view(), name="sign-up-page-3"),
    path("sign-up-page-4", views.Signup4.as_view(), name="sign-up-page-4"),
]

info_urlpatterns = [
    path("privacy-notice/", views.info_views.privacy_notice_view, name="privacy-notice"),
    path("cookies/", views.cookies_view, name="cookies"),
    path(
        "accessibility-statement/",
        views.accessibility_statement_view,
        name="accessibility-statement",
    ),
    path("support/", views.support_view, name="support"),
    path("faqs/", views.faqs_view, name="faqs"),
]

router = routers.DefaultRouter()
router.register(r"chat", ChatViewSet, basename="chat")

chat_urlpatterns = [
    path("chats/", views.ChatsViewNew.as_view(), name="chats"),
    path("chats/<uuid:chat_id>/", views.ChatsView.as_view(), name="chats"),
    path("chats/<uuid:chat_id>/upload", views.UploadView.as_view(), name="upload"),
    path("chats/<uuid:chat_id>/remove-doc/<uuid:doc_id>", views.remove_doc_view, name="remove-doc"),
    path("ratings/<uuid:message_id>/", rate_chat_message, name="ratings"),
    path("chats/<uuid:chat_id>/message", views.ChatMessageView.as_view(), name="chat-message"),
]

admin_urlpatterns = [
    path("admin/", admin.site.urls),
]

training_urlpatterns = [
    path("training/", views.training_welcome_view, name="training"),
    path("training/welcome", views.training_welcome_view, name="training-welcome"),
    path("training/chat", views.training_chat_view, name="training-chat"),
    path("training/documents", views.training_documents_view, name="training-documents"),
    path("training/models", views.training_models_view, name="training-models"),
]

other_urlpatterns = [
    path("", views.homepage_view, name="homepage"),
    path("health/", views.health, name="health"),
    path("file-status/", views.file_status_api_view, name="file-status"),
    path("check-demographics/", views.CheckDemographicsView.as_view(), name="check-demographics"),
    path("demographics/", views.DemographicsView.as_view(), name="demographics"),
    path("update-demographics", views.UpdateDemographicsView.as_view(), name="update-demographics"),
    path(".well-known/security.txt", views.SecurityTxtRedirectView.as_view(), name="security.txt"),
    path("security", views.SecurityTxtRedirectView.as_view(), name="security"),
    path("sitemap", views.misc_views.sitemap_view, name="sitemap"),
    path("download-metrics/", views.download_metrics, name="download-metrics"),
    path("download-metrics/<str:file_name>", views.download_metrics, name="download-named-metrics"),
]


api_url_patterns = [
    path("api/v0/file/", api_views.file_upload, name="file-upload"),
    path("api/v0/", include(router.urls), name="chat"),
]

urlpatterns = (
    info_urlpatterns
    + other_urlpatterns
    + auth_urlpatterns
    + chat_urlpatterns
    + admin_urlpatterns
    + api_url_patterns
    + training_urlpatterns
)

if settings.DEBUG:
    urlpatterns = urlpatterns + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
