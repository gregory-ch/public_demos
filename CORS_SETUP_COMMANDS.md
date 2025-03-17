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
# run.py - первая версия
import os
import sys
import uvicorn
from otree.asgi import app
from middleware import CorsASGIMiddleware

# Оборачиваем приложение oTree в нашу CORS middleware
app_with_cors = CorsASGIMiddleware(app)

if __name__ == "__main__":
    # Запускаем приложение с нашей middleware
    uvicorn.run(app_with_cors, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
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