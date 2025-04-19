import os
import sys
import subprocess

# Запускаем стандартный oTree server с настройкой CORS через переменные окружения
if __name__ == "__main__":
    # Получаем порт из переменных окружения (для Heroku)
    port = os.environ.get('PORT', '8000')
    
    # Запускаем timeoutsubprocess (как в prodserver1of2)
    subprocess.Popen(
        ['otree', 'timeoutsubprocess', str(port)], 
        env=os.environ.copy()
    )
    
    print('Running standard oTree prodserver with CORS configured through Heroku reverse proxy')
    
    # Запускаем оригинальный prodserver
    os.system(f"otree prodserver1of2") 