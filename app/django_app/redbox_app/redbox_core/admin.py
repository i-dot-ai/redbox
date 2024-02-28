from django.contrib import admin
from django_otp.admin import OTPAdminSite

from . import models


class OTPAdmin(OTPAdminSite):
    pass


admin_site = OTPAdmin(name="OTPAdmin")


admin.site.register(models.User)
