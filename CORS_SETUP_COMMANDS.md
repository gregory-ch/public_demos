# История команд для настройки CORS в oTree 5+

Ниже представлена последовательность команд и действий, которые были выполнены для настройки CORS в oTree 5+ на Heroku.

## 1. Попытка настройки через asgi.py

```python
# asgi.py
from otree.asgi import app
from starlette.middleware.cors import CORSMiddleware

# Добавляем CORS middleware к приложению oTree
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://gregory-ch.github.io"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    max_age=1728000
)

# Экспортируем приложение для Heroku
application = app
```

Это не сработало, так как oTree при запуске использует свой модуль otree.asgi, а не локальный файл asgi.py.

## 2. Попытка настройки через settings.py

```python
# settings.py
MIDDLEWARE = [
    'starlette.middleware.cors.CORSMiddleware',
]

CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_METHODS = ["*"]
CORS_ALLOW_HEADERS = ["*"]
```

Это также не сработало, так как oTree инициализирует приложение и middleware в особом порядке.

## 3. Анализ работы prodserver

Изучили, что делает команда `otree prodserver1of2`:

```python
# Фрагмент кода продсервера
def run_uvicorn(addr, port, *, is_devserver):
    from uvicorn.main import Config, Server

    config = Config(
        'otree.asgi:app',
        host=addr,
        port=int(port),
        log_level='warning' if is_devserver else "info",
        log_config=None,
        workers=1,
        ws='websockets',
    )
    server = Server(config=config)
    server.run()
```

Выяснили, что prodserver запускает Uvicorn и загружает app из модуля otree.asgi.

## 4. Создание кастомного скрипта запуска

```bash
# Создаем файл run.py
touch run.py
```

```python
# run.py - улучшенная версия
import os
import sys
import importlib
import subprocess
from importlib import reload

# Импортируем модуль otree.asgi перед патчингом
import otree.asgi

# Импортируем необходимые зависимости
from starlette.middleware.cors import CORSMiddleware
from starlette.types import ASGIApp, Receive, Scope, Send

# Патчим CORS для специальной обработки OPTIONS запросов
ALLOWED_ORIGINS = ["https://gregory-ch.github.io"]

# Сохраняем оригинальное приложение
original_app = otree.asgi.app

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
original_app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=1728000
)

# Оборачиваем приложение нашим кастомным middleware
patched_app = OptionsCorsMiddleware(original_app)

# Заменяем приложение в модуле otree.asgi
otree.asgi.app = patched_app

# Перезагружаем модуль, чтобы изменения вступили в силу
reload(otree.asgi)

# Запускаем оригинальный prodserver1of2
if __name__ == "__main__":
    # Запускаем timeoutsubprocess для обработки таймаутов (как в оригинальном prodserver)
    port = os.environ.get('PORT', '8000')
    subprocess.Popen(
        ['otree', 'timeoutsubprocess', str(port)],
        env=os.environ.copy()
    )
    
    print('Running patched otree prodserver with CORS middleware')
    
    # Запускаем оригинальный prodserver1of2 (это сохранит всю логику по работе со статическими файлами)
    os.system(f"otree prodserver1of2")
```

## 5. Создание кастомного middleware

```python
# middleware.py
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from starlette.types import ASGIApp, Receive, Scope, Send

class CorsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "*"
        response.headers["Access-Control-Allow-Credentials"] = "true"
        return response

class CorsASGIMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append((b"access-control-allow-origin", b"*"))
                headers.append((b"access-control-allow-methods", b"GET, POST, PUT, DELETE, OPTIONS"))
                headers.append((b"access-control-allow-headers", b"*"))
                headers.append((b"access-control-allow-credentials", b"true"))
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_wrapper)
```

## 6. Модификация Procfile

```bash
# Изменяем Procfile
echo "web: python run.py" > Procfile
echo "worker: otree prodserver2of2" >> Procfile
```

## 7. Обновление requirements.txt

```bash
# Добавляем uvicorn в dependencies
echo "uvicorn>=0.15.0" >> requirements.txt
```

## 8. Развертывание и проверка

```bash
# Коммит и деплой изменений
git add run.py middleware.py Procfile requirements.txt
git commit -m "Add custom CORS middleware and runner"
git push heroku main
```

```bash
# Проверка CORS с помощью curl
curl -v -X OPTIONS -H "Origin: https://gregory-ch.github.io" https://belabeu-e7061ee8ef78.herokuapp.com/demo
```

## 9. Финальное решение - полная версия run.py

Финальное решение включает в себя:
- Кастомный скрипт run.py, который запускает приложение
- Специальный middleware для обработки OPTIONS запросов
- Ограничение CORS только для определенных доменов
- Запуск таймаут-воркера, как в original prodserver

```bash
# Отправляем финальные изменения
git add run.py
git commit -m "Restrict CORS to specific origin for better security"
git push heroku main
```

```bash
# Проверяем работу CORS
curl -v -X OPTIONS -H "Origin: https://gregory-ch.github.io" https://belabeu-e7061ee8ef78.herokuapp.com/demo
``` 