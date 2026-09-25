FROM python:3.11-slim

# Dependencias del sistema necesarias para WeasyPrint + certificados SSL
RUN apt-get update && apt-get install -y \
    libcairo2 \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    libxml2 \
    libxslt1.1 \
    libharfbuzz0b \
    libfreetype6 \
    shared-mime-info \
    fonts-dejavu-core \
    fonts-inter \
    ca-certificates \
    && update-ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Sora y DM Mono van EN EL REPO y no se descargan en el build: una descarga
# aquí ataría cada construcción a que GitHub responda y a que la URL siga
# existiendo, y dos builds del mismo commit podrían dar imágenes distintas.
# Son OFL, así que se distribuyen con su licencia al lado (fonts/OFL-*.txt).
COPY fonts/*.ttf /usr/share/fonts/truetype/tecton/
RUN fc-cache -f >/dev/null

WORKDIR /app

# Copiamos metadata y código
COPY pyproject.toml README.md ./
COPY src/ src/

# Instalamos la librería con extras de servicio
RUN pip install --no-cache-dir pip setuptools wheel \
    && pip install --no-cache-dir -e .[service] certifi

EXPOSE 8080

CMD ["sh", "-c", "uvicorn service.main:app --host 0.0.0.0 --port ${PORT:-8080} --workers 2"]
