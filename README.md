#  Foodgram

## **Описание проекта**:
## 1. [Описание](#1)
## 2. [Установка Docker (на платформе Ubuntu)](#2)
## 3. [База данных и переменные окружения](#3)
## 4. [Команды для запуска](#4)
## 5. [Заполнение базы данных](#5)
## 6. [Техническая информация](#6)
## 7. [Об авторе](#7)

Foodgrm - сайт для публикации рецептов.
### Используемые технологии
- [Python 3.10](https://docs.python.org/3.10/)
- [Node.js 18.20](https://nodejs.org/en/download)
- [Django 3.2.16](https://docs.djangoproject.com/en/5.0/))
- [DRF 3.12.4](https://www.django-rest-framework.org/)
- [Docker](https://www.docker.com/)
- [Nginx](https://nginx.org/)
- [Gunicorn](https://gunicorn.org/)
- [JWT](https://jwt.io/) & [djoser](https://djoser.readthedocs.io/en/latest/getting_started.html)
### Как установить и запустить проект:

1. Клонируйте репозиторий на компьютер:
    ```
    git clone git@github.com:a1exandermy/foodgram.git
    ```
2. Создайте файл переменных окружения `.env` и наполните его своими данными.

### Создание Docker-образов

1. Создаете образы локально на вашем компьютере

    ```
    cd frontend
    docker build -t <your_username>/foodgram_frontend .
    cd ../backend
    docker build -t your_username/foodgram_backend .
    cd ../nginx
    docker build -t your_username/foodgram_gateway . 
    ```

2. Загрузите образы на DockerHub:

    ```
    docker push your_username/foodgram_frontend
    docker push your_username/foodgram_backend
    docker push your_username/foodgram_gateway
    ```

### Деплой на сервере

1. Подключитесь к удаленному серверу
2. Создайте на сервере директорию `foodgram`:

    ```
    mkdir foodgram
    ```

3. Установите Docker Compose на сервер:

    ```
    sudo apt update
    sudo apt install curl
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo apt install docker-compose
    ```

4. Скопируйте файлы `docker-compose.production.yml` и `.env` в директорию `foodgram/` на сервере:

    ```
    scp -i PATH_TO_SSH_KEY/SSH_KEY_NAME docker-compose.production.yml YOUR_USERNAME@SERVER_IP_ADDRESS:/home/YOUR_USERNAME/foodgram/docker-compose.production.yml
    ```
    - `PATH_TO_SSH_KEY` - путь к файлу с вашим SSH-ключом
    - `SSH_KEY_NAME` - имя файла с вашим SSH-ключом
    - `YOUR_USERNAME` - ваше имя пользователя на сервере
    - `SERVER_IP_ADDRESS` - IP-адрес вашего сервера

5. Запустите Docker Compose:

    ```
    sudo docker-compose -f /home/YOUR_USERNAME/foodgram/docker-compose.production.yml up -d
    ```

6. Выполните миграции, загрузите данные ингридиентов в БД, соберите статические файлы бэкенда и скопируйте их в `/backend_static/static/`:

    ```
    sudo docker-compose -f docker-compose.production.yml exec backend python manage.py migrate
    sudo docker-compose -f docker-compose.production.yml exec backend python manage.py collectstatic
    sudo docker-compose -f docker-compose.production.yml exec backend python manage.py load_data
    sudo docker-compose -f docker-compose.production.yml exec backend cp -r /app/collected_static/. /backend_static/static/
    ```

7. Откройте конфигурационный файл Nginx в редакторе nano:

    ```
    sudo nano /etc/nginx/sites-enabled/default
    ```

8. Измените настройки `location` в секции `server`:

    ```
    location / {
        proxy_set_header Host $http_host;
        proxy_pass http://127.0.0.1:9000;
    }
    ```
9. Перезапустите Nginx:

    ```
    sudo service nginx reload
    ```

### Настройка CI/CD

1. Файл workflow уже написан и находится в директории:

    ```
    foodgram/.github/workflows/main.yml
    ```

2. Для адаптации его к вашему серверу добавьте секреты в GitHub Actions:

    ```
    DOCKER_USERNAME                # имя пользователя в DockerHub
    DOCKER_PASSWORD                # пароль пользователя в DockerHub
    HOST                           # IP-адрес сервера
    USER                           # имя пользователя
    SSH_KEY                        # содержимое приватного SSH-ключа (cat ~/.ssh/id_rsa)
    SSH_PASSPHRASE                 # пароль для SSH-ключа

    TELEGRAM_TO                    # ID вашего телеграм-аккаунта (можно узнать у @userinfobot, команда /start)
    TELEGRAM_TOKEN                 # токен вашего бота (получить токен можно у @BotFather, команда /token, имя бота)
    ```

Автор:
[Мышкин Александр](https://github.com/A1exanderMY/)



