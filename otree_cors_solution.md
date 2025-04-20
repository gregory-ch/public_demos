# Реализация поддержки CORS в oTree

## Введение

Cross-Origin Resource Sharing (CORS) - это механизм, который позволяет веб-страницам запрашивать ресурсы с других доменов. В стандартной реализации oTree отсутствует полноценная поддержка CORS, что создает проблемы при интеграции с внешними клиентскими приложениями, особенно при использовании современных JavaScript-фреймворков.

Данный документ описывает реализацию CORS-поддержки для oTree-приложений.

## Проблемы при интеграции CORS в oTree

При попытке интеграции CORS в oTree возникает ряд сложностей:

1. **Асинхронная архитектура ASGI**: oTree использует ASGI (Asynchronous Server Gateway Interface), где обработка запросов происходит асинхронно, что требует особого подхода к добавлению CORS-заголовков.

2. **Многоуровневая middleware**: В oTree существует сложная структура middleware, порядок которых критически важен.

3. **Специфика обработки статических файлов**: Статические файлы в oTree обрабатываются особым образом через `OTreeStaticFiles` класс, который ищет файлы в нескольких местах.

4. **Блокировки при параллельных запросах**: oTree использует асинхронные блокировки (`lock2` в `CommitTransactionMiddleware`) для синхронизации доступа к базе данных, что вызывает конфликты при параллельной обработке запросов к статическим файлам.

## Решение

Наше решение включает следующие компоненты:

### 1. Изолирование статических файлов от middleware oTree

Мы создали отдельный маршрут для обработки статических файлов, который позволяет обойти middleware oTree, вызывающие конфликты с асинхронными блокировками:

```python
class RootApp:
    """
    Корневое приложение, которое перенаправляет запросы к статическим файлам 
    и другие запросы по разным путям обработки
    """
    def __init__(self, otree_app: ASGIApp, static_app: ASGIApp):
        self.otree_app = otree_app
        self.static_app = static_app
    
    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            return await self.otree_app(scope, receive, send)
            
        path = scope["path"]
        method = scope.get("method", "")
        
        # Перехватываем OPTIONS запросы
        if method == "OPTIONS":
            response = Response(
                content="",
                status_code=200,
                headers={
                    "Access-Control-Allow-Origin": CORS_ALLOW_ORIGIN,
                    "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                    "Access-Control-Allow-Headers": "*",
                    "Access-Control-Allow-Credentials": "true",
                    "Access-Control-Max-Age": "1728000",
                }
            )
            return await response(scope, receive, send)
        
        # Перенаправляем запросы к статическим файлам
        if path.startswith("/static/"):
            modified_scope = dict(scope)
            modified_scope["path"] = path[7:]  # Удаляем '/static/' из начала пути
            return await self.static_app(modified_scope, receive, send)
        
        # Остальные запросы идут к основному приложению oTree
        return await self.otree_app(scope, receive, send)
```

### 2. Использование оригинального oTree обработчика статических файлов

Вместо создания собственного обработчика статических файлов, мы используем оригинальный `static_files_app` из oTree, но добавляем к нему функциональность для обработки CORS:

