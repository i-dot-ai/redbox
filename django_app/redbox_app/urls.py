from django.contrib import admin
from django.urls import include, path

from .redbox_core import info_views, views

info_urlpatterns = [
    path("privacy-notice/", info_views.privacy_notice_view, name="privacy-notice"),
    path("accessibility-statement/", info_views.accessibility_statement_view, name="accessibility-statement"),
    path("support/", info_views.support_view, name="support"),
]

other_urlpatterns = [
    path("", views.homepage_view, name="homepage"),
    path("admin/", admin.site.urls),
    path("accounts/", include("allauth.urls")),
    path("documents/", views.documents_view, name="documents"),
    path("upload/", views.upload_view, name="upload"),
    path("remove-doc/<str:doc_id>", views.remove_doc_view, name="remove_doc"),
]

urlpatterns = info_urlpatterns + other_urlpatterns
