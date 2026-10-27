"""Point d'entrée Vercel : expose l'application FastAPI du dossier backend/ comme fonction Python.

vercel.json redirige /api/*, /health, /docs et /openapi.json vers ce fichier ;
le reste du site est le build statique de frontend/.
"""

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.main import app  # noqa: E402

__all__ = ["app"]
