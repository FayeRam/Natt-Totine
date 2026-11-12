"""Tests automatiques. Lance-les avec : python manage.py test"""
from datetime import date, timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Membre, Paiement, Tontine, ajouter_mois


class AjouterMoisTests(TestCase):
    def test_fin_de_mois(self):
        self.assertEqual(ajouter_mois(date(2027, 1, 31), 1), date(2027, 2, 28))

    def test_changement_annee(self):
        self.assertEqual(ajouter_mois(date(2026, 11, 15), 3), date(2027, 2, 15))


class TontineTests(TestCase):
    def setUp(self):
        self.awa = User.objects.create_user("awa", password="motdepasse-solide-1")
        self.moussa = User.objects.create_user("moussa", password="motdepasse-solide-1")
        self.fatou = User.objects.create_user("fatou", password="motdepasse-solide-1")
        self.tontine = Tontine.objects.create(
            nom="Natt du quartier", montant=10000, nombre_places=3,
            date_debut=date.today() + timedelta(days=7), responsable=self.awa,
        )
        for u in (self.awa, self.moussa, self.fatou):
            Membre.objects.create(tontine=self.tontine, utilisateur=u)

    def test_lancer_cree_un_tour_par_membre(self):
        self.tontine.lancer()
        self.assertEqual(self.tontine.tours.count(), 3)
        self.assertEqual(Paiement.objects.filter(tour__tontine=self.tontine).count(), 9)
        positions = sorted(self.tontine.membres.values_list("position", flat=True))
        self.assertEqual(positions, [1, 2, 3])

    def test_cagnotte(self):
        self.assertEqual(self.tontine.cagnotte, 30000)

    def test_seul_le_responsable_enregistre_un_paiement(self):
        self.tontine.lancer()
        paiement = Paiement.objects.filter(tour__tontine=self.tontine).first()
        self.client.login(username="moussa", password="motdepasse-solide-1")
        r = self.client.post(reverse("tontines:toggle_payment", args=[paiement.pk]))
        self.assertEqual(r.status_code, 403)
        self.client.login(username="awa", password="motdepasse-solide-1")
        self.client.post(reverse("tontines:toggle_payment", args=[paiement.pk]))
        paiement.refresh_from_db()
        self.assertTrue(paiement.paye)

    def test_supprimer_avant_lancement(self):
        self.client.login(username="awa", password="motdepasse-solide-1")
        self.client.post(reverse("tontines:delete", args=[self.tontine.pk]))
        self.assertFalse(Tontine.objects.filter(pk=self.tontine.pk).exists())

    def test_impossible_de_supprimer_une_tontine_lancee(self):
        self.tontine.lancer()
        self.client.login(username="awa", password="motdepasse-solide-1")
        self.client.post(reverse("tontines:delete", args=[self.tontine.pk]))
        self.assertTrue(Tontine.objects.filter(pk=self.tontine.pk).exists())

    def test_un_membre_ne_peut_pas_supprimer(self):
        self.client.login(username="moussa", password="motdepasse-solide-1")
        r = self.client.post(reverse("tontines:delete", args=[self.tontine.pk]))
        self.assertEqual(r.status_code, 403)

    def test_texte_suivi_whatsapp(self):
        self.tontine.lancer()
        tour = self.tontine.tours.first()
        p = tour.paiements.first()
        p.paye = True
        p.save()
        texte = self.tontine.texte_suivi(tour)
        self.assertIn("Tour 1/3", texte)
        self.assertIn("30 000 FCFA", texte)
        self.assertIn("Ont payé (1/3)", texte)
        self.assertIn("En attente (2)", texte)

    def test_page_detail_s_affiche(self):
        self.tontine.lancer()
        self.client.login(username="awa", password="motdepasse-solide-1")
        r = self.client.get(reverse("tontines:detail", args=[self.tontine.pk]))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Suivi WhatsApp")

    def test_un_inconnu_ne_voit_pas_la_tontine(self):
        User.objects.create_user("inconnu", password="motdepasse-solide-1")
        self.client.login(username="inconnu", password="motdepasse-solide-1")
        r = self.client.get(reverse("tontines:detail", args=[self.tontine.pk]))
        self.assertEqual(r.status_code, 403)
