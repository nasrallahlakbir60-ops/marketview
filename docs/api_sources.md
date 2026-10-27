# Sources de données externes

Toutes les sources sont appelées **uniquement par le backend** (workers planifiés). Le navigateur ne contacte jamais une API externe, à l'exception du widget TradingView intégré (chart).
Les quotas et les offres gratuites changent souvent : **vérifiez-les sur le site de chaque fournisseur** avant la mise en ligne, ainsi que leurs conditions d'utilisation (affichage public / commercial).

| Source | Utilisation dans MarketView | Inscription | Variable `.env` | Clé obligatoire ? | Fréquence d'appel | Quota à vérifier |
|---|---|---|---|---|---|---|
| Flux RSS publics | News (sites forex, banques centrales, crypto, pétrole) | aucune | — | non | toutes les 60 s (1 requête par flux) | Conditions d'utilisation de chaque site |
| Finnhub (news) | News forex, général, crypto | https://finnhub.io/register | `FINNHUB_API_KEY` | non (source ignorée sans clé) | toutes les 60 s (3 requêtes) | Limite par minute de l'offre gratuite |
| Finnhub (calendrier économique) | Calendrier du jour (impact, prévision, précédent, réel) | https://finnhub.io/register | `FINNHUB_API_KEY` | oui pour le calendrier | toutes les heures (1 requête) | **Peut être réservé aux offres payantes** : en cas de refus (401/403), le panneau affiche « Accès refusé par Finnhub » |
| FRED (Fed de St. Louis) | Inflation US mensuelle (CPI, CPI sous-jacent), taux directeur Fed | https://fredaccount.stlouisfed.org/apikeys | `FRED_API_KEY` | non (repli sur la Banque mondiale pour l'inflation US) | 1 fois par jour (≈ 6 requêtes) | Limite de requêtes par minute |
| Banque mondiale | Inflation annuelle (IPC) des 23 pays suivis, zone euro comprise | aucune | — | non | 1 fois par jour (1 requête) | Pas de clé ; API parfois lente (délai 30 s + 1 nouvel essai) |
| TradingView (widget) | Graphique de prix (chargé par le navigateur) | aucune | — | non | — | Conditions d'utilisation des widgets |

## Détail des séries

- **FRED**
  - `CPIAUCSL` : indice des prix à la consommation, mensuel → MarketView calcule la variation sur 12 mois (%).
  - `CPILFESL` : CPI hors alimentation et énergie → variation sur 12 mois (%).
  - `DFEDTARU` : borne haute de la cible des Fed funds (quotidien) ; « précédent » = niveau avant le dernier changement.
  - Date « Mis à jour » = champ `last_updated` de la série.
- **Banque mondiale** : indicateur `FP.CPI.TOTL.ZG` (inflation, prix à la consommation, % annuel). Données **annuelles**, publiées avec retard : l'année affichée est celle de la dernière valeur disponible (ex. 2024 ou 2025). La zone euro correspond à l'agrégat `EMU`.
- **Prévisions** : ni FRED ni la Banque mondiale ne fournissent de prévision ; le champ affiche « — ». Les prévisions apparaissent dans le calendrier économique (Finnhub) quand elles existent.

## Flux RSS

Liste dans `backend/app/data/rss_feeds.json` (vérifiés le 27/10/2026, tous répondent) : FXStreet, investingLive (ex-ForexLive), Investing.com Forex, CNBC Economy, BIS (discours de banquiers centraux), Federal Reserve, BCE, Bank of England, Bank of Japan, Bank of Canada, Banque nationale suisse, RBNZ, Riksbank, CoinDesk, Cointelegraph, OilPrice.com.

Retirés car injoignables : Reserve Bank of Australia (403), Norges Bank (404), FMI (403), Kitco (404).

Vérifier les flux à tout moment :

```sh
docker compose exec backend python scripts/check_feeds.py
```

MarketView n'affiche que le **titre, un résumé court (280 caractères max) et le lien** vers l'article d'origine, avec le nom de la source. Aucun scraping (ni Facebook ni autre site).

## Clés prévues pour la V2 (non utilisées par le MVP)

`NEWSAPI_KEY` (https://newsapi.org), `MARKETAUX_KEY` (https://www.marketaux.com), `TRADINGECONOMICS_KEY` (https://tradingeconomics.com/api), `TWELVEDATA_KEY` (https://twelvedata.com).
