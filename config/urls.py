from django.contrib import admin
from django.urls import include, path

from tontines import app_views, views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("compte/inscription/", views.signup, name="signup"),
    path("compte/supprimer/", app_views.supprimer_compte, name="supprimer_compte"),
    path("manifest.webmanifest", app_views.manifeste, name="manifeste"),
    path("sw.js", app_views.service_worker, name="service_worker"),
    path(".well-known/assetlinks.json", app_views.assetlinks, name="assetlinks"),
    path("hors-ligne/", app_views.hors_ligne, name="hors_ligne"),
    path("confidentialite/", app_views.confidentialite, name="confidentialite"),
    path("compte/", include("django.contrib.auth.urls")),
    path("", include("tontines.urls")),
]
