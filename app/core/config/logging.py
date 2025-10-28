"""
Logging Configuration
"""
from typing import Optional
from pydantic import BaseModel, Field
from pathlib import Path

class LogConfig(BaseModel):
    """Logging configuration settings"""
    
    LEVEL: str = Field("INFO", description="Logging level")
    FORMAT: str = Field(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        description="Log format string"
    )
    FILE: Optional[Path] = Field(
        None, 
        description="Log file path (optional)"
    )

    @property
    def log_config(self) -> dict:
        """Get complete logging configuration dictionary"""
        config = {
            'version': 1,
            'disable_existing_loggers': False,
            'formatters': {
                'standard': {
                    'format': self.FORMAT
                },
            },
            'handlers': {
                'console': {
                    'class': 'logging.StreamHandler',
                    'formatter': 'standard',
                    'level': self.LEVEL
                }
            },
            'loggers': {
                '': {  # Root logger
                    'handlers': ['console'],
                    'level': self.LEVEL,
                    'propagate': True
                }
            }
        }

        # Add file handler if log file is specified
        if self.FILE:
            config['handlers']['file'] = {
                'class': 'logging.FileHandler',
                'filename': str(self.FILE),
                'formatter': 'standard',
                'level': self.LEVEL
            }
            config['loggers']['']['handlers'].append('file')

        return config

    class Config:
        env_prefix = "LOG_"