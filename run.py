import os
import sys
import asyncio
import uvicorn
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.responses import Response, JSONResponse
from starlette.middleware.cors import CORSMiddleware
import httpx

# Домены, для которых разрешаем CORS
ALLOWED_ORIGINS = ["https://gregory-ch.github.io"]

# URL оригинального сервера oTree (localhost)
OTREE_SERVER = "http://127.0.0.1:8001"

# Асинхронная функция для проксирования запросов
async def proxy_view(request):
    # Получаем путь запроса
    path = request.url.path
    
    # Если это OPTIONS запрос, возвращаем CORS-заголовки напрямую
    if request.method == "OPTIONS":
        return Response(
            content="",
            status_code=200,
            headers={
                "Access-Control-Allow-Origin": request.headers.get("origin", ALLOWED_ORIGINS[0]),
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                "Access-Control-Allow-Headers": "*",
                "Access-Control-Allow-Credentials": "true",
                "Access-Control-Max-Age": "1728000",
            }
        )
    
    # Только для API запросов добавляем CORS
    is_api_request = not path.startswith("/static/") and not path.endswith((".css", ".js", ".ico", ".png", ".jpg"))
    
    # Перенаправляем запрос на оригинальный сервер oTree
    async with httpx.AsyncClient() as client:
        otree_url = f"{OTREE_SERVER}{path}"
        if request.query_params:
            otree_url += f"?{request.query_params}"
        
        # Копируем все заголовки из оригинального запроса
        headers = dict(request.headers)
        
        # Получаем тело запроса
        body = await request.body()
        
        # Отправляем запрос на оригинальный сервер
        otree_response = await client.request(
            method=request.method,
            url=otree_url,
            headers=headers,
            content=body
        )
        
        # Создаем ответ с данными от оригинального сервера
        headers = dict(otree_response.headers)
        
        # Если это API запрос, добавляем CORS заголовки
        if is_api_request:
            headers["Access-Control-Allow-Origin"] = request.headers.get("origin", ALLOWED_ORIGINS[0])
            headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
            headers["Access-Control-Allow-Headers"] = "*"
            headers["Access-Control-Allow-Credentials"] = "true"
        
        return Response(
            content=otree_response.content,
            status_code=otree_response.status_code,
            headers=headers
        )

# Создаем Starlette приложение с правильной обработкой всех маршрутов
app = Starlette(
    routes=[
        Route("/{path:path}", proxy_view, methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"]),
    ]
)

# Запускаем основной сервер oTree в отдельном процессе
import subprocess
import time

def main():
    # Получаем порт из переменных окружения или аргументов
    heroku_port = int(os.environ.get("PORT", 8000))
    internal_port = 8001  # Внутренний порт для oTree
    
    # Запускаем timeoutsubprocess для обработки таймаутов
    subprocess.Popen(
        ['otree', 'timeoutsubprocess', str(internal_port)],
        env=os.environ.copy()
    )
    
    # Запускаем оригинальный prodserver на другом порту
    otree_process = subprocess.Popen(
        ["otree", "prodserver1of2", str(internal_port)],
        env=os.environ.copy()
    )
    
    # Даем время на запуск oTree
    print(f"Starting oTree server on port {internal_port}...")
    time.sleep(3)
    
    # Запускаем наш CORS прокси на порту Heroku
    print(f"Starting CORS proxy on port {heroku_port}, forwarding to {OTREE_SERVER}")
    uvicorn.run(app, host="0.0.0.0", port=heroku_port)

if __name__ == "__main__":
    main() 