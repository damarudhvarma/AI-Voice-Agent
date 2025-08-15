import os
from werkzeug.utils import secure_filename
from typing import Optional
from utils.config import Config
from utils.logger import get_logger
from models.schemas import FileInfo

logger = get_logger("file_service")


class FileService:
    """Service for handling file uploads and management"""
    
    def __init__(self):
        self.upload_folder = Config.UPLOAD_FOLDER
        self.max_content_length = Config.MAX_CONTENT_LENGTH
        self._ensure_upload_directory()
    
    def _ensure_upload_directory(self) -> None:
        """Ensure the upload directory exists"""
        if not os.path.exists(self.upload_folder):
            os.makedirs(self.upload_folder)
            logger.info(f"Created upload directory: {self.upload_folder}")
    
    def save_audio_file(self, file) -> Optional[FileInfo]:
        """
        Save an uploaded audio file
        
        Args:
            file: FileStorage object from Flask request
            
        Returns:
            FileInfo object if successful, None otherwise
        """
        try:
            if not file or file.filename == '':
                logger.error("No file provided or empty filename")
                return None
            
            # Secure the filename
            filename = secure_filename(file.filename)
            
            # Check file size
            file.seek(0, os.SEEK_END)
            file_size = file.tell()
            file.seek(0)  # Reset file pointer
            
            if file_size > self.max_content_length:
                logger.error(f"File too large: {file_size} bytes (max: {self.max_content_length})")
                return None
            
            # Save the file
            file_path = os.path.join(self.upload_folder, filename)
            file.save(file_path)
            
            # Verify file was saved
            if not os.path.exists(file_path):
                logger.error(f"Failed to save file: {file_path}")
                return None
            
            actual_size = os.path.getsize(file_path)
            
            file_info = FileInfo(
                name=filename,
                content_type=file.content_type or 'audio/unknown',
                size=actual_size
            )
            
            logger.info(f"Successfully saved audio file: {filename} ({actual_size} bytes)")
            return file_info
            
        except Exception as e:
            logger.error(f"Error saving audio file: {str(e)}")
            return None
    
    def get_file_path(self, filename: str) -> Optional[str]:
        """
        Get the full path to a saved file
        
        Args:
            filename: Name of the file
            
        Returns:
            Full file path if exists, None otherwise
        """
        file_path = os.path.join(self.upload_folder, filename)
        if os.path.exists(file_path):
            return file_path
        return None
    
    def delete_file(self, filename: str) -> bool:
        """
        Delete a file from the upload directory
        
        Args:
            filename: Name of the file to delete
            
        Returns:
            True if file was deleted, False otherwise
        """
        try:
            file_path = os.path.join(self.upload_folder, filename)
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Deleted file: {filename}")
                return True
            else:
                logger.warning(f"File not found for deletion: {filename}")
                return False
        except Exception as e:
            logger.error(f"Error deleting file {filename}: {str(e)}")
            return False
    
    def get_upload_directory_size(self) -> int:
        """
        Get the total size of the upload directory
        
        Returns:
            Total size in bytes
        """
        total_size = 0
        try:
            for dirpath, dirnames, filenames in os.walk(self.upload_folder):
                for filename in filenames:
                    file_path = os.path.join(dirpath, filename)
                    if os.path.exists(file_path):
                        total_size += os.path.getsize(file_path)
        except Exception as e:
            logger.error(f"Error calculating upload directory size: {str(e)}")
        
        return total_size
    
    def cleanup_old_files(self, max_age_hours: int = 24) -> int:
        """
        Clean up old files from the upload directory
        
        Args:
            max_age_hours: Maximum age of files in hours
            
        Returns:
            Number of files deleted
        """
        import time
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        deleted_count = 0
        
        try:
            for filename in os.listdir(self.upload_folder):
                file_path = os.path.join(self.upload_folder, filename)
                if os.path.isfile(file_path):
                    file_age = current_time - os.path.getmtime(file_path)
                    if file_age > max_age_seconds:
                        if self.delete_file(filename):
                            deleted_count += 1
            
            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} old files")
            
        except Exception as e:
            logger.error(f"Error during file cleanup: {str(e)}")
        
        return deleted_count


# Global file service instance
file_service = FileService()
