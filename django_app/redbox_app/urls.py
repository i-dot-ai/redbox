from adminplus.sites import AdminSitePlus
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from magic_link import urls as magic_link_urls

from .redbox_core import views

admin.site = AdminSitePlus()
admin.autodiscover()

auth_urlpatterns = [
    path("magic_link/", include(magic_link_urls)),
    path("sign-in/", views.sign_in_view, name="sign-in"),
    path(
        "sign-in-link-sent/",
        views.sign_in_link_sent_view,
        name="sign-in-link-sent",
    ),
    path("signed-out/", views.signed_out_view, name="signed-out"),
    path("sign-up-page-1", views.Signup1.as_view(), name="sign-up-page-1"),
    path("sign-up-page-2", views.Signup2.as_view(), name="sign-up-page-2"),
    path("sign-up-page-3", views.Signup3.as_view(), name="sign-up-page-3"),
    path("sign-up-page-4", views.Signup4.as_view(), name="sign-up-page-4"),
    path("sign-up-page-5", views.Signup5.as_view(), name="sign-up-page-5"),
    path("sign-up-page-6", views.Signup6.as_view(), name="sign-up-page-6"),
    path("sign-up-page-7", views.Signup7.as_view(), name="sign-up-page-7"),
]

info_urlpatterns = [
    path("privacy-notice/", views.info_views.privacy_notice_view, name="privacy-notice"),
    path(
        "accessibility-statement/",
        views.accessibility_statement_view,
        name="accessibility-statement",
    ),
    path("support/", views.support_view, name="support"),
]

file_urlpatterns = [
    path("documents/", views.DocumentView.as_view(), name="documents"),
    path("upload/", views.UploadView.as_view(), name="upload"),
    path("remove-doc/<uuid:doc_id>", views.remove_doc_view, name="remove-doc"),
]

chat_urlpatterns = [
    path("chats/<uuid:chat_id>/", views.ChatsView.as_view(), name="chats"),
    path("chats/", views.ChatsView.as_view(), name="chats"),
    path("chat/<uuid:chat_id>/title/", views.ChatsTitleView.as_view(), name="chat-titles"),
    path("citations/<uuid:message_id>/", views.CitationsView.as_view(), name="citations"),
    path("ratings/<uuid:message_id>/", views.RatingsView.as_view(), name="ratings"),
    path("chats/<uuid:chat_id>/update-chat-feedback", views.UpdateChatFeedback.as_view(), name="chat-feedback"),
    path("chats/<uuid:chat_id>/delete-chat", views.DeleteChat.as_view(), name="chat-delete"),
]

admin_urlpatterns = [
    path("admin/report/", include("django_plotly_dash.urls")),
    path("admin/", admin.site.urls),
]

other_urlpatterns = [
    path("", views.homepage_view, name="homepage"),
    path("health/", views.health, name="health"),
    path("file-status/", views.file_status_api_view, name="file-status"),
    path(
        "check-demographics/", views.CheckDemographicsView.as_view(), name="check-demographics"
    ),  # Can be removed once profile overlay is enabled
    path("demographics/", views.DemographicsView.as_view(), name="demographics"),
    path("update-demographics", views.UpdateDemographicsView.as_view(), name="update-demographics"),
    path(".well-known/security.txt", views.SecurityTxtRedirectView.as_view(), name="security.txt"),
    path("security", views.SecurityTxtRedirectView.as_view(), name="security"),
    path("sitemap", views.misc_views.sitemap_view, name="sitemap"),
]

urlpatterns = (
    info_urlpatterns + other_urlpatterns + auth_urlpatterns + chat_urlpatterns + file_urlpatterns + admin_urlpatterns
)

if settings.DEBUG:
    urlpatterns = urlpatterns + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
