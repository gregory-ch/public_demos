import os
import sys
import subprocess
import logging
from uvicorn.main import Config, Server

# Импортируем приложение oTree
from otree.asgi import app
from starlette.middleware.cors import CORSMiddleware

# Добавляем CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Разрешаем запросы с любого домена для отладки
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=1728000
)

# Настраиваем логгирование
logger = logging.getLogger(__name__)
print_function = print

def main():
    # Получаем порт из переменных окружения (для Heroku)
    port = os.environ.get('PORT', '8000')
    
    # Запускаем timeoutsubprocess (как в prodserver1of2)
    subprocess.Popen(
        ['otree', 'timeoutsubprocess', str(port)], 
        env=os.environ.copy()
    )
    
    print_function('Running custom prodserver with CORS middleware')
    
    # Запускаем Uvicorn с нашим модифицированным app
    config = Config(
        app=app,  # Напрямую используем модифицированное приложение
        host='0.0.0.0',
        port=int(port),
        log_level="info",
        log_config=None,  # oTree имеет свой логгер
        workers=1,
        ws='websockets',  # websockets библиотека обрабатывает отключения автоматически
    )
    server = Server(config=config)
    server.run()

if __name__ == "__main__":
    main() 