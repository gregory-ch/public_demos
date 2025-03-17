import os
from otree.asgi import app
from starlette.middleware.cors import CORSMiddleware

# Полностью расширенная конфигурация CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Разрешаем запросы с любого домена для отладки
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=1728000
)

# Убедимся, что приложение доступно через стандартную переменную
application = app 