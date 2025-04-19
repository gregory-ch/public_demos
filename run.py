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

# CORS Headers для всех ответов (вместо middleware)
from starlette.types import ASGIApp, Receive, Scope, Send

class CORSHeaders:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        logger.info("CORS Headers wrapper initialized")

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        # Для WebSocket и HTTP соединений разные подходы
        if scope["type"] == "websocket":
            # Для WebSocket просто пропускаем без модификаций
            await self.app(scope, receive, send)
            return

        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Обработка OPTIONS запросов
        if scope.get("method") == "OPTIONS":
            # Отправляем CORS заголовки и завершаем запрос
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

        # Для остальных HTTP запросов добавляем CORS заголовки к ответу
        async def wrapped_send(message):
            if message["type"] == "http.response.start":
                # Добавляем CORS заголовки ко всем ответам
                headers = list(message.get("headers", []))
                headers.append((b"access-control-allow-origin", CORS_ALLOW_ORIGIN.encode()))
                headers.append((b"access-control-allow-methods", b"GET, POST, PUT, DELETE, OPTIONS"))
                headers.append((b"access-control-allow-headers", b"*"))
                headers.append((b"access-control-allow-credentials", b"true"))
                message["headers"] = headers
            
            await send(message)
        
        await self.app(scope, receive, wrapped_send)

# Применяем наш класс CORSHeaders к oTree app
app = CORSHeaders(otree.asgi.app)

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
        app=app,  # Используем наше модифицированное приложение
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