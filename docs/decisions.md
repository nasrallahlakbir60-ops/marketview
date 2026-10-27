# Choix techniques

- **Devises d'une news** : table d'association `news_currencies (news_id, currency)` plutôt qu'un tableau PostgreSQL. C'est portable (les tests tournent sur SQLite) et indexable pour le filtre par paire.
- **Étiquettes de news** : en plus des devises, des étiquettes d'actifs (`XAU`, `BTC`, `CRYPTO`, `OIL`, `US_STOCKS`…) permettent de filtrer les news de l'or, de la crypto, du pétrole et des indices. Elles sont attribuées par mots-clés dans `services/news_filter.py` (sensibles à la casse pour les sigles : « Fed », « US »).
- **Choix des pays macro** : forex = les deux pays ; métaux et crypto = États-Unis (plus le pays de cotation s'il est différent) ; indices et matières premières = pays de la devise de cotation (règle demandée, y compris pour le Nikkei coté en USD).
- **Aucun appel externe pendant une visite** : les routes lisent la base (alimentée par les workers) et un cache Redis (news 60 s, macro 24 h, calendrier 1 h). Les réponses vides ne sont pas mises en cache, et les workers vident le cache concerné après chaque mise à jour.
- **Macro « 1 fois par jour »** : la tâche est vérifiée toutes les heures mais n'appelle une source que si ses données ont plus de 24 h. On obtient un appel par jour, avec un nouvel essai l'heure suivante en cas d'échec.
- **Redis facultatif** : si Redis est injoignable, un disjoncteur l'ignore pendant 30 s. L'API fonctionne alors sans cache (rate limit en mémoire), et le temps réel est indiqué « Hors ligne ».
- **Production** : l'API tourne avec gunicorn + `uvicorn-worker` (2 workers) et `RUN_SCHEDULER=false`. Un service `worker` unique exécute le scheduler, et des verrous Redis empêchent les exécutions en double.
- **Thème** : couleurs en variables CSS (`--c-*`) exposées à Tailwind (`text-fg`, `bg-panel`…), thème sombre par défaut, choix mémorisé dans `localStorage`.
