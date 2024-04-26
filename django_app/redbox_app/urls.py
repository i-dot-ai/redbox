from django.contrib import admin
from django.urls import include, path

from .redbox_core import info_views, auth_views, views

info_urlpatterns = [
    path("privacy-notice/", info_views.privacy_notice_view, name="privacy-notice"),
    path(
        "accessibility-statement/",
        info_views.accessibility_statement_view,
        name="accessibility-statement",
    ),
    path("support/", info_views.support_view, name="support"),
]

auth_urlpatterns = [
    path("sign-in/", auth_views.sign_in_view, name="sign_in"),
    path("sign-in-link-sent/", auth_views.sign_in_link_sent_view, name="sign_in_link_sent"),
    path("signed-out/", auth_views.signed_out_view, name="signed_out"),
]

other_urlpatterns = [
    path("", views.homepage_view, name="homepage"),
    path("admin/", admin.site.urls),
    path("accounts/", include("allauth.urls")),
    path("documents/", views.documents_view, name="documents"),
    path("upload/", views.upload_view, name="upload"),
    path("remove-doc/<str:doc_id>", views.remove_doc_view, name="remove_doc"),
    path("sessions/<str:session_id>/", views.sessions_view, name="sessions"),
    path("sessions/", views.sessions_view, name="sessions"),
]

urlpatterns = info_urlpatterns + auth_urlpatterns + other_urlpatterns
