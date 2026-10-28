# MarketView

Plateforme web de suivi des marchés : on choisit une paire (forex, or, crypto, indices, matières premières) et on voit son **graphique TradingView**, les **news en temps réel** des devises concernées, l'**inflation / les taux** des pays de la paire et le **calendrier économique du jour**.

> Informations à titre indicatif, pas un conseil en investissement.

## Fonctionnalités

- **Accès réservé aux membres** : inscription par e-mail + mot de passe ou connexion directe avec Google ; page « Mon compte » (activité récente, export des données, déconnexion de tous les appareils, suppression du compte).
- 80 marchés (seed `backend/app/data/pairs_seed.json`), recherche et regroupement par catégorie.
- Graphique TradingView avec unités 1m, 5m, 15m, 1h, 4h, 1J.
- News : 16 flux RSS publics + Finnhub (si clé), filtrées par devise / actif, dédupliquées, titre + résumé court + lien vers la source (nouvel onglet), heure relative (« il y a 5 min »).
- Temps réel : nouvelles news poussées par WebSocket, animation à l'arrivée, indicateur « En direct », reconnexion automatique.
- Macro : inflation US mensuelle + taux Fed (FRED), inflation annuelle des 23 pays suivis (Banque mondiale), avec la source, la période et la date de mise à jour. Une valeur indisponible s'affiche « — ».
- Calendrier économique d'hier / du jour / de demain (Finnhub si l'offre le permet, sinon flux public ForexFactory sans clé), impact faible / moyen / fort en couleur.
- Responsive (mobile : chart, puis news, puis macro), thème clair / sombre, états de chargement, vides et d'erreur.
- Rate limit par IP (strict sur la connexion), logs structurés (JSON, identifiant de requête), journal d'activité en base, aucune clé API dans le code ni dans le navigateur.

## Architecture

```
Navigateur ──HTTP /api──►  FastAPI  ──► PostgreSQL (paires, news, macro, calendrier)
           ◄──WS /ws/news──    │    ──► Redis (cache + Pub/Sub temps réel)
                               ▲
                 Workers APScheduler : news 60 s · macro 1/jour · calendrier 1/h
                               │
           RSS · Finnhub · FRED · Banque mondiale
```

- `backend/` : FastAPI, SQLAlchemy + Alembic, providers (1 fichier par source), services (correspondance paire → devises → pays, filtre de news, dédup, cache), workers.
- `frontend/` : React + TypeScript + Vite, TailwindCSS, TanStack Query, Zustand.
- Plus de détails : [docs/plan_projet.txt](docs/plan_projet.txt), [docs/api_sources.md](docs/api_sources.md), [docs/decisions.md](docs/decisions.md).

## Installation

