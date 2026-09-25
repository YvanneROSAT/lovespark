FROM python:3.12-slim
WORKDIR /app
# On copie uniquement les fichiers utiles, jamais "COPY . ." : Coolify reecrit
# le Dockerfile avec les variables build-time en clair, il ne doit jamais
# se retrouver dans l'image.
COPY server.py ai_providers.py index.html favicon.svg ./
# Donnees visiteurs hors de /app, dans un volume persistant.
ENV DATA_DIR=/data PORT=3000
RUN useradd --system --uid 10001 app && mkdir -p /data && chown app /data
USER app
EXPOSE 3000
CMD ["python3", "server.py"]
