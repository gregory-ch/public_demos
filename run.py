#!/usr/bin/env python
import os
import sys
import logging
import importlib
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware

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

def patch_otree_for_cors():
    """Patch oTree's middleware stack to include CORS middleware"""
    
    # Import the original OTreeStarlette class
    from otree.asgi import OTreeStarlette
    
    # Store the original build_middleware_stack method
    original_build_middleware_stack = OTreeStarlette.build_middleware_stack
    
    # Create patched method that adds our CORS middleware
    def patched_build_middleware_stack(self):
        logger.info("Patching oTree middleware stack to add CORS support")
        
        # Call the original method to get the middleware list
        middlewares = [
            Middleware(CORSMiddleware,
                allow_origins=[CORS_ALLOW_ORIGIN],
                allow_methods=["*"],
                allow_headers=["*"],
                allow_credentials=True,
                expose_headers=["*"])
        ]
        
        # Get middleware stack from original method
        app = original_build_middleware_stack(self)
        
        # Add our CORS middleware at the very beginning (outside all other middleware)
        for cls, options in reversed(middlewares):
            app = cls(app=app, **options)
        
        logger.info("Successfully added CORS middleware to oTree")
        return app
    
    # Replace the original method with our patched version
    OTreeStarlette.build_middleware_stack = patched_build_middleware_stack
    logger.info("OTreeStarlette.build_middleware_stack method has been patched")

def run_server_with_cors():
    """Run standard oTree prodserver with CORS patch applied"""
    
    # Apply our patch to oTree before anything else is imported
    patch_otree_for_cors()
    
    # Import and run the standard prodserver code
    from otree.cli.prodserver1of2 import Command
    
    logger.info("Starting oTree prodserver with CORS patch")
    cmd = Command()
    cmd.handle()

if __name__ == "__main__":
    run_server_with_cors() 