# Используем Python 3.8 для архитектуры x86_64
FROM --platform=linux/amd64 python:3.8.5-slim-buster

# Устанавливаем системные зависимости для сборки
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    git \
    libssl-dev \
    libbz2-dev \
    libreadline-dev \
    libsqlite3-dev \
    zlib1g-dev \
    liblzma-dev \
    tk-dev \
    libffi-dev \
    wget \
    && apt-get clean

# Устанавливаем рабочую директорию для приложения (директория /app)
WORKDIR /app

# Копируем все файлы из текущей директории в /app
COPY . /app

# Устанавливаем необходимые версии pip и setuptools
RUN pip install --upgrade pip setuptools

# Устанавливаем зависимости из requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Устанавливаем Uvicorn
RUN pip install uvicorn

# Указываем команду для запуска приложения с помощью Uvicorn
CMD ["uvicorn", "app:app", "--reload", , "--host", "0.0.0.0"]
