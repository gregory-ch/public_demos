#!/usr/bin/env python
import os
import sys
import time
import logging
import subprocess

# Настройка логирования в файл и stdout
logging.basicConfig(
    level=logging.INFO,
    format='[CORS-DEBUG] %(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('cors_debug')
logger.info("Debug script starting")

try:
    # Импортируем otree.asgi и получаем его приложение
    import otree.asgi
    logger.info("Successfully imported otree.asgi")
    
    # Получаем домен из переменной окружения или используем значение по умолчанию
    CORS_ALLOW_ORIGIN = os.environ.get('CORS_ALLOW_ORIGIN', 'https://gregory-ch.github.io')
    logger.info(f"Setting up CORS headers for origin: {CORS_ALLOW_ORIGIN}")
    
    # Простая обертка для логирования всех запросов
    async def debug_middleware(scope, receive, send):
        # Логируем информацию о запросе
        if scope["type"] == "http":
            method = scope.get("method", "UNKNOWN")
            path = scope.get("path", "UNKNOWN")
            logger.info(f"Request: {method} {path}")
            
            # Для OPTIONS запросов сразу отвечаем 200 OK с CORS заголовками
            if method == "OPTIONS":
                logger.info(f"Intercepting OPTIONS request to {path}")
                
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
                
                logger.info(f"Responded to OPTIONS request with 200 OK")
                return
        
        # Для всех других запросов просто передаем в приложение
        await otree.asgi.app(scope, receive, send)
    
    # Заменяем приложение otree нашим middleware
    logger.info("Replacing otree.asgi.app with debug middleware")
    original_app = otree.asgi.app
    otree.asgi.app = debug_middleware
    logger.info("CORS debug middleware applied")
    
    # Получаем порт из переменных окружения (для Heroku)
    port = os.environ.get('PORT', '8000')
    
    # Вместо запуска стандартных команд, запускаем напрямую prodserver с нашим измененным приложением
    from otree.main import execute_from_command_line
    logger.info(f"Running otree runprodserver {port}")
    sys.argv = ['otree', 'runprodserver', port]
    execute_from_command_line()
    
except Exception as e:
    # Логируем любые исключения
    logger.error(f"Exception: {str(e)}", exc_info=True)
    
    # В случае ошибки с базой данных, запускаем стандартную команду
    logger.info("Falling back to standard otree prodserver1of2")
    port = os.environ.get('PORT', '8000')
    os.system(f"otree prodserver1of2") 