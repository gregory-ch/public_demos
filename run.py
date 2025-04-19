import os
import sys
import subprocess
from starlette.middleware.cors import CORSMiddleware
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

        # Если запрос к статическим файлам, пропускаем без модификации
        path = scope.get("path", "").decode("utf-8") if isinstance(scope.get("path", ""), bytes) else scope.get("path", "")
        if path.startswith("/static/") or path.endswith((".css", ".js", ".ico", ".png", ".jpg")):
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

# Импортируем модуль otree.asgi ТОЛЬКО после того, как определили middleware
import otree.asgi
from importlib import reload

# Применяем наш middleware к приложению oTree
original_app = otree.asgi.app

# Добавляем CORS middleware
original_app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=1728000
)

# Оборачиваем приложение в наш middleware для OPTIONS запросов
otree.asgi.app = OptionsCorsMiddleware(original_app)

# Перезагружаем модуль otree.asgi, чтобы изменения вступили в силу
reload(otree.asgi)

# Монтируем наш импорт как application для Heroku
application = otree.asgi.app

# Запускаем сервер
if __name__ == "__main__":
    # Получаем порт из переменных окружения (для Heroku)
    port = os.environ.get('PORT', '8000')
    
    # Запускаем timeoutsubprocess (как в prodserver1of2)
    subprocess.Popen(
        ['otree', 'timeoutsubprocess', str(port)], 
        env=os.environ.copy()
    )
    
    print('Running custom prodserver with CORS middleware')
    
    # Импортируем uvicorn только после определения и патчинга приложения
    from uvicorn.main import Config, Server
    
    # Запускаем сервер с нашим модифицированным приложением
    config = Config(
        app=application,
        host='0.0.0.0',
        port=int(port),
        log_level="info",
        log_config=None,
        workers=1,
        ws='websockets',
    )
    server = Server(config=config)
    server.run() 