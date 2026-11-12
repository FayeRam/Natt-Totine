from django.contrib import admin
from django.urls import include, path

from tontines import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("compte/inscription/", views.signup, name="signup"),
    path("compte/", include("django.contrib.auth.urls")),
    path("", include("tontines.urls")),
]
