# ![Chatalyze logo](https://github.com/air17/chatalyze/raw/dev/chatalyze/static/assets/img/favicon/favicon-32x32.png) Chatalyze

A web app that analyzes exported chat file from supported platforms and generates a report containing statistics, charts and a wordcloud.

Live demo: https://chatalyze.161e.tk

![Chatalyze mockup](https://github.com/air17/chatalyze/raw/dev/chatalyze/static/assets/img/mockup-presentation.png)

## Features

- Both group and private chats are supported
- Intuitive user interface
- Multiple languages supported (currently english, russian and ukrainian)
- Multiple platforms support
  - Telegram
  - WhatsApp
  - Facebook Messenger

## How to export your chat

[Instruction](how-to-export.md) for supported platforms.

## Installation

### Run in Docker

1. Clone this repo `git clone https://github.com/air17/chatalyze.git` and go to it's root folder.
2. Rename `.env.template` file in the root folder to `.env` and fill it in.
3. Run `docker compose up -d`
4. Optional: create admin user with a command `docker exec -it django_web python manage.py createsuperuser`
5. Go to http://localhost:8000

### Install for development

0. Install `python3`
1. Clone this repo `git clone https://github.com/air17/chatalyze.git` and go to it's root directory.
2. Install dependencies: `pip install -r requirements.txt` and `pip install -r requirements-dev.txt`
3. Run `pre-commit install` and `pre-commit install --hook-type pre-push` to set up Git hooks
4. Setup PostgreSQL Database
5. Rename `.env.template` to `.env` in `chatalyze/config` directory and fill it in.
6. Run `python manage.py makemigrations`
7. Run `python manage.py migrate`
8. Run `python manage.py runserver`
9. Run celery worker `celery -A core worker --pool=solo -l INFO`
10. Go to http://127.0.0.1:8000

### Tests
Run `pytest`

## License
[GPL-3.0 license](https://github.com/air17/chatalyze/blob/dev/LICENSE.txt)

## Author

[Bulent Ozcan](https://github.com/air17)