Prérequis : [Docker Desktop](https://www.docker.com/products/docker-desktop/) (inclut Docker Compose).

```sh
cp .env.example .env        # Windows PowerShell : Copy-Item .env.example .env
```

L'application fonctionne **sans aucune clé** : news RSS et inflation Banque mondiale. Pour tout activer, créez ces clés gratuites et collez-les dans `.env` :

| Clé | Où la créer | Variable `.env` | Ce qu'elle active |
|---|---|---|---|
| Finnhub | https://finnhub.io/register (clé dans le tableau de bord) | `FINNHUB_API_KEY` | News Finnhub + calendrier économique (le calendrier peut demander une offre payante ; sans lui, repli automatique sur ForexFactory) |
| FRED | https://fredaccount.stlouisfed.org/apikeys (compte gratuit, puis « Request API Key ») | `FRED_API_KEY` | Inflation US mensuelle, CPI sous-jacent, taux de la Fed |

Sans clé, un avertissement est logué et le panneau concerné affiche « Source non configurée ». Rien ne plante.

## Lancement (développement)

```sh
docker compose up --build
# ou : make up   (recrée aussi le volume node_modules si les dépendances ont changé)
```

- Interface : http://localhost:5173
- API : http://localhost:8000 (documentation interactive : http://localhost:8000/docs)
- Au démarrage, le backend applique les migrations (`alembic upgrade head`) et charge les paires (`python -m app.seed`, idempotent), puis le scheduler lance une première récupération des news (après environ 3 s), de la macro et du calendrier.

Commandes utiles :

```sh
make fetch-news      # récupérer les news immédiatement
make fetch-macro     # forcer la mise à jour macro
make check-feeds     # vérifier que chaque flux RSS répond
make seed            # recharger les paires (sans doublons)
docker compose down  # arrêter (les données restent dans les volumes)
```

### Lancement sans Docker (Windows)

```powershell
powershell -ExecutionPolicy Bypass -File .\start-local.ps1
```

Le script installe les dépendances si besoin, crée une base SQLite locale (`backend\marketview-local.db`), puis ouvre deux fenêtres : l'API (http://localhost:8000) et le site (http://localhost:5173). Fermez ces fenêtres pour arrêter l'application. Sans Redis, il n'y a ni cache ni temps réel (indicateur « Hors ligne ») ; le reste fonctionne.

### Routes de l'API

Toutes les routes ci-dessous, sauf `/api/auth/config`, `/register`, `/login`, `/google`, `/logout` et `/health`, exigent une session (cookie `mv_session`) ; sinon : `401 Connexion requise.`

| Méthode | Route | Description |
|---|---|---|
| POST | `/api/auth/register` | Inscription `{email, password, full_name}` (8 caractères min., une lettre, un chiffre) |
| POST | `/api/auth/login` | Connexion `{email, password}` |
| POST | `/api/auth/google` | Connexion Google `{credential}` (jeton du bouton Google, vérifié côté serveur) |
| POST | `/api/auth/logout` · `/api/auth/logout-all` | Déconnexion de cet appareil · de tous les appareils |
| GET | `/api/auth/me` · `/api/auth/me/activity` | Compte connecté · 20 derniers événements (connexions…) |
| GET | `/api/auth/me/export` | Toutes les données personnelles du compte (JSON) |
| DELETE | `/api/auth/me` | Suppression du compte et de ses sessions |
| GET | `/api/pairs` | Liste des paires actives (`?category=crypto` facultatif) |
| GET | `/api/pairs/{symbol}` | Détail : étiquettes de news et pays macro |
| GET | `/api/news?pair=EURUSD&limit=50` | News des devises de la paire, les plus récentes d'abord |
| GET | `/api/news/sources` | État des sources de news (clé manquante, accès refusé…) |
| GET | `/api/macro?pair=EURUSD` | Inflation / taux des pays de la paire + état des sources |
| GET | `/api/calendar?pair=EURUSD&day=today` | Événements du jour (`today`, `tomorrow`, `yesterday` ou `AAAA-MM-JJ`, journée UTC) |
| WS | `/ws/news/{symbol}` | News en direct : `{"type":"news","data":{...}}` |
| GET | `/health` | Contrôle de santé |

## Comptes utilisateurs

- **Sessions** : jeton aléatoire dans un cookie `httpOnly` + `SameSite=Lax` (+ `Secure` en HTTPS), valable `SESSION_DAYS` jours. La base ne stocke que son hash SHA-256 : une fuite de la table ne permet pas de se connecter. Une déconnexion supprime la session côté serveur.
- **Mots de passe** : hachés avec Argon2id (jamais stockés ni logués en clair). Message identique pour un e-mail inconnu ou un mauvais mot de passe. `AUTH_RATE_LIMIT_PER_MINUTE` tentatives par minute et par IP.
- **Google** : le bouton officiel (Google Identity Services) renvoie un jeton signé par Google ; le backend vérifie la signature, l'audience (`GOOGLE_CLIENT_ID`), l'émetteur, l'expiration et que l'e-mail est vérifié. Si l'adresse correspond à un compte e-mail existant, les deux sont reliés.
- **Activer Google** : [console.cloud.google.com](https://console.cloud.google.com) > *API et services* > *Écran de consentement OAuth* (type Externe), puis *Identifiants* > *Créer des identifiants* > *ID client OAuth* > *Application Web*. Dans *Origines JavaScript autorisées*, ajoutez `http://localhost:5173` et l'URL du site (ex. `https://votre-projet.vercel.app`). Copiez l'ID client dans `GOOGLE_CLIENT_ID` (aucun secret client n'est nécessaire).
- **Données** : tables `users`, `user_sessions` et `audit_logs` (migration `0002_auth`). Le journal d'activité (inscription, connexion, échec de connexion, déconnexion, export, suppression) garde l'IP, le navigateur et l'identifiant de requête. Les sessions expirées et les journaux de plus de `AUDIT_RETENTION_DAYS` jours sont purgés automatiquement (scheduler toutes les 6 h, ou `/api/cron/refresh`). À la suppression d'un compte, ses journaux sont conservés mais détachés du compte.

## Logs

- Une ligne par requête API (`app.access`) : méthode, chemin, statut, durée, utilisateur, IP. Chaque réponse porte un en-tête `X-Request-ID`, repris dans tous les logs de la requête et dans le journal d'activité : on retrouve ainsi tout ce qui s'est passé pour une erreur signalée.
- `LOG_FORMAT=json` (défaut sur Vercel et en production Docker) : une ligne JSON par log, directement exploitable par les outils de collecte (Vercel *Logs* / *Log Drains*, Datadog, Grafana Loki, Better Stack…).
- Production Docker : logs sur la sortie standard, conservés par Docker avec rotation (10 Mo x 5 fichiers par service), lisibles avec `make prod-logs`.
- `LOG_FILE` : fichier avec rotation (10 Mo x 5) pour un lancement sans Docker, avec un seul processus (plusieurs workers gunicorn ne doivent pas partager le même fichier).

## Tests

Aucun test n'appelle le réseau : les réponses externes sont simulées (`httpx.MockTransport`), la base est SQLite en mémoire et Redis est remplacé par fakeredis.

```sh
make test            # backend + frontend
make test-backend    # pytest (routes, providers, workers, WebSocket, migrations)
make test-frontend   # Vitest + React Testing Library
```

Sans Docker :

```sh
cd backend && python -m venv .venv && .venv/bin/pip install -r requirements-dev.txt && .venv/bin/pytest
cd frontend && npm ci && npm test
```

(Sous Windows, remplacez `.venv/bin/` par `.venv\Scripts\`.)

## Déploiement sur Vercel (un seul projet : site + API)

`vercel.json` (à la racine) relie les deux dossiers sur **une seule URL** :

- `frontend/` est construit et servi en statique (`/`, `/market/...`) ;
- `/api/*`, `/health` et `/docs` sont relayés vers `api/index.py`, qui charge l'application FastAPI de `backend/`. Même domaine pour le navigateur : aucune configuration CORS nécessaire.

Limites de Vercel : pas de WebSocket (les news sont rechargées automatiquement toutes les 60 s, indicateur « Auto 60 s »), et pas de processus permanent. Le scheduler est remplacé par `GET /api/cron/refresh`.

1. **Projet Vercel** : *Settings > General > Root Directory* **vide** (racine du dépôt), *Framework Preset* : **Other**. Les commandes de build viennent de `vercel.json`.
2. **Base PostgreSQL** : *Storage* (ou *Marketplace*) > **Neon** > *Connect* au projet. La variable `DATABASE_URL` est créée automatiquement.
3. **Redis (facultatif, recommandé pour le cache)** : *Marketplace* > **Upstash Redis** > *Connect*. `REDIS_URL` ou `KV_URL` est reconnue automatiquement.
4. **Variables d'environnement** (*Settings > Environment Variables*) :
   - `CRON_SECRET` : longue valeur aléatoire (ex. résultat de `python -c "import secrets; print(secrets.token_urlsafe(32))"`) ;
   - `GOOGLE_CLIENT_ID` pour la connexion Google (voir *Comptes utilisateurs*), en ajoutant l'URL Vercel aux origines autorisées ;
   - `FINNHUB_API_KEY`, `FRED_API_KEY` (facultatives).
   - Sans base Neon, les comptes sont stockés dans une base temporaire **effacée au redémarrage de l'instance** : connectez Neon avant d'ouvrir les inscriptions.
5. **Redéployer** (*Deployments > ... > Redeploy*). Au premier démarrage, l'API crée les tables et charge les 80 paires.
6. **Remplir les données** : *Settings > Cron Jobs > /api/cron/refresh > Run*. Ensuite, Vercel l'exécute une fois par jour (limite du plan gratuit).
7. **Mises à jour plus fréquentes** : dans GitHub, *Settings > Secrets and variables > Actions*, ajoutez `MARKETVIEW_URL` (l'URL Vercel) et `CRON_SECRET` (même valeur). Le workflow `.github/workflows/refresh.yml` appelle alors l'API toutes les 30 min. Autre option : [cron-job.org](https://cron-job.org) (gratuit, chaque minute possible), avec l'en-tête `Authorization: Bearer <CRON_SECRET>`.

## Déploiement (production, serveur Docker)

La configuration de production sert le frontend statique avec Nginx, qui relaie `/api` et `/ws` vers le backend (gunicorn + uvicorn). PostgreSQL et Redis ne sont pas exposés, et un service `worker` exécute les tâches planifiées.

Sur un VPS (Hetzner, OVH, Contabo…) avec Docker installé :

```sh
git clone <votre-dépôt> marketview && cd marketview
cp .env.example .env
# Dans .env : POSTGRES_PASSWORD fort, DATABASE_URL avec ce mot de passe, clés API, CORS_ORIGINS=https://votre-domaine
docker compose -f docker-compose.prod.yml --env-file .env up -d --build    # ou : make prod-up
```

**HTTPS (obligatoire)** : placez un reverse proxy TLS devant le port 80. Le plus simple est [Caddy](https://caddyserver.com/docs/quick-starts/reverse-proxy) (`caddy reverse-proxy --from votre-domaine.com --to localhost:80`, certificat Let's Encrypt automatique). Vous pouvez aussi utiliser Nginx + Certbot sur l'hôte. Pointez d'abord l'enregistrement DNS A du domaine vers l'IP du serveur.

Option hébergée : frontend sur Vercel / Netlify (build avec `VITE_API_URL=https://api.votre-domaine` et `VITE_WS_URL=wss://api.votre-domaine`), backend + worker sur Render / Railway / Fly.io avec `backend/Dockerfile.prod`, PostgreSQL managé (Neon, Supabase…) et Redis managé (Upstash). Ajoutez alors le domaine du frontend dans `CORS_ORIGINS`. Le cookie de session (`SameSite=Lax`) n'est envoyé qu'entre sous-domaines d'un même domaine (`app.votre-domaine` et `api.votre-domaine`), pas entre `*.vercel.app` et `*.onrender.com`.

Surveillance : `make prod-logs`, et la route `/health` pour un service de supervision (UptimeRobot…).

## Sécurité et aspects juridiques

- `.env` est ignoré par git ; les clés ne sont lues que par le backend.
- Données personnelles (RGPD) : chaque utilisateur peut exporter ses données et supprimer son compte depuis « Mon compte ». Mentionnez dans vos mentions légales / politique de confidentialité les données collectées (e-mail, nom, IP et navigateur des connexions) et leur durée de conservation (`AUDIT_RETENTION_DAYS`).
- Chaque news affiche sa source et renvoie vers l'article d'origine (titre + résumé court uniquement).
- Lisez les conditions d'utilisation de chaque source avant une mise en ligne publique ou commerciale (voir [docs/api_sources.md](docs/api_sources.md)).
# marketview
