from django.conf import settings


def marque(request):
    """Rend le nom de l'application disponible dans tous les templates."""
    return {"APP_NAME": settings.APP_NAME, "APP_SLOGAN": settings.APP_SLOGAN}
