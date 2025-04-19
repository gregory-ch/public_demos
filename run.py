#!/usr/bin/env python
import os
import sys
import subprocess

# Добавляем CORS заголовки через переменные окружения
# os.environ['CORS_ALLOW_ORIGIN'] = 'https://gregory-ch.github.io'

# Получаем порт из переменных окружения (для Heroku)
port = os.environ.get('PORT', '8000')

# Запускаем стандартный продсервер без модификаций
os.system(f"otree prodserver1of2 {port}") 