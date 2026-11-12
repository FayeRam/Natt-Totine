"""Modèles de données : Tontine, Membre, Tour et Paiement."""
import calendar
import random
import secrets
from datetime import date, timedelta

from django.conf import settings
from django.db import models, transaction
from django.utils.formats import date_format


def fcfa(n: int) -> str:
    """10000 -> '10 000 FCFA'"""
    return f"{n:,}".replace(",", " ") + " FCFA"


def nouveau_code():
    """Code d'invitation court et difficile à deviner."""
    return secrets.token_urlsafe(6)


def ajouter_mois(d: date, n: int) -> date:
    """Ajoute n mois à une date (le 31 janvier + 1 mois donne le 28 ou 29 février)."""
    mois = d.month - 1 + n
    annee = d.year + mois // 12
    mois = mois % 12 + 1
    jour = min(d.day, calendar.monthrange(annee, mois)[1])
    return date(annee, mois, jour)


class Tontine(models.Model):
    class Frequence(models.TextChoices):
        HEBDO = "hebdo", "Chaque semaine"
        MENSUEL = "mensuel", "Chaque mois"

    nom = models.CharField("nom", max_length=80)
    montant = models.PositiveIntegerField("cotisation par personne (FCFA)")
    frequence = models.CharField(
        "fréquence", max_length=10, choices=Frequence.choices, default=Frequence.MENSUEL
    )
    nombre_places = models.PositiveSmallIntegerField("nombre de membres")
    date_debut = models.DateField("date du premier tour")
    responsable = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="tontines_gerees"
    )
    code_invitation = models.CharField(max_length=16, unique=True, default=nouveau_code)
    lancee = models.BooleanField(default=False)
    cree_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-cree_le"]

    def __str__(self):
        return self.nom

    @property
    def cagnotte(self):
        """Somme reçue par le bénéficiaire à chaque tour."""
        return self.montant * self.membres.count()

    @property
    def est_complete(self):
        return self.membres.count() >= self.nombre_places

    def tour_en_cours(self):
        """Premier tour dont tous les paiements ne sont pas encore reçus."""
        for tour in self.tours.prefetch_related("paiements"):
            if not tour.est_complet:
                return tour
        return None

    @property
    def peut_etre_supprimee(self):
        """On ne supprime qu'une tontine qui n'a pas encore commencé."""
        return not self.lancee

    def texte_suivi(self, tour, lien=""):
        """Message prêt à coller dans un groupe WhatsApp (gras avec *…*)."""
        total = self.tours.count()
        payes = [p.membre.nom_affiche for p in tour.paiements.all() if p.paye]
        attente = [p.membre.nom_affiche for p in tour.paiements.all() if not p.paye]
        lignes = [
            f"*{self.nom}* · Tour {tour.numero}/{total}",
            f"📅 Échéance : {date_format(tour.echeance, 'j F Y')}",
            f"🎁 Bénéficiaire : *{tour.beneficiaire.nom_affiche}*",
            f"💰 Cagnotte : {fcfa(self.cagnotte)} ({fcfa(self.montant)} par personne)",
            "",
            f"✅ Ont payé ({len(payes)}/{len(payes) + len(attente)})",
            *[f"  • {n}" for n in payes],
        ]
        if attente:
            lignes += ["", f"⏳ En attente ({len(attente)})", *[f"  • {n}" for n in attente]]
        else:
            lignes += ["", "🎉 Tout le monde a payé, merci !"]
        suivant = self.tours.filter(numero=tour.numero + 1).select_related("beneficiaire__utilisateur").first()
        if suivant:
            lignes += ["", f"➡️ Prochain tour : {suivant.beneficiaire.nom_affiche}, le {date_format(suivant.echeance, 'j F Y')}"]
        if lien:
            lignes += ["", f"Suivi en ligne : {lien}"]
        return "\n".join(lignes)

    @transaction.atomic
    def lancer(self, tirage_au_sort=True):
        """Fixe l'ordre de passage, crée les tours et les paiements attendus."""
        if self.lancee:
            return
        membres = list(self.membres.all())
        if tirage_au_sort:
            random.shuffle(membres)
        else:
            membres.sort(key=lambda m: m.rejoint_le)
        for position, membre in enumerate(membres, start=1):
            membre.position = position
            membre.save(update_fields=["position"])

        for numero, beneficiaire in enumerate(membres, start=1):
            if self.frequence == self.Frequence.HEBDO:
                echeance = self.date_debut + timedelta(weeks=numero - 1)
            else:
                echeance = ajouter_mois(self.date_debut, numero - 1)
            tour = Tour.objects.create(
                tontine=self, numero=numero, echeance=echeance, beneficiaire=beneficiaire
            )
            Paiement.objects.bulk_create(
                [Paiement(tour=tour, membre=m) for m in membres]
            )
        self.lancee = True
        self.save(update_fields=["lancee"])


class Membre(models.Model):
    tontine = models.ForeignKey(Tontine, on_delete=models.CASCADE, related_name="membres")
    utilisateur = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="adhesions"
    )
    position = models.PositiveSmallIntegerField("ordre de passage", null=True, blank=True)
    rejoint_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["position", "rejoint_le"]
        constraints = [
            models.UniqueConstraint(fields=["tontine", "utilisateur"], name="un_membre_par_tontine")
        ]

    def __str__(self):
        return self.nom_affiche

    @property
    def nom_affiche(self):
        u = self.utilisateur
        return u.get_full_name() or u.username


class Tour(models.Model):
    tontine = models.ForeignKey(Tontine, on_delete=models.CASCADE, related_name="tours")
    numero = models.PositiveSmallIntegerField()
    echeance = models.DateField("échéance")
    beneficiaire = models.ForeignKey(Membre, on_delete=models.CASCADE, related_name="tours_recus")

    class Meta:
        ordering = ["numero"]
        constraints = [
            models.UniqueConstraint(fields=["tontine", "numero"], name="un_numero_par_tour")
        ]

    def __str__(self):
        return f"{self.tontine} – tour {self.numero}"

    @property
    def nb_payes(self):
        return sum(1 for p in self.paiements.all() if p.paye)

    @property
    def est_complet(self):
        paiements = self.paiements.all()
        return bool(paiements) and all(p.paye for p in paiements)

    @property
    def en_retard(self):
        return not self.est_complet and self.echeance < date.today()


class Paiement(models.Model):
    tour = models.ForeignKey(Tour, on_delete=models.CASCADE, related_name="paiements")
    membre = models.ForeignKey(Membre, on_delete=models.CASCADE, related_name="paiements")
    paye = models.BooleanField("payé", default=False)
    paye_le = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["membre__position"]
        constraints = [
            models.UniqueConstraint(fields=["tour", "membre"], name="un_paiement_par_membre_et_tour")
        ]

    def __str__(self):
        etat = "payé" if self.paye else "en attente"
        return f"{self.membre} – tour {self.tour.numero} – {etat}"
