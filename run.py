import os
import sys
import subprocess
import logging
from uvicorn.main import Config, Server
from typing import Callable

# Импортируем приложение oTree
from otree.asgi import app
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp, Receive, Scope, Send

# Разрешенные домены для CORS
ALLOWED_ORIGINS = ["https://gregory-ch.github.io"]

# Специальный middleware для обработки OPTIONS запросов
class OptionsCorsMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        self.allowed_origins = ALLOWED_ORIGINS

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Получаем origin из заголовков запроса
        origin = None
        for key, value in scope.get("headers", []):
            if key.decode("latin1").lower() == "origin":
                origin = value.decode("latin1")
                break
        
        # Если origin отсутствует или не в списке разрешенных, не добавляем CORS-заголовки
        if not origin or origin not in self.allowed_origins:
            await self.app(scope, receive, send)
            return

        # Обработка OPTIONS запросов
        if scope["method"] == "OPTIONS":
            headers = [
                (b"access-control-allow-origin", origin.encode()),
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
            return
            
        # Добавляем CORS-заголовки ко всем другим ответам
        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append((b"access-control-allow-origin", origin.encode()))
                headers.append((b"access-control-allow-methods", b"GET, POST, PUT, DELETE, OPTIONS"))
                headers.append((b"access-control-allow-headers", b"*"))
                headers.append((b"access-control-allow-credentials", b"true"))
                message["headers"] = headers
            await send(message)
            
        await self.app(scope, receive, send_wrapper)

# Добавляем CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,  # Разрешаем запросы только с Jekyll сайта
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=1728000
)

# Оборачиваем приложение нашим кастомным middleware для обработки OPTIONS
app = OptionsCorsMiddleware(app)

# Настраиваем логгирование
logger = logging.getLogger(__name__)
print_function = print

def main():
    # Получаем порт из переменных окружения (для Heroku)
    port = os.environ.get('PORT', '8000')
    
    # Запускаем timeoutsubprocess (как в prodserver1of2)
    subprocess.Popen(
        ['otree', 'timeoutsubprocess', str(port)], 
        env=os.environ.copy()
    )
    
    print_function('Running custom prodserver with CORS middleware')
    
    # Запускаем Uvicorn с нашим модифицированным app
    config = Config(
        app=app,  # Напрямую используем модифицированное приложение
        host='0.0.0.0',
        port=int(port),
        log_level="info",
        log_config=None,  # oTree имеет свой логгер
        workers=1,
        ws='websockets',  # websockets библиотека обрабатывает отключения автоматически
    )
    server = Server(config=config)
    server.run()

if __name__ == "__main__":
    main() 