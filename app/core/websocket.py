from app.services.websocket_service import connection_manager

# Re-export the ConnectionManager singleton
__all__ = ["connection_manager"]