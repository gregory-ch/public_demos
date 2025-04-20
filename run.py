#!/usr/bin/env python
import os
import sys
import logging
import asyncio
import importlib
import importlib.util
from pathlib import Path

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
    Run oTree with CORS support by patching both static files and main app
    """
    # First, import starlette components we need
    from starlette.staticfiles import StaticFiles
    from starlette.responses import Response
    from starlette.middleware import Middleware
    
    # Import otree modules but NOT the app itself
    import otree
    import otree.settings

    # 1. Patch static files handler with CORS support
    # Create a wrapper for StaticFiles that adds CORS headers
    class CORSStaticFiles(StaticFiles):
        """
        A wrapper around StaticFiles that adds CORS headers to all responses
        """
        async def __call__(self, scope, receive, send):
            """
            Process a request and add CORS headers to the response
            """
            if scope["type"] != "http":
                await super().__call__(scope, receive, send)
                return
                
            method = scope.get("method", "")
            path = scope.get("path", "")
            
            # Special handling for OPTIONS requests (preflight)
            if method == "OPTIONS":
                logger.info(f"Handling OPTIONS request for static file: {path}")
                
                # Send a response with CORS headers
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
                await response(scope, receive, send)
                return
            
            # For regular requests, intercept the response to add CORS headers
            async def send_with_cors(message):
                if message["type"] == "http.response.start":
                    # Get original headers
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
                    
                    # Update headers in message
                    message["headers"] = headers
                
                # Send the modified message
                await send(message)
            
            # Call the original handler with our modified send function
            await super().__call__(scope, receive, send_with_cors)
    
    # Define a class to mimic the original OTreeStaticFiles with CORS support
    class OTreeStaticFilesWithCORS(CORSStaticFiles):
        """
        A version of otree.common2.OTreeStaticFiles with CORS support
        """
        def get_directories(self, directory, packages):
            directories = []
            if directory is not None:
                directories.append(directory)

            for package in packages or []:
                spec = importlib.util.find_spec(package)
                assert (
                    spec is not None and spec.origin is not None
                ), f"Package {package!r} could not be found, or maybe __init__.py is missing"
                package_directory = os.path.normpath(
                    os.path.join(spec.origin, "..", "static")
                )
                if os.path.isdir(package_directory):
                    directories.append(package_directory)

            return directories

        def assert_file_exists(self, path):
            # Simplified version without cache
            for _dir in self.all_directories:
                if Path(_dir, path).is_file():
                    return
            raise FileNotFoundError(path)
    
    # Create a new instance of static files handler with CORS
    static_files_app_with_cors = OTreeStaticFilesWithCORS(
        directory='_static', packages=['otree'] + otree.settings.OTREE_APPS
    )
    
    # Now, patch otree.common2.static_files_app with our CORS version
    from otree import common2
    logger.info("Patching otree.common2.static_files_app with CORS support")
    common2.static_files_app = static_files_app_with_cors
    
    # Verify the patch was successful
    logger.info(f"Static files app is now: {type(common2.static_files_app).__name__}")
    
    # 2. Patch the main application to add CORS middleware
    # First, we create a CORS middleware for the main app
    class CORSMiddleware:
        """
        Middleware that adds CORS headers to all responses and handles OPTIONS requests
        """
        def __init__(self, app):
            self.app = app
        
        async def __call__(self, scope, receive, send):
            if scope["type"] != "http":
                await self.app(scope, receive, send)
                return
                
            method = scope.get("method", "")
            path = scope.get("path", "")
            
            # Special handling for OPTIONS requests (preflight)
            if method == "OPTIONS":
                logger.info(f"Handling OPTIONS request for path: {path}")
                
                # Send a response with CORS headers
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
                await response(scope, receive, send)
                return
            
            # For regular requests, wrap the send function to add CORS headers
            async def send_with_cors(message):
                if message["type"] == "http.response.start":
                    # Get original headers
                    headers = list(message.get("headers", []))
                    
                    # Add CORS headers
                    cors_headers = [
                        (b"access-control-allow-origin", CORS_ALLOW_ORIGIN.encode()),
                        (b"access-control-allow-methods", b"GET, POST, PUT, DELETE, OPTIONS"),
                        (b"access-control-allow-headers", b"*"),
                        (b"access-control-allow-credentials", b"true"),
                    ]
                    
                    # Debug log the original headers
                    header_dict = {name.decode(): value.decode() for name, value in headers}
                    logger.info(f"Original headers for {path}: {header_dict}")
                    
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
                    
                    # Debug log the modified headers
                    new_header_dict = {name.decode(): value.decode() for name, value in headers}
                    logger.info(f"Modified headers for {path}: {new_header_dict}")
                    
                    # Update headers in message
                    message["headers"] = headers
                
                # Send the modified message
                await send(message)
            
            # Call the original app with our modified send function
            await self.app(scope, receive, send_with_cors)
    
    # Now patch the main ASGI application with our CORS middleware
    # We need to import it here after patching the static files app
    from otree import asgi
    logger.info("Patching main oTree ASGI application with CORS middleware")
    
    # Save the original app
    original_app = asgi.app
    
    # Replace it with our wrapped version
    asgi.app = CORSMiddleware(original_app)
    logger.info("Main oTree application patched with CORS middleware")
    
    # After patching, run oTree using the command
    logger.info("Starting oTree with CORS support for both static files and main app...")
    
    # Directly import the command runner and execute
    from otree.cli.prodserver1of2 import Command
    
    # Get port from environment or default to 8000
    port = os.environ.get('PORT', '8000')
    
    # Create and run the command
    command = Command()
    logger.info(f"Running oTree prodserver on port {port}")
    
    # The command expects an optional addrport argument (format: [host:]port)
    command.handle(addrport=port)

if __name__ == "__main__":
    run_otree_with_cors() 