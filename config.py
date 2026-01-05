"""
Konfigurasi Aplikasi Absensi Karyawan 2025
Mendukung environment development dan production
"""

import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Base configuration"""
    
    # App Settings
    SECRET_KEY = os.getenv('SECRET_KEY', 'absensi-rahasia-2025-indonesia')
    
    # Database - PostgreSQL untuk production (Render), SQLite untuk development
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'DATABASE_URL', 
        'sqlite:///absensi_karyawan.db'
    )
    # Fix untuk Render PostgreSQL URL
    if SQLALCHEMY_DATABASE_URI.startswith('postgres://'):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace(
            'postgres://', 'postgresql://', 1
        )
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # JWT Settings
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'jwt-absensi-2025')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=12)  # Sesi kerja 12 jam
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    
    # Upload Settings
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
    
    # Attendance Settings (Sesuai kultur kerja Indonesia)
    OFFICE_START_TIME = "08:00"  # Jam masuk standar
    OFFICE_END_TIME = "17:00"    # Jam pulang standar
    LATE_TOLERANCE_MINUTES = 15   # Toleransi keterlambatan
    EARLY_LEAVE_TOLERANCE = 30    # Toleransi pulang awal
    
    # Geolocation Settings (Contoh: Jakarta)
    OFFICE_LOCATIONS = [
        {
            "name": "Kantor Pusat Jakarta",
            "latitude": -6.2088,
            "longitude": 106.8456,
            "radius_meters": 100  # Radius absen dalam meter
        },
        {
            "name": "Kantor Cabang Surabaya", 
            "latitude": -7.2575,
            "longitude": 112.7521,
            "radius_meters": 100
        }
    ]
    
    # Timezone Indonesia
    TIMEZONE = 'Asia/Jakarta'  # WIB
    # Untuk WIT: 'Asia/Jayapura'
    # Untuk WITA: 'Asia/Makassar'


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    

class ProductionConfig(Config):
    """Production configuration untuk Render"""
    DEBUG = False
    

# Config selector
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
