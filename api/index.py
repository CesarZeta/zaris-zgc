# Entrada serverless para Vercel (@vercel/python sirve esta app ASGI).
# El código real vive en backend/app; acá solo se ajusta el path.
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.main import app  # noqa: E402, F401
