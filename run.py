#!/usr/bin/env python
import os
import logging
import subprocess
import otree.asgi
import otree.settings
from otree.cli.prodserver1of2 import run_asgi_server, get_addr_port
from starlette.staticfiles import StaticFiles
from starlette.responses import Response
from starlette.applications import Starlette
from starlette.routing import Mount
from starlette.types import ASGIApp, Receive, Scope, Send
from otree.common2 import OTreeStaticFiles, static_files_app as original_static_app
import importlib.util
import uvicorn
import asyncio

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='[OTREE-CORS] %(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('otree_cors')
logger.info("=== Starting oTree with CORS support ===")

# Get allowed domain for CORS from environment variables
CORS_ALLOW_ORIGIN = os.environ.get('CORS_ALLOW_ORIGIN', 'https://gregory-ch.github.io')
logger.info(f"CORS allowed origin: {CORS_ALLOW_ORIGIN}")

class CORSStaticFiles(OTreeStaticFiles):
    """
    Расширенная версия OTreeStaticFiles с поддержкой CORS и обработкой OPTIONS запросов
    """
    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            return await super().__call__(scope, receive, send)
            
        method = scope.get("method", "")
        path = scope.get("path", "")
        
        # Handle OPTIONS requests directly
        if method == "OPTIONS":
            logger.info(f"CORSStaticFiles: Handling OPTIONS request for {path}")
            response = Response(
                content="",
                status_code=200,
                headers={
                    "Access-Control-Allow-Origin": CORS_ALLOW_ORIGIN,
                    "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                    "Access-Control-Allow-Headers": "X-CSRFToken, X-Requested-With, Content-Type, Accept, otree-rest-key, otree-rest",
                    "Access-Control-Allow-Credentials": "true",
                    "Access-Control-Max-Age": "1728000",
                    "Access-Control-Expose-Headers": "Allow",
                }
            )
            return await response(scope, receive, send)
        
        # For other requests, add CORS headers after StaticFiles processing
        async def send_with_cors(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                
                # Add CORS headers
                cors_headers = [
                    (b"access-control-allow-origin", CORS_ALLOW_ORIGIN.encode()),
                    (b"access-control-allow-methods", b"GET, POST, PUT, DELETE, OPTIONS"),
                    (b"access-control-allow-headers", b"X-CSRFToken, X-Requested-With, Content-Type, Accept, otree-rest-key, otree-rest"),
                    (b"access-control-allow-credentials", b"true"),
                    (b"access-control-expose-headers", b"Allow"),
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
        
        return await super().__call__(scope, receive, send_with_cors)

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
        
        # Перехватываем OPTIONS запросы к любым путям, включая корневой
        if method == "OPTIONS":
            logger.info(f"RootApp: Handling OPTIONS request for {path}")
            response = Response(
                content="",
                status_code=200,
                headers={
                    "Access-Control-Allow-Origin": CORS_ALLOW_ORIGIN,
                    "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                    "Access-Control-Allow-Headers": "X-CSRFToken, X-Requested-With, Content-Type, Accept, otree-rest-key, otree-rest",
                    "Access-Control-Allow-Credentials": "true",
                    "Access-Control-Max-Age": "1728000",
                    "Access-Control-Expose-Headers": "Allow",
                }
            )
            return await response(scope, receive, send)
        
        # Перенаправляем запросы к статическим файлам на наше отдельное приложение,
        # минуя middleware oTree с блокировками
        if path.startswith("/static/"):
            logger.info(f"RootApp: Routing static request {path} to separate static app")
            # Преобразуем путь к формату, который ожидает static_files_app
            # Удаляем '/static/' из начала пути
            modified_scope = dict(scope)
            modified_scope["path"] = path[7:]  # Remove '/static/' prefix
            return await self.static_app(modified_scope, receive, send)
        # # Все остальные запросы идут к основному приложению oTree
        # return await self.otree_app(scope, receive, send)
        # 3) для всех остальных (GET /demo/dsst и т.д.):
        async def send_with_cors(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                cors_headers = [
                    (b"access-control-allow-origin", CORS_ALLOW_ORIGIN.encode()),
                    (b"access-control-allow-methods", b"GET, POST, PUT, DELETE, OPTIONS"),
                    (b"access-control-allow-headers", b"X-CSRFToken, X-Requested-With, Content-Type, Accept, otree-rest-key, otree-rest"),
                    (b"access-control-allow-credentials", b"true"),
                    (b"access-control-expose-headers", b"Allow"),
                ]
                for new_header in cors_headers:
                    for i, (name, _) in enumerate(headers):
                        if name.lower() == new_header[0].lower():
                            headers[i] = new_header
                            break
                    else:
                        headers.append(new_header)
                message["headers"] = headers
            await send(message)

        return await self.otree_app(scope, receive, send_with_cors)

def run_otree_with_cors():
    """
    Run oTree with CORS support by safely integrating CORS headers at initialization time
    """
    # Patch OTreeStarlette.build_middleware_stack for normal requests
    original_build_middleware = otree.asgi.OTreeStarlette.build_middleware_stack
    
    # Create a new build_middleware_stack method that adds CORS handling
    def build_middleware_with_cors(self):
        # Call the original method to get the middleware stack
        app = original_build_middleware(self)
        
        # Create an outer middleware that handles OPTIONS and adds CORS headers
        async def cors_middleware(scope, receive, send):
            if scope["type"] != "http":
                return await app(scope, receive, send)
                
            method = scope.get("method", "")
            path = scope.get("path", "")
            
            # Handle OPTIONS requests directly
            if method == "OPTIONS" and not path.startswith('/static/'):
                logger.info(f"CORS middleware: Handling OPTIONS for {path}")
                response = Response(
                    content="",
                    status_code=200,
                    headers={
                        "Access-Control-Allow-Origin": CORS_ALLOW_ORIGIN,
                        "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                        "Access-Control-Allow-Headers": "X-CSRFToken, X-Requested-With, Content-Type, Accept, otree-rest-key, otree-rest",
                        "Access-Control-Allow-Credentials": "true",
                        "Access-Control-Max-Age": "1728000",
                        "Access-Control-Expose-Headers": "Allow",
                    }
                )
                return await response(scope, receive, send)
            
            # For regular requests, add CORS headers to the response
            async def send_with_cors(message):
                if message["type"] == "http.response.start":
                    headers = list(message.get("headers", []))
                    # and not path.startswith('/static/'):
                    # Add CORS headers
                    cors_headers = [
                        (b"access-control-allow-origin", CORS_ALLOW_ORIGIN.encode()),
                        (b"access-control-allow-methods", b"GET, POST, PUT, DELETE, OPTIONS"),
                        (b"access-control-allow-headers", b"X-CSRFToken, X-Requested-With, Content-Type, Accept, otree-rest-key, otree-rest"),
                        (b"access-control-allow-credentials", b"true"),
                        (b"access-control-expose-headers", b"Allow"),
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
            
            return await app(scope, receive, send_with_cors)
        
        return cors_middleware
    
    # Replace the original build_middleware_stack method with our patched version
    otree.asgi.OTreeStarlette.build_middleware_stack = build_middleware_with_cors
    logger.info("Patched OTreeStarlette.build_middleware_stack with CORS support")
    
    # Now let's initialize oTree itself and get the app instance
    from otree.asgi import app as otree_app
    
    # Вместо создания нового экземпляра, используем оригинальный static_files_app 
    # и оборачиваем его в наш CORS обработчик
    original_static_call = original_static_app.__call__
    
    async def static_app_with_cors(scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            return await original_static_call(scope, receive, send)
            
        method = scope.get("method", "")
        
        # Handle OPTIONS requests directly
        if method == "OPTIONS":
            logger.info(f"CORSStaticFiles: Handling OPTIONS request for path")
            response = Response(
                content="",
                status_code=200,
                headers={
                    "Access-Control-Allow-Origin": CORS_ALLOW_ORIGIN,
                    "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                    "Access-Control-Allow-Headers": "X-CSRFToken, X-Requested-With, Content-Type, Accept, otree-rest-key, otree-rest",
                    "Access-Control-Allow-Credentials": "true",
                    "Access-Control-Max-Age": "1728000",
                    "Access-Control-Expose-Headers": "Allow",
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
                    (b"access-control-allow-headers", b"X-CSRFToken, X-Requested-With, Content-Type, Accept, otree-rest-key, otree-rest"),
                    (b"access-control-allow-credentials", b"true"),
                    (b"access-control-expose-headers", b"Allow"),
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
    
    # Create a root application that routes requests appropriately
    root_app = RootApp(otree_app, original_static_app)
    
    # Get the port from the environment
    addr, port = get_addr_port(os.environ.get('PORT'))
    logger.info(f"Starting server on {addr}:{port}")
    
    # Start the timeout subprocess
    subprocess.Popen(
        ['otree', 'timeoutsubprocess', str(port)], 
        env=os.environ.copy()
    )
    
    # Configure and run Uvicorn directly instead of using run_asgi_server
    logger.info("Starting Uvicorn with custom app")
    config = uvicorn.Config(
        app=root_app,
        host=addr,
        port=int(port),
        log_level="info",
        log_config=None,
        workers=1,
        ws='websockets',
    )
    server = uvicorn.Server(config=config)
    server.run()

if __name__ == "__main__":
    run_otree_with_cors() 