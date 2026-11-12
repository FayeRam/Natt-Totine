# Natt – tontine claire

Application web (Python / Django) pour gérer une tontine en toute transparence :
le responsable crée la tontine, invite les membres par WhatsApp, l'ordre de passage
est tiré au sort, et chaque membre voit qui a payé à chaque tour.

## Installation sur Windows

1. Installe Python 3.12 ou plus récent depuis https://www.python.org/downloads/
   (coche bien « Add python.exe to PATH » pendant l'installation).
2. Ouvre PowerShell dans ce dossier, puis :

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py makemigrations tontines
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

3. Ouvre http://127.0.0.1:8000 dans ton navigateur.

Si PowerShell refuse d'activer l'environnement (« l'exécution de scripts est désactivée »),
lance une fois : `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

## Commandes utiles

| Commande | À quoi elle sert |
|---|---|
| `python manage.py runserver` | Lance le site en local |
| `python manage.py test` | Lance les tests automatiques |
| `python manage.py makemigrations` puis `migrate` | Après une modification de `models.py` |
| http://127.0.0.1:8000/admin | Interface d'administration (compte superuser) |

## Organisation du code

- `tontines/models.py` : les données (Tontine, Membre, Tour, Paiement)
- `tontines/views.py` : ce qui se passe quand on ouvre une page ou clique sur un bouton
- `tontines/urls.py` : les adresses des pages
- `templates/` : le HTML des pages
- `static/style.css` : le style
