import os
from otree.asgi import app as otree_app
from starlette.middleware.cors import CORSMiddleware

# Добавляем CORS middleware к приложению oTree
app = otree_app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Разрешаем запросы с любого домена для отладки
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=1728000
)

# Это важно для Heroku - приложение должно быть доступно как 'application'
application = app 