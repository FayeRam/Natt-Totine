"""
Pages et fichiers nécessaires pour publier Natt comme application :
- manifeste et service worker (application installable / PWA) ;
- assetlinks.json (lien entre le site et l'application Android du Play Store) ;
- politique de confidentialité et suppression du compte (exigées par Google Play).
"""
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.templatetags.static import static
from django.views.decorators.cache import cache_control

from .models import Tontine


@cache_control(max_age=3600)
def manifeste(request):
    donnees = {
        "name": f"{settings.APP_NAME} – {settings.APP_SLOGAN}",
        "short_name": settings.APP_NAME,
        "description": "Gère ta tontine en toute transparence : invitations WhatsApp, "
                       "ordre de passage, suivi des cotisations.",
        "lang": "fr",
        "start_url": "/?source=app",
        "scope": "/",
        "display": "standalone",
        "orientation": "portrait",
        "background_color": "#F1F2EC",
        "theme_color": "#14213D",
        "categories": ["finance", "lifestyle"],
        "icons": [
            {"src": static("icons/icone-192.png"), "sizes": "192x192", "type": "image/png"},
            {"src": static("icons/icone-512.png"), "sizes": "512x512", "type": "image/png"},
            {"src": static("icons/icone-maskable-512.png"), "sizes": "512x512",
             "type": "image/png", "purpose": "maskable"},
        ],
    }
    return JsonResponse(donnees, content_type="application/manifest+json",
                        json_dumps_params={"ensure_ascii": False})


@cache_control(no_cache=True)
def service_worker(request):
    reponse = render(request, "sw.js", content_type="application/javascript")
    reponse["Service-Worker-Allowed"] = "/"
    return reponse


def assetlinks(request):
    """Contenu fourni par PWABuilder, à coller dans config/assetlinks.json."""
    fichier = settings.BASE_DIR / "config" / "assetlinks.json"
    contenu = fichier.read_text(encoding="utf-8") if fichier.exists() else "[]"
    return HttpResponse(contenu, content_type="application/json")


def hors_ligne(request):
    return render(request, "hors_ligne.html")


def confidentialite(request):
    return render(request, "confidentialite.html", {
        "contact": getattr(settings, "CONTACT_EMAIL", ""),
    })


@login_required
def supprimer_compte(request):
    """Supprime les données personnelles du compte.

    Pour ne pas casser l'historique des tontines des autres membres, on ne supprime pas
    la ligne de l'utilisateur : on l'anonymise (nom effacé, connexion impossible).
    Les tontines qu'il gère et qui n'ont pas commencé sont supprimées."""
    user = request.user
    a_supprimer = Tontine.objects.filter(responsable=user, lancee=False)
    en_cours = Tontine.objects.filter(membres__utilisateur=user, lancee=True).distinct()

    if request.method == "POST":
        with transaction.atomic():
            a_supprimer.delete()
            user.adhesions.filter(tontine__lancee=False).delete()
            user.username = f"supprime-{user.pk}"
            user.first_name = "Membre supprimé"
            user.last_name = ""
            user.email = ""
            user.set_unusable_password()
            user.is_active = False
            user.save()
        logout(request)
        messages.success(request, "Ton compte et tes données personnelles ont été supprimés.")
        return redirect("login")

    return render(request, "registration/supprimer_compte.html", {
        "a_supprimer": a_supprimer,
        "en_cours": en_cours,
    })
