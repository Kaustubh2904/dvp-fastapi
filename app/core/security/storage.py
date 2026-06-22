import os
import shutil
from abc import ABC, abstractmethod
from typing import BinaryIO
from fastapi import UploadFile
from app.core.config.settings import settings


class StorageService(ABC):
    @abstractmethod
    async def upload_file(self, file: UploadFile, folder: str = "") -> str:
        """
        Uploads a file and returns its public URL/path string.
        """
        pass

    @abstractmethod
    async def delete_file(self, file_url: str) -> bool:
        """
        Deletes a file from storage.
        """
        pass

    @abstractmethod
    def get_file_url(self, file_path: str) -> str:
        """
        Translates a file path to its URL.
        """
        pass


class LocalStorageService(StorageService):
    def __init__(self, base_dir: str = settings.UPLOAD_DIR):
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)

    async def upload_file(self, file: UploadFile, folder: str = "") -> str:
        folder_path = os.path.join(self.base_dir, folder)
        os.makedirs(folder_path, exist_ok=True)
        
        # Save file with original filename
        file_path = os.path.join(folder_path, file.filename)
        
        # Async writing loop
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        return self.get_file_url(os.path.join(folder, file.filename))

    async def delete_file(self, file_url: str) -> bool:
        # Resolve path
        path = os.path.join(self.base_dir, file_url.replace("/static/uploads/", ""))
        if os.path.exists(path):
            os.remove(path)
            return True
        return False

    def get_file_url(self, file_path: str) -> str:
        # Format a relative URL that FastAPI can serve
        normalized = file_path.replace("\\", "/")
        return f"/static/uploads/{normalized}"


# Instantiate default storage
storage_service = LocalStorageService()
