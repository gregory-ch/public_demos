#!/usr/bin/env python
import os
import sys
import time
import logging

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='[CORS-DEBUG] %(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('cors_debug')
logger.info("Debug script starting")

# Получаем домен из переменной окружения или используем значение по умолчанию
CORS_ALLOW_ORIGIN = os.environ.get('CORS_ALLOW_ORIGIN', 'https://gregory-ch.github.io')
logger.info(f"Setting up CORS headers for origin: {CORS_ALLOW_ORIGIN}")

# Импортируем otree.asgi до всех других импортов oTree
import otree.asgi

# Создаем класс CORS middleware который добавит заголовки ко всем ответам
from starlette.middleware.cors import CORSMiddleware

# Применяем CORS middleware стандартным способом
logger.info("Adding CORS middleware to oTree app")
otree.asgi.app.add_middleware(
    CORSMiddleware,
    allow_origins=[CORS_ALLOW_ORIGIN, "*"],  # Разрешаем любой источник для тестирования
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=1728000
)

# Теперь запускаем стандартный prodserver1of2
logger.info("Starting oTree prodserver1of2")
os.environ["PYTHONUNBUFFERED"] = "1"  # Убираем буферизацию вывода

port = os.environ.get('PORT', '8000')
logger.info(f"Using port: {port}")

# Запускаем сервер напрямую, избегая проблем с базой данных
from subprocess import call
logger.info("Executing otree prodserver1of2")
call(["otree", "prodserver1of2"]) 