FROM python:3.11-slim

ARG INSTALL_DIARIZATION=false

WORKDIR /app

# Dépendances système
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Installe les librairies Python
COPY requirements.txt requirements-diarization.txt ./
RUN pip install --no-cache-dir -r requirements.txt
RUN if [ "$INSTALL_DIARIZATION" = "true" ]; then \
      pip install --no-cache-dir -r requirements-diarization.txt; \
    fi

# Copie le code
COPY . /app/pipeline_worker/

WORKDIR /app/pipeline_worker

CMD ["python", "-u", "worker.py"]
