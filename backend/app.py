"""
Sistem Absensi Karyawan 2025
Main Application - FIXED with DB Retry Logic
"""

import os
import sys
import logging
import traceback
import time
from functools import wraps
from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from datetime import datetime
from sqlalchemy import text
from sqlalchemy.exc import OperationalError, DisconnectionError

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

logger.info("="*50)
logger.info("Starting Sistem Absensi Karyawan 2025")
logger.info("="*50)

# Import config
try:
    from config import config
    logger.info("✓ Config imported")
except Exception as e:
    logger.error(f"✗ Config import failed: {e}")
    traceback.print_exc()

# Import models
try:
    from models import db, Company, Department, Employee, OfficeLocation, LeaveBalance
    logger.info("✓ Models imported")
except Exception as e:
    logger.error(f"✗ Models import failed: {e}")
    traceback.print_exc()

# Import routes
try:
    from routes import auth_bp, attendance_bp, leave_bp, reports_bp, employee_bp
    from routes.auth import *
    from routes.attendance import *
    from routes.leave import *
    from routes.reports import *
    from routes.employee import *
    logger.info("✓ Routes imported")
except Exception as e:
    logger.error(f"✗ Routes import failed: {e}")
    traceback.print_exc()

# Initialize JWT
jwt = JWTManager()


