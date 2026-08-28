# Python 3.11 image'dan foydalanamiz
FROM python:3.11-slim

# Konteyner ichidagi ishchi papka
WORKDIR /app

# Atrof-muhit o'zgaruvchilari
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Tizim uchun zaruriy paketlarni o'rnatish
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Pip va bog'liqliklarni o'rnatish
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Loyiha kodlarini konteynerga nusxalash
COPY . .

# FastAPI ishga tushirish buyrug'i
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]# Python 3.11 image'dan foydalanamiz
FROM python:3.11-slim

# Konteyner ichidagi ishchi papka
WORKDIR /app

# Atrof-muhit o'zgaruvchilari
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Tizim uchun zaruriy paketlarni o'rnatish
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Pip va bog'liqliklarni o'rnatish
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Loyiha kodlarini konteynerga nusxalash
COPY . .

# FastAPI ishga tushirish buyrug'i
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]