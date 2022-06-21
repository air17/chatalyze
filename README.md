# Chatalyze

Analyze your chats!

## Installation for development

0. Install `python3`
1. Change directory to `chatalyze/chatalyze` (`cd chatalyze` for Windows)
2. Install dependencies: `pip install -r requirements-dev.txt`
3. Run `pre-commit install` and `pre-commit install --hook-type pre-push`
4. Setup PostgreSQL Database
5. Rename `.env.template` to `.env` in `config` directory and fill it
6. Run `python manage.py makemigrations`
7. Run `python manage.py migrate`
8. Run `python manage.py runserver`
9. Go to http://127.0.0.1:8000

### Tests
Run `pytest`

## Author

[Bulent Ozcan](https://github.com/air17)
