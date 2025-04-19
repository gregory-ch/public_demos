#!/usr/bin/env python
import os
import sys
import logging
import subprocess

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='[OTREE-CORS] %(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('otree_cors')
logger.info("=== Starting oTree with CORS support ===")

# Получаем разрешенный домен для CORS из переменных окружения
CORS_ALLOW_ORIGIN = os.environ.get('CORS_ALLOW_ORIGIN', 'https://gregory-ch.github.io')
logger.info(f"CORS allowed origin: {CORS_ALLOW_ORIGIN}")

# Патчим функции oTree перед импортом
import types

def patch_otree_routes():
    """
    Патчим маршруты oTree для добавления CORS заголовков
    и обработки OPTIONS запросов
    """
    logger.info("Patching oTree HTTP handlers for CORS support")
    
    # Импортируем модуль маршрутов только после патча
    import otree.urls
    from starlette.responses import PlainTextResponse
    
    # Сохраняем оригинальную функцию add_route
    original_add_route = otree.urls.routes.add_route
    
    # Создаем обработчик для OPTIONS запросов
    async def options_handler(request):
        """Обработчик OPTIONS запросов для CORS preflight"""
        headers = {
            "Access-Control-Allow-Origin": CORS_ALLOW_ORIGIN,
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Max-Age": "1728000",
        }
        return PlainTextResponse("", headers=headers)

    # Добавляем обработчик OPTIONS запросов
    otree.urls.routes.add_route("OPTIONS", "/", options_handler)
    otree.urls.routes.add_route("OPTIONS", "/{path:path}", options_handler)
    
    logger.info("Added OPTIONS handlers")

# Запуск стандартного prodserver
def run_standard_prodserver():
    """Запуск стандартного oTree prodserver"""
    
    # Патчим маршруты перед запуском
    patch_otree_routes()
    
    # Теперь запускаем стандартный prodserver
    logger.info("Starting standard oTree prodserver")
    port = os.environ.get('PORT', '8000')
    
    # Используем напрямую код из prodserver1of2.py
    from otree.cli.prodserver1of2 import run_uvicorn, print_function
    
    # Запускаем timeoutsubprocess
    subprocess.Popen(
        ['otree', 'timeoutsubprocess', str(port)], 
        env=os.environ.copy()
    )
    
    # Запускаем uvicorn с standard app
    print_function('Running prodserver with CORS patch')
    run_uvicorn('0.0.0.0', port, is_devserver=False)

if __name__ == "__main__":
    run_standard_prodserver() 