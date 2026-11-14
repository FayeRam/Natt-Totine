{% load static %}// Service worker de {{ APP_NAME }} : rend l'application installable et affiche
// une page « hors ligne » quand il n'y a pas de connexion.
const CACHE = "natt-v1";
const PAGE_HORS_LIGNE = "{% url 'hors_ligne' %}";
const A_GARDER = [
  PAGE_HORS_LIGNE,
  "{% static 'style.css' %}",
  "{% static 'icons/icone-192.png' %}",
  "{% static 'icons/icone-512.png' %}",
];

self.addEventListener("install", (evenement) => {
  evenement.waitUntil(caches.open(CACHE).then((cache) => cache.addAll(A_GARDER)));
  self.skipWaiting();
});

self.addEventListener("activate", (evenement) => {
  evenement.waitUntil(
    caches.keys().then((noms) =>
      Promise.all(noms.filter((nom) => nom !== CACHE).map((nom) => caches.delete(nom)))
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (evenement) => {
  const requete = evenement.request;
  if (requete.method !== "GET") return;          // formulaires : toujours en ligne

  // Pages : toujours la version à jour ; sans réseau, la page « hors ligne »
  if (requete.mode === "navigate") {
    evenement.respondWith(fetch(requete).catch(() => caches.match(PAGE_HORS_LIGNE)));
    return;
  }

  // Style et icônes : depuis le cache s'ils y sont (plus rapide)
  if (new URL(requete.url).pathname.startsWith("{% static '' %}")) {
    evenement.respondWith(caches.match(requete).then((r) => r || fetch(requete)));
  }
});
