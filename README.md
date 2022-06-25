# Chatalyze

Analyze your chats!

Live demo: https://chatalyze.161e.tk

## Install

### Run in Docker

1. `git clone https://github.com/air17/chatalyze.git`
2. Set current directory `chatalyze`
3. Rename `.env.template` file to `.env` and fill it.
4. Run `docker compose up -d`
5. Optional: create admin user with a command `docker exec -it django_web python manage.py createsuperuser`
6. Go to http://localhost:8000

### Installation for development

0. Install `python3`
1. Install dependencies: `pip install -r requirements-dev.txt`
2. Run `pre-commit install` and `pre-commit install --hook-type pre-push`
3. Setup PostgreSQL Database
4. Rename `.env.template` to `.env` in `config` directory and fill it
5. Run `python manage.py makemigrations`
6. Run `python manage.py migrate`
7. Run `python manage.py runserver`
8. Go to http://127.0.0.1:8000

### Tests
Run `pytest`

## Author

[Bulent Ozcan](https://github.com/air17)
