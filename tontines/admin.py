from django.contrib import admin

from .models import Membre, Paiement, Tontine, Tour


class MembreInline(admin.TabularInline):
    model = Membre
    extra = 0


@admin.register(Tontine)
class TontineAdmin(admin.ModelAdmin):
    list_display = ("nom", "montant", "frequence", "nombre_places", "responsable", "lancee")
    inlines = [MembreInline]


@admin.register(Tour)
class TourAdmin(admin.ModelAdmin):
    list_display = ("tontine", "numero", "echeance", "beneficiaire")
    list_filter = ("tontine",)


@admin.register(Paiement)
class PaiementAdmin(admin.ModelAdmin):
    list_display = ("tour", "membre", "paye", "paye_le")
    list_filter = ("paye", "tour__tontine")
