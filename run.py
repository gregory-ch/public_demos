#!/usr/bin/env python
import os
import sys
import subprocess

# Импортируем otree.asgi и получаем его приложение
import otree.asgi
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware import Middleware
from starlette.responses import Response

# Получаем домен из переменной окружения или используем значение по умолчанию
CORS_ALLOW_ORIGIN = os.environ.get('CORS_ALLOW_ORIGIN', 'https://gregory-ch.github.io')
print(f"Setting up CORS headers in run.py for origin: {CORS_ALLOW_ORIGIN}")

# Вместо добавления middleware, создаем полностью новое ASGI приложение
# которое перехватывает запросы до того, как они попадут в oTree
class CorsApplication:
    def __init__(self, app):
        self.app = app
        self.cors_origin = CORS_ALLOW_ORIGIN.encode()
        print("Creating custom ASGI application wrapper")
        
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Перехватываем все OPTIONS запросы и обрабатываем их напрямую
        if scope["method"] == "OPTIONS":
            print(f"Intercepting OPTIONS request to {scope['path']}")
            
            # Отправляем HTTP ответ со статусом 200 и CORS заголовками
            await send({
                "type": "http.response.start",
                "status": 200,
                "headers": [
                    (b"content-type", b"text/plain"),
                    (b"access-control-allow-origin", self.cors_origin),
                    (b"access-control-allow-methods", b"GET, POST, PUT, DELETE, OPTIONS"),
                    (b"access-control-allow-headers", b"*"),
                    (b"access-control-allow-credentials", b"true"),
                    (b"access-control-max-age", b"1728000")
                ]
            })
            await send({
                "type": "http.response.body",
                "body": b"OK",
                "more_body": False
            })
            return
            
        # Для не-OPTIONS запросов добавляем CORS заголовки к ответам
        async def send_with_cors(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                # Добавляем CORS заголовки
                headers.append((b"access-control-allow-origin", self.cors_origin))
                headers.append((b"access-control-allow-methods", b"GET, POST, PUT, DELETE, OPTIONS"))
                headers.append((b"access-control-allow-headers", b"*"))
                headers.append((b"access-control-allow-credentials", b"true"))
                headers.append((b"access-control-max-age", b"1728000"))
                message["headers"] = headers
            
            await send(message)
            
        await self.app(scope, receive, send_with_cors)

# Создаем новое приложение, заменяя приложение oTree нашим обертывающим приложением
app = otree.asgi.app
otree.asgi.app = CorsApplication(app)

print("CORS wrapper successfully applied to oTree application")

# Получаем порт из переменных окружения (для Heroku)
port = os.environ.get('PORT', '8000')

# Запускаем timeoutsubprocess для обработки таймаутов
subprocess.Popen(
    ['otree', 'timeoutsubprocess', str(port)], 
    env=os.environ.copy()
)

print('Running prodserver with patched CORS application')

# Запускаем стандартный prodserver1of2
os.system(f"otree prodserver1of2") 