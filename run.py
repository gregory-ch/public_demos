#!/usr/bin/env python
import os
import sys
import logging
import importlib
import subprocess
from copy import deepcopy

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

def run_with_cors():
    """
    Creates a new instance of the oTree application with CORS middleware added
    and then runs it using uvicorn.
    """
    # Import necessary modules from oTree and Starlette
    from starlette.applications import Starlette
    from starlette.middleware import Middleware
    from starlette.middleware.cors import CORSMiddleware
    from starlette.responses import HTMLResponse
    
    # Import oTree specific modules without importing the app instance
    # We need to avoid importing app from otree.asgi as that would give us the
    # already-constructed instance
    import otree.errorpage
    import otree.database
    import otree.middleware
    import otree.settings
    from otree.errorpage import OTreeServerErrorMiddleware
    from otree.patch import ExceptionMiddleware
    import otree.urls
    
    logger.info("Creating new oTree application with CORS support")
    
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
            
            # Create middleware stack identical to oTree's but with our CORS middleware
            middlewares = [
                # Add CORS middleware at the very beginning
                Middleware(CORSMiddleware,
                    allow_origins=[CORS_ALLOW_ORIGIN],
                    allow_methods=["*"],
                    allow_headers=["*"],
                    allow_credentials=True),
                
                # Original oTree middleware stack
                Middleware(otree.middleware.CommitTransactionMiddleware),
                Middleware(OTreeServerErrorMiddleware, handler=error_handler, debug=debug),
                Middleware(otree.middleware.PerfMiddleware),
                Middleware(otree.middleware.SessionMiddleware, secret_key=otree.middleware._SECRET),
                Middleware(ExceptionMiddleware, handlers=exception_handlers, debug=debug),
            ]
            
            app = self.router
            for cls, options in reversed(middlewares):
                app = cls(app=app, **options)
            
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
    
    # Create a new instance of our custom application class
    custom_app = OTreeStarletteWithCORS(
        debug=otree.settings.DEBUG,
        routes=otree.urls.routes,
        exception_handlers={ERR_500: server_error},
        on_shutdown=[otree.database.save_sqlite_db],
    )
    
    logger.info("Successfully created oTree application with CORS support")
    
    # Run the application using uvicorn (same way as in prodserver1of2.py)
    port = os.environ.get('PORT', '8000')
    addr = '0.0.0.0'
    
    # Start timeout subprocess
    logger.info(f"Starting timeout subprocess on port {port}")
    subprocess.Popen(
        ['otree', 'timeoutsubprocess', str(port)],
        env=os.environ.copy()
    )
    
    # Start uvicorn with our custom application
    logger.info(f"Starting uvicorn with custom app on {addr}:{port}")
    from uvicorn.main import Config, Server
    
    config = Config(
        app=custom_app,
        host=addr,
        port=int(port),
        log_level="info",
        log_config=None,  # oTree has its own logger
        workers=1,
        ws='websockets',
    )
    
    server = Server(config=config)
    server.run()

if __name__ == "__main__":
    run_with_cors() 