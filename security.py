import bleach
import html
from flask import request
from werkzeug.utils import secure_filename
import re

class SecurityManager:
    """Centralized security management for the chat application"""

    def __init__(self):
        # XSS protection - allowed tags and attributes
        self.allowed_tags = [
            'p', 'br', 'strong', 'em', 'u', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
            'ul', 'ol', 'li', 'blockquote', 'code', 'pre', 'a', 'img'
        ]
        self.allowed_attributes = {
            'a': ['href', 'title'],
            'img': ['src', 'alt', 'title']
        }

    def sanitize_html(self, content: str) -> str:
        """Sanitize HTML content to prevent XSS attacks"""
        if not content:
            return content

        # First, escape HTML entities
        content = html.escape(content, quote=True)

        # Then allow specific tags
        content = bleach.clean(
            content,
            tags=self.allowed_tags,
            attributes=self.allowed_attributes,
            strip=True
        )

        return content

    def validate_input(self, data: dict) -> dict:
        """Validate and sanitize input data"""
        sanitized = {}

        for key, value in data.items():
            if isinstance(value, str):
                # Remove null bytes and other dangerous characters
                value = value.replace('\x00', '').replace('\r\n', '\n').replace('\r', '\n')

                # Limit length (adjust based on field)
                max_length = 10000 if 'text' in key.lower() else 255
                value = value[:max_length]

                # Sanitize HTML for text fields
                if 'text' in key.lower() or 'content' in key.lower():
                    value = self.sanitize_html(value)

                sanitized[key] = value
            else:
                sanitized[key] = value

        return sanitized

    def secure_filename_ext(self, filename: str) -> str:
        """Enhanced secure filename with extension validation"""
        if not filename:
            return filename

        # Use werkzeug's secure_filename as base
        filename = secure_filename(filename)

        # Additional validation - only allow specific extensions
        allowed_extensions = {
            'images': ['jpg', 'jpeg', 'png', 'gif', 'webp'],
            'audio': ['mp3', 'wav', 'ogg', 'webm'],
            'documents': ['pdf', 'txt', 'doc', 'docx']
        }

        if '.' in filename:
            ext = filename.rsplit('.', 1)[1].lower()
            # Check if extension is in any allowed category
            if not any(ext in exts for exts in allowed_extensions.values()):
                # If not allowed, remove extension
                filename = filename.rsplit('.', 1)[0] + '.txt'

        return filename

    def validate_file_upload(self, file, max_size: int = 10*1024*1024) -> tuple[bool, str]:
        """Validate file upload"""
        if not file:
            return False, "No file provided"

        # Check file size
        if hasattr(file, 'content_length') and file.content_length:
            if file.content_length > max_size:
                return False, f"File too large (max {max_size//1024//1024}MB)"

        # Check filename
        if hasattr(file, 'filename') and file.filename:
            if len(file.filename) > 255:
                return False, "Filename too long"

            # Check for dangerous characters
            if any(char in file.filename for char in ['<', '>', ':', '"', '|', '?', '*']):
                return False, "Invalid filename characters"

        return True, "Valid"

    def rate_limit_check(self, key: str, max_requests: int = 10, window_seconds: int = 60) -> bool:
        """Basic rate limiting check (can be enhanced with Redis/external storage)"""
        # This is a simple in-memory implementation
        # For production, use Redis or database
        current_time = __import__('time').time()

        # In a real implementation, you'd store this in Redis/database
        # For now, we'll use a simple approach
        return True  # Placeholder - implement proper rate limiting

    def log_security_event(self, event_type: str, details: dict):
        """Log security-related events"""
        import logging
        logger = logging.getLogger('security')
        logger.warning(f"SECURITY EVENT: {event_type} - {details}")

# Global security manager instance
security_manager = SecurityManager()
