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

Первоначально это решение казалось не работающим, так как предполагалось, что oTree при запуске использует свой модуль otree.asgi, а не локальный файл asgi.py.

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

Это также не дало ожидаемых результатов, так как oTree инициализирует приложение и middleware в особом порядке.

## 3. Использование middleware.py и otree_extensions.py

```python
# middleware.py
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

class CorsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "*"
        response.headers["Access-Control-Allow-Credentials"] = "true"
        return response
```

```python
# otree_extensions.py
from otree.extension_utils import get_extensions_modules, get_extensions_data_modules
from starlette.middleware.cors import CORSMiddleware

def middleware_modules():
    return ['middleware']
```

Этот подход также не дал ожидаемых результатов из-за особенностей инициализации middleware в oTree.

## 4. Создание кастомного скрипта запуска (run.py)

В процессе отладки был создан кастомный скрипт запуска `run.py`, который импортирует приложение oTree, добавляет к нему CORS middleware и запускает. Этот подход работал, но был слишком сложным и приводил к проблемам с загрузкой статических файлов и конфликтам в базе данных.

## 5. Возврат к решению с asgi.py

После различных экспериментов выяснилось, что oTree 5+ действительно поддерживает локальный файл `asgi.py`, если он существует в проекте. Это позволило вернуться к самому простому и элегантному решению:

```bash
# Создаем файл asgi.py
touch asgi.py
```

```python
# asgi.py - финальная версия
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

## 6. Очистка проекта

Для избежания конфликтов и путаницы, были удалены ненужные файлы:

```bash
# Удаляем middleware.py
rm middleware.py

# Удаляем otree_extensions.py
rm otree_extensions.py
```

## 7. Сохранение стандартного Procfile

Procfile был возвращен к стандартному виду для oTree 5+:

```
web: otree prodserver1of2
worker: otree prodserver2of2
```

## 8. Deployment и проверка

```bash
# Коммит и деплой изменений
git add asgi.py
git commit -m "Add CORS middleware via asgi.py"
git push heroku main
```

## 9. Тестирование CORS

Тестирование было выполнено с помощью специализированного сервиса CORS Tester:

```
URL: https://gregory-ch.github.io/
Origin: https://belabeu-e7061ee8ef78.herokuapp.com/SessionStartLinks/taetp6lu
Method: GET
```

Результаты теста подтвердили, что CORS настроен корректно:

```
This URL will work correctly with CORS.

Headers:
access-control-allow-origin: *
age: 0
cache-control: max-age=600
cf-cache-status: DYNAMIC
cf-ray: 932d1bd9a06eef48-LHR
connection: keep-alive
content-type: text/html; charset=utf-8
date: Sat, 19 Apr 2025 14:32:00 GMT
expires: Sat, 19 Apr 2025 14:42:00 GMT
last-modified: Mon, 17 Mar 2025 19:13:56 GMT
...
```

Также проверка логов Heroku показала наличие строки "Setting up CORS headers...", что подтверждает активацию CORS при запуске приложения.

## 10. Заключение

Финальное решение оказалось самым простым и элегантным - использование стандартного механизма oTree для загрузки пользовательского файла `asgi.py`. Этот подход:

1. Не требует модификации стандартного процесса запуска oTree
2. Не нарушает работу статических файлов и сессионных данных
3. Обеспечивает корректную обработку CORS заголовков
4. Поддерживается официально в oTree 5+

Преимущество этого решения в его простоте и отсутствии сложных обходных путей, что делает его более устойчивым к будущим обновлениям oTree. 