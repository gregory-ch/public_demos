#!/usr/bin/env python
import os
import sys
import subprocess
import logging
from uvicorn.main import Config, Server

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='[OTREE-CORS] %(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('otree_cors')
logger.info("=== Starting oTree with CORS support ===")

# Получаем разрешенный домен для CORS из переменных окружения
CORS_ALLOW_ORIGIN = os.environ.get('CORS_ALLOW_ORIGIN', 'https://gregory-ch.github.io')
logger.info(f"CORS allowed origin: {CORS_ALLOW_ORIGIN}")

# Импортируем приложение oTree перед любыми модификациями
import otree.asgi

# Добавляем CORS middleware к приложению oTree используя стандартный middleware
from starlette.middleware.cors import CORSMiddleware

# Настройка CORS
logger.info("Adding CORS middleware to oTree app")
otree.asgi.app.add_middleware(
    CORSMiddleware,
    allow_origins=[CORS_ALLOW_ORIGIN, "*"],  # Разрешаем указанный домен и * для статики
    allow_credentials=True,
    allow_methods=["*"],  # Все методы
    allow_headers=["*"],  # Все заголовки
    expose_headers=["*"],
    max_age=1728000,  # 20 дней в секундах
)

# Основная функция для запуска сервера
def main():
    # Получаем порт из переменных окружения (для Heroku)
    port = os.environ.get('PORT', '8000')
    addr = '0.0.0.0'  # На Heroku нужно слушать на всех интерфейсах
    
    # Запускаем timeoutsubprocess (точно как в prodserver1of2)
    logger.info(f"Starting otree timeoutsubprocess {port}")
    subprocess.Popen(
        ['otree', 'timeoutsubprocess', str(port)], 
        env=os.environ.copy()
    )
    
    logger.info(f"Running oTree server with CORS on {addr}:{port}")
    
    # Конфигурация и запуск сервера - точно как в prodserver1of2
    config = Config(
        app=otree.asgi.app,  # Используем стандартное приложение oTree с нашим middleware
        host=addr,
        port=int(port),
        log_level="info",
        log_config=None,  # oTree имеет свой логгер
        workers=1,
        ws='websockets',  # websockets библиотека для WebSocket
    )
    
    logger.info("Starting Uvicorn server")
    server = Server(config=config)
    server.run()

if __name__ == "__main__":
    main() 