# ============================================
# DATABASE RETRY DECORATOR
# ============================================
def db_retry(max_retries=3, delay=1):
    """Decorator to retry database operations on connection errors"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except (OperationalError, DisconnectionError) as e:
                    last_error = e
                    logger.warning(f"DB connection error (attempt {attempt + 1}/{max_retries}): {e}")
                    
                    # Try to rollback and reconnect
                    try:
                        db.session.rollback()
                        db.session.remove()
                        db.engine.dispose()
                    except:
                        pass
                    
                    if attempt < max_retries - 1:
                        time.sleep(delay * (attempt + 1))  # Exponential backoff
                    
            # All retries failed
            logger.error(f"All {max_retries} DB retry attempts failed")
            raise last_error
        return wrapper
    return decorator


# ============================================
# APPLICATION FACTORY
# ============================================
def create_app(config_name=None):
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'production')
    
    logger.info(f"Creating app with config: {config_name}")
    
    # Paths
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    static_folder = os.path.join(base_dir, 'frontend')
    
    logger.info(f"Static folder: {static_folder}")
    
    app = Flask(__name__, static_folder=static_folder, static_url_path='')
    
    # Load config
    try:
        app.config.from_object(config[config_name])
        logger.info("✓ Config loaded")
        logger.info(f"Database URI: {app.config.get('SQLALCHEMY_DATABASE_URI', '')[:50]}...")
    except Exception as e:
        logger.error(f"Config load failed: {e}")
        # Fallback config
        app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'fallback-secret')
        app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///absensi.db')
        if app.config['SQLALCHEMY_DATABASE_URI'].startswith('postgres://'):
            app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SQLALCHEMY_DATABASE_URI'].replace('postgres://', 'postgresql://', 1)
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'fallback-jwt')
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
            'pool_pre_ping': True,
            'pool_recycle': 280,
        }
    
    # Initialize extensions
    db.init_app(app)
    jwt.init_app(app)
    CORS(app, origins=["*"], supports_credentials=True)
    logger.info("✓ Extensions initialized")
    
    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(attendance_bp)
    app.register_blueprint(leave_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(employee_bp)
    logger.info("✓ Blueprints registered")
    
    # ============================================
    # JWT Error Handlers
    # ============================================
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return jsonify({'success': False, 'message': 'Token kadaluarsa. Silakan login kembali.'}), 401
    
    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return jsonify({'success': False, 'message': 'Token tidak valid.'}), 401
    
    @jwt.unauthorized_loader
    def missing_token_callback(error):
        return jsonify({'success': False, 'message': 'Token diperlukan.'}), 401
    
    # ============================================
    # Error Handlers
    # ============================================
    @app.errorhandler(404)
    def not_found(e):
        if request.path.startswith('/api'):
            return jsonify({'success': False, 'message': 'Endpoint tidak ditemukan'}), 404
        try:
            return send_from_directory(app.static_folder, 'index.html')
        except:
            return jsonify({'message': 'API Sistem Absensi', 'health': '/api/health'}), 200
    
    @app.errorhandler(500)
    def server_error(e):
        logger.error(f"Server error: {e}")
        
        # Check if it's a database error
        error_str = str(e).lower()
        if 'ssl' in error_str or 'connection' in error_str or 'operational' in error_str:
            try:
                db.session.rollback()
                db.session.remove()
            except:
                pass
            return jsonify({
                'success': False,
                'message': 'Koneksi database terputus. Silakan coba lagi.',
                'retry': True
            }), 503
        
        return jsonify({'success': False, 'message': 'Terjadi kesalahan server'}), 500
    
    # ============================================
    # Health Check with DB Retry
    # ============================================
    @app.route('/api/health')
    def health_check():
        result = {
            'status': 'running',
            'timestamp': datetime.now().isoformat(),
            'version': '1.0.0',
            'database': 'checking...'
        }
        
        # Try to connect to database with retry
        for attempt in range(3):
            try:
                db.session.execute(text('SELECT 1'))
                db.session.commit()
                result['database'] = 'connected'
                break
            except Exception as e:
                logger.warning(f"Health check DB attempt {attempt + 1} failed: {e}")
                try:
                    db.session.rollback()
                    db.session.remove()
                except:
                    pass
                
                if attempt == 2:
                    result['database'] = f'error after 3 attempts'
                else:
                    time.sleep(1)
        
        status_code = 200 if result['database'] == 'connected' else 503
        return jsonify(result), status_code
    
    # ============================================
    # Debug Endpoint
    # ============================================
    @app.route('/api/debug')
    def debug_info():
        return jsonify({
            'env': os.getenv('FLASK_ENV', 'not set'),
            'database_url_set': bool(os.getenv('DATABASE_URL')),
            'secret_key_set': bool(os.getenv('SECRET_KEY')),
            'static_folder': app.static_folder,
            'static_exists': os.path.exists(app.static_folder) if app.static_folder else False
        }), 200
    
    # ============================================
    # Frontend Routes
    # ============================================
    @app.route('/')
    def serve_index():
        try:
            return send_from_directory(app.static_folder, 'index.html')
        except Exception as e:
            logger.error(f"Error serving index: {e}")
            return jsonify({
                'message': 'Sistem Absensi Karyawan API',
                'health': '/api/health'
            }), 200
    
    @app.route('/<path:path>')
    def serve_static(path):
        try:
            if app.static_folder and os.path.exists(os.path.join(app.static_folder, path)):
                return send_from_directory(app.static_folder, path)
            return send_from_directory(app.static_folder, 'index.html')
        except:
            return jsonify({'error': 'File not found'}), 404
    
    # ============================================
    # Request Hooks
    # ============================================
    @app.before_request
    def before_request():
        # Ensure fresh database connection for each request
        try:
            db.session.execute(text('SELECT 1'))
        except:
            try:
                db.session.rollback()
                db.session.remove()
            except:
                pass
    
    @app.teardown_request
    def teardown_request(exception=None):
        # Clean up database session after each request
        try:
            if exception:
                db.session.rollback()
            db.session.remove()
        except:
            pass
    
    return app


# ============================================
# DATABASE INITIALIZATION
# ============================================
def init_database(app):
    with app.app_context():
        # Create tables with retry
        for attempt in range(3):
            try:
                logger.info(f"Creating tables (attempt {attempt + 1})...")
                db.create_all()
                logger.info("✓ Tables created")
                break
            except Exception as e:
                logger.error(f"Table creation failed: {e}")
                if attempt == 2:
                    return
                time.sleep(2)
        
        # Check if data exists
        try:
            if Company.query.first():
                logger.info("Database already has data")
                return
        except Exception as e:
            logger.warning(f"Check existing data failed: {e}")
            try:
                db.session.rollback()
            except:
                pass
        
        logger.info("Inserting initial data...")
        
        try:
            # Create company
            company = Company(
                name="PT Contoh Indonesia",
                address="Jl. Sudirman No. 123, Jakarta",
                phone="021-1234567",
                email="info@contoh.co.id",
                work_start_time="08:00",
                work_end_time="17:00",
                late_tolerance=15
            )
            db.session.add(company)
            db.session.flush()
            logger.info(f"✓ Company created: {company.id}")
            
            # Create department
            dept = Department(company_id=company.id, name="IT", code="IT")
            db.session.add(dept)
            db.session.flush()
            logger.info(f"✓ Department created: {dept.id}")
            
            # Create office location
            location = OfficeLocation(
                company_id=company.id,
                name="Kantor Pusat",
                latitude=-6.2088,
                longitude=106.8456,
                radius_meters=100
            )
            db.session.add(location)
            
            # Create admin
            admin = Employee(
                company_id=company.id,
                department_id=dept.id,
                nik="1234567890123456",
                nip="ADM001",
                name="Administrator",
                email="admin@contoh.co.id",
                phone="081234567890",
                position="Admin",
                role="admin",
                is_wfh_allowed=True
            )
            admin.set_password("admin123")
            db.session.add(admin)
            db.session.flush()
            
            # Create leave balance for admin
            lb = LeaveBalance(
                employee_id=admin.id,
                year=datetime.now().year,
                annual_quota=12,
                annual_remaining=12
            )
            db.session.add(lb)
            
            # Create sample employee
            emp = Employee(
                company_id=company.id,
                department_id=dept.id,
                nik="9999999999999999",
                nip="EMP001",
                name="Budi Santoso",
                email="budi@contoh.co.id",
                phone="081234567891",
                position="Staff",
                role="employee",
                is_wfh_allowed=True
            )
            emp.set_password("password123")
            db.session.add(emp)
            db.session.flush()
            
            lb2 = LeaveBalance(
                employee_id=emp.id,
                year=datetime.now().year,
                annual_quota=12,
                annual_remaining=12
            )
            db.session.add(lb2)
            
            db.session.commit()
            
            logger.info("="*50)
            logger.info("DATABASE INITIALIZED!")
            logger.info("Admin: admin@contoh.co.id / admin123")
            logger.info("Employee: budi@contoh.co.id / password123")
            logger.info("="*50)
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Data insertion failed: {e}")
            traceback.print_exc()


# ============================================
# CREATE APP
# ============================================
app = create_app()

# Initialize database
try:
    init_database(app)
except Exception as e:
    logger.warning(f"Database init skipped: {e}")

logger.info("="*50)
logger.info("APPLICATION READY")
logger.info("="*50)

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=os.getenv('FLASK_ENV') == 'development')
if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_ENV') == 'development'
    logger.info(f"Starting server on port {port}...")
    app.run(host='0.0.0.0', port=port, debug=debug)
