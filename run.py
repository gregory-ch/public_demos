#!/usr/bin/env python
import os
import sys
import logging
import importlib
import subprocess
from copy import deepcopy

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

def run_with_cors():
    """
    Creates a new instance of the oTree application with CORS middleware added
    and then runs it using uvicorn.
    """
    # Import necessary modules from oTree and Starlette
    from starlette.applications import Starlette
    from starlette.middleware import Middleware
    from starlette.responses import HTMLResponse, PlainTextResponse, Response
    from starlette.routing import Route, NoMatchFound
    
    # Import oTree specific modules without importing the app instance
    import otree.errorpage
    import otree.database
    import otree.middleware
    import otree.settings
    from otree.errorpage import OTreeServerErrorMiddleware
    from otree.patch import ExceptionMiddleware
    import otree.urls
    
    logger.info("Creating new oTree application with CORS support")
    
    # Custom CORS middleware with static file optimization
    class OptimizedCORSMiddleware:
        def __init__(self, app):
            self.app = app
        
        async def __call__(self, scope, receive, send):
            if scope["type"] != "http":
                # Pass through WebSocket and lifespan messages unchanged
                await self.app(scope, receive, send)
                return
            
            path = scope.get("path", "")
            method = scope.get("method", "")
            
            # Check if this is a static file request
            is_static = path.startswith('/static/')
            
            logger.info(f"OptimizedCORSMiddleware handling {method} request for {path}")
            
            # Handle OPTIONS requests directly
            if method == "OPTIONS":
                logger.info(f"Handling OPTIONS request for {path}")
                
                # Create a response with CORS headers
                cors_headers = {
                    "Access-Control-Allow-Origin": CORS_ALLOW_ORIGIN,
                    "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                    "Access-Control-Allow-Headers": "*",
                    "Access-Control-Allow-Credentials": "true",
                    "Access-Control-Max-Age": "1728000",
                    "Content-Type": "text/plain",
                    "Content-Length": "0"
                }
                
                # Log headers for debugging
                logger.info(f"Sending CORS headers for OPTIONS: {cors_headers}")
                
                response = PlainTextResponse("", status_code=200, headers=cors_headers)
                await response(scope, receive, send)
                return
            
            # For static files, use a simpler approach to avoid async conflicts
            if is_static:
                # For static files, we'll capture the response and add headers
                # without wrapping the send function to avoid async conflicts
                original_messages = []
                
                async def capture_send(message):
                    original_messages.append(message)
                
                # Get the original response
                await self.app(scope, receive, capture_send)
                
                # Now we can modify the headers and send
                for message in original_messages:
                    if message["type"] == "http.response.start":
                        # Get original headers
                        headers = list(message.get("headers", []))
                        
                        # Add CORS headers
                        cors_headers = [
                            (b'access-control-allow-origin', CORS_ALLOW_ORIGIN.encode()),
                            (b'access-control-allow-methods', b'GET, POST, PUT, DELETE, OPTIONS'),
                            (b'access-control-allow-headers', b'*'),
                            (b'access-control-allow-credentials', b'true')
                        ]
                        
                        # Add our CORS headers
                        for header in cors_headers:
                            # Check if header already exists
                            exists = False
                            for i, (name, _) in enumerate(headers):
                                if name.lower() == header[0].lower():
                                    exists = True
                                    headers[i] = header
                                    break
                            if not exists:
                                headers.append(header)
                        
                        # Update message with new headers
                        message["headers"] = headers
                    
                    # Send the modified message
                    await send(message)
                
                return
            
            # For non-static files, use the wrapped send approach
            # For other methods, wrap the send function to add CORS headers
            async def wrapped_send(message):
                if message["type"] == "http.response.start":
                    # Get original headers
                    orig_headers = message.get("headers", [])
                    headers = {}
                    
                    # Convert to dict for easier manipulation
                    for name, value in orig_headers:
                        name_str = name.decode() if isinstance(name, bytes) else name
                        value_str = value.decode() if isinstance(value, bytes) else value
                        headers[name_str.lower()] = value_str
                    
                    # Add CORS headers
                    headers["access-control-allow-origin"] = CORS_ALLOW_ORIGIN
                    headers["access-control-allow-methods"] = "GET, POST, PUT, DELETE, OPTIONS"
                    headers["access-control-allow-headers"] = "*"
                    headers["access-control-allow-credentials"] = "true"
                    
                    # Convert back to list of tuples
                    new_headers = []
                    for name, value in headers.items():
                        new_headers.append((
                            name.encode() if isinstance(name, str) else name,
                            value.encode() if isinstance(value, str) else value
                        ))
                    
                    # Log headers for debugging
                    logger.info(f"Adding CORS headers to {method} response for {path}")
                    logger.info(f"Final headers: {headers}")
                    
                    # Update message with new headers
                    message["headers"] = new_headers
                
                await send(message)
            
            # Call app with wrapped send
            await self.app(scope, receive, wrapped_send)
    
    # Define our version of OTreeStarlette that includes CORS middleware
    class OTreeStarletteWithCORS(Starlette):
        def build_middleware_stack(self):
            debug = self.debug
            error_handler = None
            exception_handlers = {}
            
            for key, value in self.exception_handlers.items():
                if key in (500, Exception):
                    error_handler = value
                else:
                    exception_handlers[key] = value
            
            # Create middleware stack with our custom CORS middleware first
            middlewares = [
                # Original oTree middleware stack
                Middleware(otree.middleware.CommitTransactionMiddleware),
                Middleware(OTreeServerErrorMiddleware, handler=error_handler, debug=debug),
                Middleware(otree.middleware.PerfMiddleware),
                Middleware(otree.middleware.SessionMiddleware, secret_key=otree.middleware._SECRET),
                Middleware(ExceptionMiddleware, handlers=exception_handlers, debug=debug),
            ]
            
            logger.info("Building middleware stack with CORS support")
            
            # Build the middleware stack
            app = self.router
            for cls, options in reversed(middlewares):
                app = cls(app=app, **options)
            
            # Add our custom CORS middleware at the very end (runs first)
            app = OptimizedCORSMiddleware(app)
            
            logger.info("Successfully built middleware stack with CORS middleware")
            return app
    
    # Define server error handler (same as in otree.asgi)
    ERR_500 = 500
    
    async def server_error(request, exc):
        return HTMLResponse(
            content=otree.errorpage.TEMPLATE.format(
                styles=otree.errorpage.STYLES,
                otree_styles=otree.errorpage.OTREE_STYLES,
                tab_title="Application error (500)",
                error="",
                ibis_html='',
                exc_html="""
                <p>
                  For security reasons, the error is not displayed here.
                  You can view it with one of the below techniques:
                </p>
                
                <ul>
                    <li>Delete the <code>OTREE_PRODUCTION</code> environment variable and reload this page</li>
                    <li>Look at your Sentry messages (see the docs on how to enable Sentry)</li>
                    <li>Look at the server logs</li>
                </ul>
                """,
                js='',
            ),
            status_code=ERR_500
        )
    
    # Add route for direct OPTIONS handling
    async def handle_options(request):
        logger.info(f"Direct route handler for OPTIONS at {request.url.path}")
        return PlainTextResponse("", headers={
            "Access-Control-Allow-Origin": CORS_ALLOW_ORIGIN,
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Max-Age": "1728000",
        })
    
    # Add our routes
    custom_routes = list(otree.urls.routes)
    
    # Add catch-all OPTIONS route
    custom_routes.append(
        Route("/{path:path}", endpoint=handle_options, methods=["OPTIONS"])
    )
    
    # Create a new instance of our custom application class
    custom_app = OTreeStarletteWithCORS(
        debug=otree.settings.DEBUG,
        routes=custom_routes,
        exception_handlers={ERR_500: server_error},
        on_shutdown=[otree.database.save_sqlite_db],
    )
    
    logger.info("Successfully created oTree application with CORS support")
    
    # Run the application using uvicorn
    port = os.environ.get('PORT', '8000')
    addr = '0.0.0.0'
    
    # Start timeout subprocess
    logger.info(f"Starting timeout subprocess on port {port}")
    subprocess.Popen(
        ['otree', 'timeoutsubprocess', str(port)],
        env=os.environ.copy()
    )
    
    # Start uvicorn with our custom application
    logger.info(f"Starting uvicorn with custom CORS-enabled app on {addr}:{port}")
    from uvicorn.main import Config, Server
    
    config = Config(
        app=custom_app,
        host=addr,
        port=int(port),
        log_level="info",
        log_config=None,
        workers=1,
        ws='websockets',
    )
    
    server = Server(config=config)
    server.run()

if __name__ == "__main__":
    run_with_cors() 