"""
Configuration - FIXED for Render PostgreSQL SSL
"""

import os
from datetime import timedelta

class Config:
    # Secret Keys
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'jwt-secret-key-change-in-production')
    
    # Database
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///absensi.db')
    
    # Fix Render PostgreSQL URL (postgres:// -> postgresql://)
    if SQLALCHEMY_DATABASE_URI and SQLALCHEMY_DATABASE_URI.startswith('postgres://'):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace('postgres://', 'postgresql://', 1)
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # === FIX: Connection Pool Settings untuk Render ===
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,        # Test connection before use
        'pool_recycle': 280,          # Recycle connections every 280 seconds (Render timeout is 300s)
        'pool_timeout': 20,           # Wait max 20 seconds for connection
        'pool_size': 5,               # Number of connections to keep
        'max_overflow': 10,           # Max additional connections
        'connect_args': {
            'connect_timeout': 10,    # Connection timeout
            'keepalives': 1,          # Enable TCP keepalive
            'keepalives_idle': 30,    # Seconds before sending keepalive
            'keepalives_interval': 10, # Seconds between keepalives
            'keepalives_count': 5      # Max keepalive probes
        }
    }
    
    # JWT Settings
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=12)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    
    # Timezone
    TIMEZONE = 'Asia/Jakarta'


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_ECHO = True


class ProductionConfig(Config):
    DEBUG = False
    SQLALCHEMY_ECHO = False


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': ProductionConfig
}
