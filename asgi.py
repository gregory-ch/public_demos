from otree.asgi import app
from starlette.middleware.cors import CORSMiddleware

# Добавляем CORS middleware к приложению oTree
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://gregory-ch.github.io"],  # Разрешаем запросы с Jekyll сайта
    allow_credentials=True,                          # Разрешаем передачу куков и credentials
    allow_methods=["*"],                             # Разрешаем все HTTP методы
    allow_headers=["*"],                             # Разрешаем все заголовки
    max_age=1728000                                  # 20 дней в секундах
)

# Экспортируем приложение для Heroku
application = app 