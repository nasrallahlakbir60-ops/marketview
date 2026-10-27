#!/bin/sh
# Applique les migrations et charge les paires (idempotent) avant de lancer la commande.
set -e
alembic upgrade head
python -m app.seed
exec "$@"
