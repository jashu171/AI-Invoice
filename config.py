"""
Configuration management for the invoice processing application.
Handles AI extraction settings, API keys, and feature flags.
"""

import os
from typing import Optional
import logging

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # If python-dotenv is not installed, try to load manually
    if os.path.exists('.env'):
        with open('.env', 'r') as f:
            for line in f:
                if line.strip() and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value

logger = logging.getLogger(__name__)


class AIConfig:
    """Configuration class for AI extraction settings."""
    
    def __init__(self):
        self.api_key = os.getenv('GEMINI_API_KEY')
        self.model = os.getenv('GEMINI_MODEL', 'gemini-2.0-flash')
        self.temperature = float(os.getenv('GEMINI_TEMPERATURE', '0.1'))
        self.max_tokens = int(os.getenv('GEMINI_MAX_TOKENS', '8192'))
        self.enabled = os.getenv('AI_EXTRACTION_ENABLED', 'true').lower() == 'true'
        self.fallback_enabled = os.getenv('FALLBACK_TO_REGEX', 'true').lower() == 'true'
        self.timeout = int(os.getenv('GEMINI_TIMEOUT', '30'))
        self.max_retries = int(os.getenv('GEMINI_MAX_RETRIES', '3'))
        
    def is_configured(self) -> bool:
        """Check if AI extraction is properly configured."""
        return bool(self.api_key and self.enabled)
    
    def validate(self) -> list:
        """Validate configuration and return list of errors."""
        errors = []
        
        if self.enabled and not self.api_key:
            errors.append("GEMINI_API_KEY is required when AI extraction is enabled")
        
        if self.temperature < 0 or self.temperature > 2:
            errors.append("GEMINI_TEMPERATURE must be between 0 and 2")
        
        if self.max_tokens < 1 or self.max_tokens > 32768:
            errors.append("GEMINI_MAX_TOKENS must be between 1 and 32768")
        
        if self.timeout < 1 or self.timeout > 300:
            errors.append("GEMINI_TIMEOUT must be between 1 and 300 seconds")
        
        return errors


class AppConfig:
    """Main application configuration."""
    
    def __init__(self):
        self.ai = AIConfig()
        self.debug = os.getenv('DEBUG', 'false').lower() == 'true'
        self.secret_key = os.getenv('SECRET_KEY', 'your-secret-key-here')
        self.upload_folder = os.getenv('UPLOAD_FOLDER', 'uploads')
        self.processed_folder = os.getenv('PROCESSED_FOLDER', 'processed')
        self.max_content_length = int(os.getenv('MAX_CONTENT_LENGTH', str(16 * 1024 * 1024)))
        
    def validate(self) -> list:
        """Validate all configuration and return list of errors."""
        errors = []
        errors.extend(self.ai.validate())
        
        if not self.secret_key or self.secret_key == 'your-secret-key-here':
            errors.append("SECRET_KEY should be set to a secure random value")
        
        return errors


# Global configuration instance
config = AppConfig()

# Validate configuration on import
config_errors = config.validate()
if config_errors:
    for error in config_errors:
        logger.warning(f"Configuration warning: {error}")