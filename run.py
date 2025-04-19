#!/usr/bin/env python
import os
import sys
import time
import logging
import json

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='[CORS-WRAPPER] %(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('cors_wrapper')
logger.info("=== CORS Wrapper Starting ===")

# Получаем домен из переменной окружения или используем значение по умолчанию
CORS_ALLOW_ORIGIN = os.environ.get('CORS_ALLOW_ORIGIN', 'https://gregory-ch.github.io')
logger.info(f"CORS origin: {CORS_ALLOW_ORIGIN}")

# Импортируем otree.asgi до всех других импортов oTree
import otree.asgi

# Создаем полностью новое ASGI приложение-обертку
otree_app = otree.asgi.app  # Сохраняем оригинальное приложение oTree

async def cors_wrapper_app(scope, receive, send):
    """
    Полностью новое ASGI приложение, которое будет:
    1. Напрямую отвечать на OPTIONS запросы с CORS заголовками
    2. Добавлять CORS заголовки к ответам oTree для других методов
    """
    # Логируем каждый запрос
    if scope["type"] == "http":
        method = scope.get("method", "UNKNOWN")
        path = scope.get("path", "UNKNOWN")
        client = scope.get("client", ("Unknown", 0))
        logger.info(f"Request: {method} {path} from {client[0]}:{client[1]}")
        
        # Напрямую отвечаем на OPTIONS запросы
        if method == "OPTIONS":
            logger.info(f"Handling OPTIONS request to {path}")
            
            # Отправляем HTTP ответ со статусом 200 и CORS заголовками
            await send({
                "type": "http.response.start",
                "status": 200,
                "headers": [
                    (b"content-type", b"text/plain"),
                    (b"access-control-allow-origin", CORS_ALLOW_ORIGIN.encode()),
                    (b"access-control-allow-methods", b"GET, POST, PUT, DELETE, OPTIONS"),
                    (b"access-control-allow-headers", b"*"),
                    (b"access-control-allow-credentials", b"true"),
                    (b"access-control-max-age", b"1728000")
                ]
            })
            
            await send({
                "type": "http.response.body",
                "body": b"CORS OK",
                "more_body": False
            })
            
            logger.info(f"OPTIONS request handled successfully")
            return
    
    # Для всех других запросов, перенаправляем в oTree, но обрабатываем ответы
    async def send_with_cors(message):
        if message["type"] == "http.response.start":
            # Добавляем CORS заголовки ко всем HTTP ответам
            headers = list(message.get("headers", []))
            
            # Добавляем заголовки CORS
            cors_headers = [
                (b"access-control-allow-origin", CORS_ALLOW_ORIGIN.encode()),
                (b"access-control-allow-methods", b"GET, POST, PUT, DELETE, OPTIONS"),
                (b"access-control-allow-headers", b"*"),
                (b"access-control-allow-credentials", b"true"),
                (b"access-control-max-age", b"1728000")
            ]
            
            # Добавляем только те заголовки, которых еще нет
            existing_header_names = [h[0].lower() for h in headers]
            for header in cors_headers:
                if header[0].lower() not in existing_header_names:
                    headers.append(header)
            
            # Заменяем заголовки в сообщении
            message["headers"] = headers
            
            if scope.get("method") and scope.get("path"):
                logger.info(f"Added CORS headers to response from {scope['method']} {scope['path']}")
        
        # Передаем модифицированное или немодифицированное сообщение дальше
        await send(message)
    
    # Вызываем оригинальное приложение oTree, но перехватываем ответы
    await otree_app(scope, receive, send_with_cors)

# Заменяем приложение oTree нашей оберткой
otree.asgi.app = cors_wrapper_app
logger.info("CORS wrapper applied to oTree ASGI app")

# Запускаем проверку системы
logger.info(f"Python version: {sys.version}")
logger.info(f"Current working dir: {os.getcwd()}")
logger.info(f"PORT: {os.environ.get('PORT', 'not set')}")

# Теперь запускаем стандартный prodserver1of2
logger.info("Starting oTree prodserver1of2")

# Запускаем сервер 
from subprocess import call
logger.info("Executing otree prodserver1of2")
sys.stdout.flush()  # Убедимся, что все логи будут видны
call(["otree", "prodserver1of2"]) 