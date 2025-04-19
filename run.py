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

def run_standard_prodserver():
    """Запуск стандартного oTree prodserver с минимальными модификациями для CORS"""
    
    # Подготавливаем ASGI приложение для обработки CORS
    logger.info("Setting up CORS support for oTree")
    
    # Создаем простой HTTP-сервер для обработки OPTIONS запросов
    from http.server import HTTPServer, BaseHTTPRequestHandler
    import threading
    
    class CORSHandler(BaseHTTPRequestHandler):
        def do_OPTIONS(self):
            self.send_response(200)
            self.send_header('Access-Control-Allow-Origin', CORS_ALLOW_ORIGIN)
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', '*')
            self.send_header('Access-Control-Allow-Credentials', 'true')
            self.send_header('Access-Control-Max-Age', '1728000')
            self.send_header('Content-Type', 'text/plain')
            self.send_header('Content-Length', '0')
            self.end_headers()
    
    def run_options_server():
        # Запускаем на том же порту, что и основной сервер
        # Heroku будет перенаправлять OPTIONS запросы сюда
        port = int(os.environ.get('PORT_OPTIONS', '8001'))
        logger.info(f"Starting OPTIONS handler server on port {port}")
        try:
            server = HTTPServer(('0.0.0.0', port), CORSHandler)
            server.serve_forever()
        except Exception as e:
            logger.error(f"Error starting OPTIONS server: {e}")
    
    # Запускаем OPTIONS сервер в отдельном потоке
    options_thread = threading.Thread(target=run_options_server, daemon=True)
    options_thread.start()
    logger.info("Started OPTIONS handler in background thread")
    
    # Запускаем стандартный prodserver
    logger.info("Starting standard oTree prodserver")
    port = os.environ.get('PORT', '8000')
    
    # Используем напрямую код из prodserver1of2.py
    from otree.cli.prodserver1of2 import run_uvicorn, print_function
    
    # Запускаем timeoutsubprocess
    subprocess.Popen(
        ['otree', 'timeoutsubprocess', str(port)], 
        env=os.environ.copy()
    )
    
    # Запускаем uvicorn со standard app
    print_function('Running standard oTree prodserver')
    run_uvicorn('0.0.0.0', port, is_devserver=False)

if __name__ == "__main__":
    run_standard_prodserver() 