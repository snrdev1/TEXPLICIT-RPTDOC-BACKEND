# TEXPLICIT2-BACKEND-B2C

## Note: 

- [If getting error then install exe](https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases)

## Celery and Redis

[Installing and setting up redis](https://developer.redis.com/create/windows/)

`celery -A app.celery worker --loglevel=info`

On Windows : `celery -A app.celery worker --loglevel=info -P solo`

Using Flower for monitoring : `celery -A app.celery flower --port=5555`

## Generating requirements.txt using Poetry

`poetry export --without-hashes --format=requirements.txt > requirements.txt`