```python
# Вместо создания нового экземпляра, используем оригинальный static_files_app 
# и оборачиваем его в наш CORS обработчик
original_static_call = original_static_app.__call__

async def static_app_with_cors(scope: Scope, receive: Receive, send: Send) -> None:
    if scope["type"] != "http":
        return await original_static_call(scope, receive, send)
        
    method = scope.get("method", "")
    
    # Handle OPTIONS requests directly
    if method == "OPTIONS":
        response = Response(
            content="",
            status_code=200,
            headers={
                "Access-Control-Allow-Origin": CORS_ALLOW_ORIGIN,
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                "Access-Control-Allow-Headers": "*",
                "Access-Control-Allow-Credentials": "true",
                "Access-Control-Max-Age": "1728000",
            }
        )
        return await response(scope, receive, send)
    
    # For other requests, add CORS headers
    async def send_with_cors(message):
        if message["type"] == "http.response.start":
            headers = list(message.get("headers", []))
            
            # Add CORS headers
            cors_headers = [
                (b"access-control-allow-origin", CORS_ALLOW_ORIGIN.encode()),
                (b"access-control-allow-methods", b"GET, POST, PUT, DELETE, OPTIONS"),
                (b"access-control-allow-headers", b"*"),
                (b"access-control-allow-credentials", b"true"),
            ]
            
            # Add or replace headers
            for new_header in cors_headers:
                exists = False
                for i, (name, _) in enumerate(headers):
                    if name.lower() == new_header[0].lower():
                        exists = True
                        headers[i] = new_header
                        break
                if not exists:
                    headers.append(new_header)
            
            message["headers"] = headers
        
        await send(message)
    
    # Вызываем оригинальный обработчик, но с модифицированным send
    return await original_static_call(scope, receive, send_with_cors)

# Заменяем метод __call__ у original_static_app
original_static_app.__call__ = static_app_with_cors
```

Этот подход позволяет сохранить всю логику oTree для поиска статических файлов, но добавляет CORS-заголовки к ответам.

### 3. Обработка OPTIONS-запросов

Мы перехватываем все OPTIONS-запросы на ранней стадии обработки, чтобы предотвратить их попадание в middleware oTree, которые могут отклонить такие запросы:

```python
# Перехватываем OPTIONS запросы к любым путям, включая корневой
if method == "OPTIONS":
    response = Response(
        content="",
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": CORS_ALLOW_ORIGIN,
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Max-Age": "1728000",
        }
    )
    return await response(scope, receive, send)
```

### 4. Монопатчинг middleware oTree

Для обычных (не-статических) запросов мы монопатчим middleware stack oTree, чтобы добавить CORS-заголовки:

```python
# Patch OTreeStarlette.build_middleware_stack для обычных запросов
original_build_middleware = otree.asgi.OTreeStarlette.build_middleware_stack

def build_middleware_with_cors(self):
    # Вызываем оригинальный метод
    app = original_build_middleware(self)
    
    # Создаем внешний middleware для обработки CORS
    async def cors_middleware(scope, receive, send):
        # ... логика добавления CORS-заголовков ...
    
    return cors_middleware

# Заменяем оригинальный метод
otree.asgi.OTreeStarlette.build_middleware_stack = build_middleware_with_cors
```

## Ключевые особенности реализации

1. **Коррекция путей**: Для запросов к статическим файлам мы удаляем префикс `/static/` перед передачей в обработчик oTree.

2. **Обратная совместимость**: Мы используем оригинальные компоненты oTree везде, где это возможно, чтобы сохранить обратную совместимость.

3. **Обход блокировок**: Путем перенаправления запросов к статическим файлам мимо основного middleware stack oTree, мы избегаем конфликтов с асинхронными блокировками.

4. **Настройка CORS-заголовков**: CORS-заголовки настраиваются через переменную окружения `CORS_ALLOW_ORIGIN`.

## Ограничения и возможные улучшения

1. **Конфигурация CORS**: В текущей реализации поддерживается только одно значение для `Access-Control-Allow-Origin`. Можно расширить функциональность для поддержки нескольких доменов.

2. **Производительность**: При интенсивном использовании статических файлов можно реализовать кэширование ответов.

3. **Дополнительные заголовки**: Текущая реализация добавляет стандартный набор CORS-заголовков. Можно добавить поддержку дополнительных заголовков.

## Заключение

Данная реализация CORS для oTree успешно решает проблемы межсайтовых запросов, позволяя использовать oTree как backend API для внешних клиентских приложений. Ключевыми особенностями являются корректная обработка OPTIONS-запросов и бесконфликтное добавление CORS-заголовков к ответам, включая ответы со статическими файлами. 