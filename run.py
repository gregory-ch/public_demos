#!/usr/bin/env python
import os
import sys
import subprocess
import logging
from uvicorn.main import Config, Server

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='[CORS-SERVER] %(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('cors_server')
logger.info("=== Custom CORS prodserver starting ===")

# Разрешенные домены для CORS
CORS_ALLOW_ORIGIN = os.environ.get('CORS_ALLOW_ORIGIN', 'https://gregory-ch.github.io')
logger.info(f"CORS allowed origin: {CORS_ALLOW_ORIGIN}")

# Импортируем oTree ASGI приложение
import otree.asgi
from starlette.types import ASGIApp, Receive, Scope, Send

# Очень простой middleware только для OPTIONS запросов
class OptionsMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        logger.info("Simple OPTIONS middleware initialized")

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        # Пропускаем не-HTTP запросы
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Проверяем, является ли запрос OPTIONS
        if scope.get("method") == "OPTIONS":
            path = scope.get("path", "")
            logger.info(f"Handling OPTIONS request to {path}")
            
            headers = [
                (b"access-control-allow-origin", CORS_ALLOW_ORIGIN.encode()),
                (b"access-control-allow-methods", b"GET, POST, PUT, DELETE, OPTIONS"),
                (b"access-control-allow-headers", b"*"),
                (b"access-control-allow-credentials", b"true"),
                (b"access-control-max-age", b"1728000"),
                (b"content-type", b"text/plain"),
                (b"content-length", b"0"),
            ]
            
            await send({
                "type": "http.response.start",
                "status": 200,
                "headers": headers,
            })
            
            await send({
                "type": "http.response.body",
                "body": b"",
            })
            logger.info("Responded to OPTIONS request with 200 OK")
            return
        
        # Для всех других запросов просто пропускаем к oTree
        await self.app(scope, receive, send)

# Добавляем стандартный CORSMiddleware к приложению oTree
from starlette.middleware.cors import CORSMiddleware

logger.info("Adding CORS middleware to oTree app")
otree.asgi.app.add_middleware(
    CORSMiddleware,
    allow_origins=[CORS_ALLOW_ORIGIN, "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=1728000
)

# Применяем наш простой middleware для OPTIONS запросов
logger.info("Applying OPTIONS middleware")
app = OptionsMiddleware(otree.asgi.app)

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
    
    logger.info(f"Running prodserver with CORS on {addr}:{port}")
    
    # Запускаем Uvicorn напрямую с нашим модифицированным app
    # Точно соответствует конфигурации в prodserver1of2.py
    config = Config(
        app=app,  # Используем наше модифицированное приложение
        host=addr,
        port=int(port),
        log_level="info",
        log_config=None,  # oTree имеет свой логгер
        workers=1,
        ws='websockets',  # websockets библиотека обрабатывает отключения автоматически
    )
    
    logger.info("Starting Uvicorn server")
    server = Server(config=config)
    server.run()

if __name__ == "__main__":
    main() 