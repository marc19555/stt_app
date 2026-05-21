FROM python:3.11-slim

WORKDIR /app

# Dépendances système
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copie et installe les packages Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copie le projet
COPY . .

# Lance Jupyter
CMD ["jupyter", "notebook", "--ip=0.0.0.0", "--port=8888", "--no-browser", "--allow-root", "--ContentsManager.allow_hidden=True"]