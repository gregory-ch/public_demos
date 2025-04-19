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
ALLOWED_ORIGINS = [CORS_ALLOW_ORIGIN]
logger.info(f"CORS allowed origins: {ALLOWED_ORIGINS}")

# Импортируем oTree ASGI приложение
# Важно: импортируем до применения middleware
import otree.asgi

# Применяем CORS middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.types import ASGIApp, Receive, Scope, Send

# Кастомный middleware для обработки OPTIONS запросов и статических файлов
class OptionsAndStaticCorsMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        logger.info("OptionsAndStaticCorsMiddleware initialized")

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        # Пропускаем не-HTTP запросы
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Проверяем, является ли запрос запросом к статическому файлу
        path = scope.get("path", "")
        is_static = path.startswith("/static/")

        # Получаем origin из заголовков запроса
        origin = None
        for key, value in scope.get("headers", []):
            if key.decode("latin1").lower() == "origin":
                origin = value.decode("latin1")
                break

        # Обработка OPTIONS запросов
        if scope.get("method") == "OPTIONS":
            logger.info(f"Processing OPTIONS request to {path}")
            
            # Определяем, какой origin использовать
            origin_value = origin if origin else "*"
            if origin in ALLOWED_ORIGINS:
                origin_value = origin
            
            headers = [
                (b"access-control-allow-origin", origin_value.encode()),
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
            logger.info(f"Responded to OPTIONS request with 200 OK")
            return

        # Для обычных запросов обертываем send функцию, чтобы добавить CORS заголовки
        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                
                # Добавляем CORS заголовки только для не-статических файлов или если есть origin
                if origin and (origin in ALLOWED_ORIGINS or is_static):
                    # Проверяем, есть ли уже такие заголовки
                    header_names = [h[0].lower() for h in headers]
                    
                    # Добавляем только если нет
                    if b"access-control-allow-origin" not in header_names:
                        headers.append((b"access-control-allow-origin", origin.encode()))
                    if b"access-control-allow-methods" not in header_names:
                        headers.append((b"access-control-allow-methods", b"GET, POST, PUT, DELETE, OPTIONS"))
                    if b"access-control-allow-headers" not in header_names:
                        headers.append((b"access-control-allow-headers", b"*"))
                    if b"access-control-allow-credentials" not in header_names:
                        headers.append((b"access-control-allow-credentials", b"true"))
                    
                    message["headers"] = headers
                    
                    if not is_static:
                        logger.info(f"Added CORS headers to response for {path}")
            
            await send(message)
            
        # Передаем запрос в приложение с оберткой для send
        await self.app(scope, receive, send_wrapper)

# Добавляем стандартный CORSMiddleware (для совместимости с другими компонентами)
logger.info("Applying standard CORSMiddleware")
otree.asgi.app.add_middleware(
    CORSMiddleware,
    allow_origins=["*", CORS_ALLOW_ORIGIN],  # Разрешаем любые источники для статических файлов
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=1728000
)

# Применяем наш кастомный middleware для OPTIONS запросов и статических файлов
logger.info("Applying custom OptionsAndStaticCorsMiddleware")
app = OptionsAndStaticCorsMiddleware(otree.asgi.app)

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
    
    logger.info(f"Running custom prodserver with CORS on {addr}:{port}")
    
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