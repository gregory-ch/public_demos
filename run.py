#!/usr/bin/env python
import os
import sys
import subprocess

# Импортируем otree.asgi и модифицируем app
import otree.asgi
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware import Middleware

print("Setting up CORS headers in run.py...")

# Способ 1: Добавляем CORS middleware через стандартный метод
# (это работает, если add_middleware добавляет middleware в правильном порядке)
otree.asgi.app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://gregory-ch.github.io"],
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
        
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
            
        async def send_with_cors(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append((b"access-control-allow-origin", b"https://gregory-ch.github.io"))
                headers.append((b"access-control-allow-methods", b"GET, POST, PUT, DELETE, OPTIONS"))
                headers.append((b"access-control-allow-headers", b"*"))
                headers.append((b"access-control-allow-credentials", b"true"))
                headers.append((b"access-control-max-age", b"1728000"))
                message["headers"] = headers
                
                # Специальная обработка для OPTIONS запросов
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