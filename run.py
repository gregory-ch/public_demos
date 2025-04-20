#!/usr/bin/env python
import os
import logging
import subprocess
import otree.asgi
from otree.cli.prodserver1of2 import run_asgi_server, get_addr_port
from starlette.staticfiles import StaticFiles
from starlette.responses import Response
from starlette.applications import Starlette
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

def run_otree_with_cors():
    """
    Run oTree with CORS support by safely integrating CORS headers at initialization time
    """
    # IMPORTANT: We need to do all imports inside this function to ensure
    # we can monkey-patch modules before they're used by oTree

    
    # First, patch the StaticFiles class to add CORS support
    
    # Save the original StaticFiles.__call__ method
    original_staticfiles_call = StaticFiles.__call__
    
    # Create a new __call__ method that adds CORS headers
    async def cors_staticfiles_call(self, scope, receive, send):
        if scope["type"] != "http":
            return await original_staticfiles_call(self, scope, receive, send)
            
        method = scope.get("method", "")
        path = scope.get("path", "")
        
        # Handle OPTIONS requests directly
        if method == "OPTIONS":
            logger.info(f"StaticFiles: Handling OPTIONS request for {path}")
            response = Response(
                content="",
                status_code=200,
                headers={
                    "Access-Control-Allow-Origin": CORS_ALLOW_ORIGIN,
                    "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                    "Access-Control-Allow-Headers": "*",
                    "Access-Control-Allow-Credentials": "true",
                    "Access-Control-Max-Age": "1728000",
                }
            )
            return await response(scope, receive, send)
        
        # For regular requests, add CORS headers to the response
        async def send_with_cors(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                
                # Add CORS headers
                cors_headers = [
                    (b"access-control-allow-origin", CORS_ALLOW_ORIGIN.encode()),
                    (b"access-control-allow-methods", b"GET, POST, PUT, DELETE, OPTIONS"),
                    (b"access-control-allow-headers", b"*"),
                    (b"access-control-allow-credentials", b"true"),
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
        
        return await original_staticfiles_call(self, scope, receive, send_with_cors)
    
    # Replace the original __call__ method with our patched version
    StaticFiles.__call__ = cors_staticfiles_call
    logger.info("Patched StaticFiles.__call__ with CORS support")
    
    # Now, patch the OTreeStarlette to add CORS handling for non-static routes
    # We need to modify the class before it's instantiated in asgi.py
    
    # Save the original build_middleware_stack method
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
                        "Access-Control-Allow-Headers": "*",
                        "Access-Control-Allow-Credentials": "true",
                        "Access-Control-Max-Age": "1728000",
                    }
                )
                return await response(scope, receive, send)
            
            # For regular requests, add CORS headers to the response
            async def send_with_cors(message):
                if message["type"] == "http.response.start" and not path.startswith('/static/'):
                    headers = list(message.get("headers", []))
                    
                    # Add CORS headers
                    cors_headers = [
                        (b"access-control-allow-origin", CORS_ALLOW_ORIGIN.encode()),
                        (b"access-control-allow-methods", b"GET, POST, PUT, DELETE, OPTIONS"),
                        (b"access-control-allow-headers", b"*"),
                        (b"access-control-allow-credentials", b"true"),
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
    
    # Now let oTree initialize itself with our patches in place
    logger.info("Starting oTree with CORS support at initialization time")
    
    # Запускаем сервер напрямую, как это делает prodserver1of2
    logger.info("Starting ASGI server directly")
    
    # Получаем адрес и порт
    addr, port = get_addr_port(os.environ.get('PORT'))
    logger.info(f"Server will run on {addr}:{port}")
    
    # Запускаем таймаут процесс, как это делает prodserver1of2
    subprocess.Popen(
        ['otree', 'timeoutsubprocess', str(port)], 
        env=os.environ.copy()
    )
    
    # Запускаем ASGI сервер
    run_asgi_server(addr, port, is_devserver=False)

if __name__ == "__main__":
    run_otree_with_cors() 