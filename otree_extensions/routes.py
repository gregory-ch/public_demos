from middleware import CorsASGIMiddleware

def get_middleware(app):
    """
    Adds CORS middleware to ASGI application
    """
    app = CorsASGIMiddleware(app)
    return app 