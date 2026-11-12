from datetime import date
from urllib.parse import quote

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import InscriptionForm, TontineForm
from .models import Membre, Paiement, Tontine, fcfa


def signup(request):
    if request.user.is_authenticated:
        return redirect("tontines:list")
    form = InscriptionForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, "Bienvenue ! Ton compte est créé.")
        next_url = request.GET.get("next")
        return redirect(next_url if next_url and next_url.startswith("/") else "tontines:list")
    return render(request, "registration/signup.html", {"form": form})


@login_required
def liste(request):
    tontines = (
        Tontine.objects.filter(membres__utilisateur=request.user)
        .prefetch_related("membres")
        .distinct()
    )
    return render(request, "tontines/list.html", {"tontines": tontines})


@login_required
def creer(request):
    form = TontineForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            tontine = form.save(commit=False)
            tontine.responsable = request.user
            tontine.save()
            Membre.objects.create(tontine=tontine, utilisateur=request.user)
        messages.success(request, "Tontine créée. Partage le lien d'invitation avec les membres.")
        return redirect("tontines:detail", pk=tontine.pk)
    return render(request, "tontines/create.html", {"form": form})


def _membre_ou_403(request, tontine):
    return tontine.membres.filter(utilisateur=request.user).first()


@login_required
def detail(request, pk):
    tontine = get_object_or_404(
        Tontine.objects.prefetch_related(
            "membres__utilisateur", "tours__paiements__membre__utilisateur", "tours__beneficiaire__utilisateur"
        ),
        pk=pk,
    )
    moi = _membre_ou_403(request, tontine)
    if moi is None:
        return HttpResponseForbidden("Tu ne fais pas partie de cette tontine.")
    lien = request.build_absolute_uri(f"/rejoindre/{tontine.code_invitation}/")
    lien_suivi = request.build_absolute_uri(f"/tontine/{tontine.pk}/")
    tours = list(tontine.tours.all())
    tour_actuel = next((t for t in tours if not t.est_complet), None)

    # Statistiques par membre pour l'onglet « Membres »
    aujourd_hui = date.today()
    stats = []
    for m in tontine.membres.all():
        dus = [p for t in tours if t.echeance <= aujourd_hui for p in t.paiements.all() if p.membre_id == m.id]
        payes = sum(1 for t in tours for p in t.paiements.all() if p.membre_id == m.id and p.paye)
        stats.append({
            "membre": m,
            "payes": payes,
            "retards": sum(1 for p in dus if not p.paye),
            "tour_recu": next((t for t in tours if t.beneficiaire_id == m.id), None),
        })

    texte_suivi = tontine.texte_suivi(tour_actuel, lien_suivi) if tour_actuel else (
        f"*{tontine.nom}* : les {len(tours)} tours sont terminés. Merci à tous ! 🎉"
    )
    contexte = {
        "stats": stats,
        "texte_suivi": texte_suivi,
        "whatsapp_suivi": "https://wa.me/?text=" + quote(texte_suivi),
        "whatsapp_invitation": "https://wa.me/?text=" + quote(
            f"Rejoins ma tontine « {tontine.nom} » ({fcfa(tontine.montant)} {tontine.get_frequence_display().lower()}) : {lien}"
        ),
        "tontine": tontine,
        "moi": moi,
        "est_responsable": tontine.responsable_id == request.user.id,
        "lien_invitation": lien,
        "tours": tours,
        "tour_actuel": tour_actuel,
        "tours_termines": sum(1 for t in tours if t.est_complet),
        "places_restantes": max(tontine.nombre_places - tontine.membres.count(), 0),
    }
    return render(request, "tontines/detail.html", contexte)


@login_required
@require_POST
def lancer(request, pk):
    tontine = get_object_or_404(Tontine, pk=pk)
    if tontine.responsable_id != request.user.id:
        return HttpResponseForbidden("Seul le responsable peut lancer la tontine.")
    if tontine.membres.count() < 2:
        messages.error(request, "Il faut au moins 2 membres pour lancer la tontine.")
    elif not tontine.lancee:
        tontine.lancer(tirage_au_sort=request.POST.get("ordre") != "arrivee")
        messages.success(request, "C'est parti ! L'ordre de passage est fixé.")
    return redirect("tontines:detail", pk=pk)


@login_required
def supprimer(request, pk):
    tontine = get_object_or_404(Tontine, pk=pk)
    if tontine.responsable_id != request.user.id:
        return HttpResponseForbidden("Seul le responsable peut supprimer la tontine.")
    if not tontine.peut_etre_supprimee:
        messages.error(request, "Une tontine déjà lancée ne peut pas être supprimée.")
        return redirect("tontines:detail", pk=pk)
    if request.method == "POST":
        nom = tontine.nom
        tontine.delete()
        messages.success(request, f"La tontine « {nom} » a été supprimée.")
        return redirect("tontines:list")
    return render(request, "tontines/delete.html", {"tontine": tontine})


@login_required
@require_POST
def basculer_paiement(request, pk):
    paiement = get_object_or_404(Paiement.objects.select_related("tour__tontine"), pk=pk)
    tontine = paiement.tour.tontine
    if tontine.responsable_id != request.user.id:
        return HttpResponseForbidden("Seul le responsable peut enregistrer les paiements.")
    paiement.paye = not paiement.paye
    paiement.paye_le = timezone.now() if paiement.paye else None
    paiement.save(update_fields=["paye", "paye_le"])
    ancre = "encours" if request.POST.get("retour") == "encours" else f"tour-{paiement.tour.numero}"
    return redirect(f"/tontine/{tontine.pk}/#{ancre}")


def rejoindre(request, code):
    tontine = get_object_or_404(Tontine, code_invitation=code)
    if not request.user.is_authenticated:
        return render(request, "tontines/join.html", {"tontine": tontine, "invite": True})

    deja = tontine.membres.filter(utilisateur=request.user).exists()
    if deja:
        return redirect("tontines:detail", pk=tontine.pk)

    if request.method == "POST":
        if tontine.lancee:
            messages.error(request, "Cette tontine a déjà commencé, on ne peut plus la rejoindre.")
        elif tontine.est_complete:
            messages.error(request, "Cette tontine est complète.")
        else:
            Membre.objects.create(tontine=tontine, utilisateur=request.user)
            messages.success(request, f"Tu as rejoint « {tontine.nom} ».")
            return redirect("tontines:detail", pk=tontine.pk)
        return redirect("tontines:list")
    return render(request, "tontines/join.html", {"tontine": tontine})
