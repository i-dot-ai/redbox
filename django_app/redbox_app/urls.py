from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from magic_link import urls as magic_link_urls

from .redbox_core import auth_views, info_views, views

auth_urlpatterns = [
    path("magic_link/", include(magic_link_urls)),
    path("sign-in/", auth_views.sign_in_view, name="sign-in"),
    path(
        "sign-in-link-sent/",
        auth_views.sign_in_link_sent_view,
        name="sign-in-link-sent",
    ),
    path("signed-out/", auth_views.signed_out_view, name="signed-out"),
]

info_urlpatterns = [
    path("privacy-notice/", info_views.privacy_notice_view, name="privacy-notice"),
    path(
        "accessibility-statement/",
        info_views.accessibility_statement_view,
        name="accessibility-statement",
    ),
    path("support/", info_views.support_view, name="support"),
]

file_urlpatterns = [
    path("documents/", views.documents_view, name="documents"),
    path("upload/", views.upload_view, name="upload"),
    path("remove-doc/<uuid:doc_id>", views.remove_doc_view, name="remove-doc"),
]

chat_urlpatterns = [
    path("sessions/<uuid:session_id>/", views.sessions_view, name="sessions"),
    path("sessions/", views.sessions_view, name="sessions"),
    path("post-message/", views.post_message, name="post-message"),
]

admin_urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("allauth.urls")),
]

other_urlpatterns = [
    path("", views.homepage_view, name="homepage"),
    path("health/", views.health, name="health"),
    path("file-status/<uuid:file_id>", views.file_status_api_view, name="file-status"),
]

urlpatterns = (
    info_urlpatterns + other_urlpatterns + auth_urlpatterns + chat_urlpatterns + file_urlpatterns + admin_urlpatterns
)

if settings.DEBUG:
    urlpatterns = urlpatterns + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
