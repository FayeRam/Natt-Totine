from django.urls import path

from . import views

app_name = "tontines"

urlpatterns = [
    path("", views.liste, name="list"),
    path("nouvelle/", views.creer, name="create"),
    path("tontine/<int:pk>/", views.detail, name="detail"),
    path("tontine/<int:pk>/lancer/", views.lancer, name="start"),
    path("tontine/<int:pk>/supprimer/", views.supprimer, name="delete"),
    path("paiement/<int:pk>/basculer/", views.basculer_paiement, name="toggle_payment"),
    path("rejoindre/<str:code>/", views.rejoindre, name="join"),
]
