from datetime import date

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import Tontine


class InscriptionForm(UserCreationForm):
    first_name = forms.CharField(label="Prénom et nom", max_length=150)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "first_name")
        labels = {"username": "Nom d'utilisateur (ou numéro de téléphone)"}


class TontineForm(forms.ModelForm):
    class Meta:
        model = Tontine
        fields = ("nom", "montant", "frequence", "nombre_places", "date_debut")
        widgets = {"date_debut": forms.DateInput(attrs={"type": "date"})}
        help_texts = {
            "montant": "Ce que chaque membre verse à chaque tour.",
            "nombre_places": "Toi compris. Il y aura autant de tours que de membres.",
        }

    def clean_nombre_places(self):
        n = self.cleaned_data["nombre_places"]
        if not 2 <= n <= 50:
            raise forms.ValidationError("Choisis entre 2 et 50 membres.")
        return n

    def clean_montant(self):
        m = self.cleaned_data["montant"]
        if m < 100:
            raise forms.ValidationError("La cotisation doit être d'au moins 100 FCFA.")
        return m

    def clean_date_debut(self):
        d = self.cleaned_data["date_debut"]
        if d < date.today():
            raise forms.ValidationError("La date du premier tour ne peut pas être passée.")
        return d
