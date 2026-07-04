# Backend ZGC — imagen para cualquier host de contenedores (Oracle VM,
# Railway, Cloud Run). Config por variables de entorno (ver app/core/config.py):
# DATABASE_URL, JWT_SECRET, CORS_ORIGINS, ENV.
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

ENV PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
