#!/usr/bin/env bash
# Render build script — runs once every deploy
set -o errexit

pip install --upgrade pip
pip install -r requirements-production.txt
python manage.py collectstatic --noinput
python manage.py migrate --noinput
