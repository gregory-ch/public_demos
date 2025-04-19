#!/usr/bin/env python
import os
import sys
import subprocess
import logging

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='[CORS-SERVER] %(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('cors_server')
logger.info("=== Custom CORS prodserver starting ===")

# Разрешенные домены для CORS
CORS_ALLOW_ORIGIN = os.environ.get('CORS_ALLOW_ORIGIN', 'https://gregory-ch.github.io')
logger.info(f"CORS allowed origin: {CORS_ALLOW_ORIGIN}")

def handle_options_requests():
    # Запускаем отдельный HTTP-сервер только для обработки OPTIONS запросов
    from http.server import HTTPServer, BaseHTTPRequestHandler
    import threading

    class OptionsHandler(BaseHTTPRequestHandler):
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
            logger.info(f"Responded to OPTIONS request with 200 OK: {self.path}")

        def do_GET(self):
            # Просто перенаправляем все остальные запросы на основной сервер
            self.send_response(301)
            self.send_header('Location', f'http://127.0.0.1:{os.environ.get("PORT", "8000")}{self.path}')
            self.end_headers()

    # Получаем порт для OPTIONS сервера, делаем его на 1 больше чем основной порт
    main_port = int(os.environ.get('PORT', '8000'))
    options_port = main_port  # Используем тот же порт

    # Запускаем OPTIONS сервер в отдельном потоке
    def run_options_server():
        try:
            server = HTTPServer(('0.0.0.0', options_port), OptionsHandler)
            logger.info(f"Starting OPTIONS handler on port {options_port}")
            server.serve_forever()
        except Exception as e:
            logger.error(f"Error starting OPTIONS server: {e}")

    # Запускаем отдельный сервер для OPTIONS
    thread = threading.Thread(target=run_options_server)
    thread.daemon = True
    thread.start()

def run_standard_prodserver():
    logger.info("Running standard oTree prodserver")
    port = os.environ.get('PORT', '8000')
    
    # Модифицируем otree.settings для включения CORS (это не сработает в продакшн)
    # import otree.settings
    # otree.settings.CORS_ALLOW_ALL = True
    
    # Запускаем стандартную команду prodserver
    from otree.cli.prodserver1of2 import Command
    command = Command()
    command.handle(addrport=f"0.0.0.0:{port}")

def main():
    # Настраиваем обработку OPTIONS запросов
    handle_options_requests()
    
    # Запускаем стандартный prodserver
    run_standard_prodserver()

if __name__ == "__main__":
    main() 