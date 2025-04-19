#!/usr/bin/env python
import os
import sys
import subprocess

# Импортируем otree.asgi и модифицируем app
import otree.asgi
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware import Middleware
from starlette.responses import Response

# Получаем домен из переменной окружения или используем значение по умолчанию
CORS_ALLOW_ORIGIN = os.environ.get('CORS_ALLOW_ORIGIN', 'https://gregory-ch.github.io')
print(f"Setting up CORS headers in run.py for origin: {CORS_ALLOW_ORIGIN}")

# Способ 1: Добавляем CORS middleware через стандартный метод
# (это работает, если add_middleware добавляет middleware в правильном порядке)
otree.asgi.app.add_middleware(
    CORSMiddleware,
    allow_origins=[CORS_ALLOW_ORIGIN],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    max_age=1728000
)

# Способ 2: Для надежности создаем ASGI middleware, который будет первым в цепочке
# Этот подход обойдет ограничения кастомного build_middleware_stack
class CorsAsgiMiddleware:
    def __init__(self, app):
        self.app = app
        self.cors_origin = CORS_ALLOW_ORIGIN.encode()
        
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
            
        # Специальная обработка для OPTIONS запросов к корневому пути
        if scope["method"] == "OPTIONS" and scope["path"] == "/":
            # Сразу отвечаем на OPTIONS запрос без передачи в приложение
            async def send_options_response(message):
                if message["type"] == "http.response.start":
                    headers = [
                        (b"content-type", b"text/plain"),
                        (b"access-control-allow-origin", self.cors_origin),
                        (b"access-control-allow-methods", b"GET, POST, PUT, DELETE, OPTIONS"),
                        (b"access-control-allow-headers", b"*"),
                        (b"access-control-allow-credentials", b"true"),
                        (b"access-control-max-age", b"1728000")
                    ]
                    return await send({"type": "http.response.start", "status": 200, "headers": headers})
                elif message["type"] == "http.response.body":
                    return await send({"type": "http.response.body", "body": b"OK", "more_body": False})
            
            # Отправляем HTTP ответ со статусом 200 и CORS заголовками
            await send_options_response({"type": "http.response.start"})
            await send_options_response({"type": "http.response.body"})
            return
            
        async def send_with_cors(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append((b"access-control-allow-origin", self.cors_origin))
                headers.append((b"access-control-allow-methods", b"GET, POST, PUT, DELETE, OPTIONS"))
                headers.append((b"access-control-allow-headers", b"*"))
                headers.append((b"access-control-allow-credentials", b"true"))
                headers.append((b"access-control-max-age", b"1728000"))
                message["headers"] = headers
                
                # Специальная обработка для OPTIONS запросов к другим маршрутам
                if scope["method"] == "OPTIONS":
                    message["status"] = 200
            
            await send(message)
            
        await self.app(scope, receive, send_with_cors)

# Обертываем приложение в наш CORS middleware
# Это гарантирует, что CORS заголовки будут добавлены независимо от порядка middleware
otree.asgi.app = CorsAsgiMiddleware(otree.asgi.app)

print("CORS middleware successfully added to oTree application")

# Получаем порт из переменных окружения (для Heroku)
port = os.environ.get('PORT', '8000')

# Запускаем timeoutsubprocess для обработки таймаутов
subprocess.Popen(
    ['otree', 'timeoutsubprocess', str(port)], 
    env=os.environ.copy()
)

print('Running prodserver with patched CORS middleware')

# Запускаем стандартный prodserver1of2
os.system(f"otree prodserver1of2") 