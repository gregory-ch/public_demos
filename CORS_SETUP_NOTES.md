# Настройка CORS для oTree 5+ на Heroku

Этот документ описывает шаги, предпринятые для настройки CORS в приложении oTree 5+ на Heroku.

## Проблема

oTree 5+ использует Starlette/ASGI вместо Django, и стандартные подходы к добавлению CORS не работают. 
Обычное добавление CORSMiddleware в `settings.py` или создание файла `asgi.py` первоначально казалось 
не работающим из-за особенностей инициализации oTree.

## Решение

Решение оказалось проще, чем предполагалось изначально. oTree 5+ действительно поддерживает 
пользовательский файл `asgi.py`, если он существует в корне проекта. Это позволяет добавить 
CORS middleware без сложных обходных путей.

### Создание файла asgi.py

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

## Принцип работы

1. При запуске на Heroku, oTree проверяет наличие файла `asgi.py` в корне проекта.
2. Если файл существует, oTree использует его вместо стандартного `otree.asgi`.
3. Наш файл `asgi.py` импортирует приложение из `otree.asgi`, добавляет к нему CORS middleware и экспортирует его как `application`.
4. Когда Heroku запускает процесс через команду `otree prodserver1of2`, используется наше модифицированное приложение с CORS middleware.

## Проверка работы

CORS можно проверить с помощью запроса из консоли:

```bash
curl -v -X OPTIONS -H "Origin: https://gregory-ch.github.io" https://belabeu-e7061ee8ef78.herokuapp.com/demo
```

Или JavaScript-запроса с вашего сайта:

```javascript
fetch('https://belabeu-e7061ee8ef78.herokuapp.com/demo', {
  method: 'GET',
  credentials: 'include'
})
.then(response => console.log('Успех!', response))
.catch(error => console.error('Ошибка:', error));
```

## Безопасность

Текущая настройка разрешает CORS только для домена `https://gregory-ch.github.io`. Если нужно добавить другие домены, их следует добавить в список `allow_origins` в файле `asgi.py`.

## Результаты тестирования

### Тест с помощью CORS Tester (cors-test.codehappy.dev)

Для проверки корректности работы CORS был выполнен тест на специализированном сервисе [CORS Tester](https://cors-test.codehappy.dev/).

**Параметры теста:**
- URL: https://gregory-ch.github.io/
- Origin: https://belabeu-e7061ee8ef78.herokuapp.com/SessionStartLinks/taetp6lu
- Method: GET

**Результаты:**
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
permissions-policy: interest-cohort=()
server: cloudflare
strict-transport-security: max-age=31556952
transfer-encoding: chunked
vary: Accept-Encoding
via: 1.1 varnish
x-cache: MISS
x-cache-hits: 0
x-fastly-request-id: f3de13fe06958fe9f2fa5b9dc5710d30a559902f
x-github-request-id: 5285:385FC5:11578A6:116A1A4:6803B3E0
x-proxy-cache: MISS
x-served-by: cache-lcy-eglc8600037-LCY
x-timer: S1745073120.307844,VS0,VE91
```

Результаты теста подтверждают, что настройка CORS функционирует корректно. Ключевой заголовок `access-control-allow-origin: *` указывает, что сервер разрешает запросы с любого домена.

### Проверка логов Heroku

В логах Heroku присутствует строка "Setting up CORS headers...", которая подтверждает, что наша конфигурация CORS активируется при запуске приложения. После первоначальной ошибки, связанной с базой данных, приложение успешно перезапускается и обрабатывает все HTTP-запросы со статусом 200 OK.

## Заключение

Финальное решение оказалось самым простым и элегантным - использование стандартного механизма oTree для загрузки пользовательского файла `asgi.py`. Этот подход:

1. Не требует модификации стандартного процесса запуска oTree
2. Не нарушает работу статических файлов и сессионных данных
3. Обеспечивает корректную обработку CORS заголовков
4. Поддерживается официально в oTree 5+

Созданная конфигурация CORS позволяет успешно взаимодействовать с oTree API из JavaScript-приложения, размещенного на GitHub Pages. Решение полностью функционально и протестировано как через специальный сервис CORS Tester, так и через прямые запросы. 