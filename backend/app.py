"""
Sistem Absensi Karyawan 2025
Main Application - With Debug
"""

import os
import sys
import logging
import traceback
from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# Log startup
logger.info("="*50)
logger.info("Starting Sistem Absensi Karyawan 2025")
logger.info("="*50)

# Try importing config
try:
    from config import config
    logger.info("✓ Config imported successfully")
except Exception as e:
    logger.error(f"✗ Failed to import config: {e}")
    traceback.print_exc()

# Try importing models
try:
    from models import db, Company, Department, Employee, OfficeLocation, LeaveBalance
    logger.info("✓ Models imported successfully")
except Exception as e:
    logger.error(f"✗ Failed to import models: {e}")
    traceback.print_exc()

# Try importing routes
try:
    from routes import auth_bp, attendance_bp, leave_bp, reports_bp, employee_bp
    logger.info("✓ Route blueprints imported successfully")
except Exception as e:
    logger.error(f"✗ Failed to import routes: {e}")
    traceback.print_exc()

# Import route handlers
try:
    from routes.auth import *
    logger.info("✓ Auth routes imported")
except Exception as e:
    logger.error(f"✗ Failed to import auth routes: {e}")
    traceback.print_exc()

try:
    from routes.attendance import *
    logger.info("✓ Attendance routes imported")
except Exception as e:
    logger.error(f"✗ Failed to import attendance routes: {e}")
    traceback.print_exc()

try:
    from routes.leave import *
    logger.info("✓ Leave routes imported")
except Exception as e:
    logger.error(f"✗ Failed to import leave routes: {e}")
    traceback.print_exc()

try:
    from routes.reports import *
    logger.info("✓ Reports routes imported")
except Exception as e:
    logger.error(f"✗ Failed to import reports routes: {e}")
    traceback.print_exc()

try:
    from routes.employee import *
    logger.info("✓ Employee routes imported")
except Exception as e:
    logger.error(f"✗ Failed to import employee routes: {e}")
    traceback.print_exc()

# Initialize extensions
jwt = JWTManager()


def create_app(config_name=None):
    """Application factory"""
    
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'production')
    
    logger.info(f"Creating app with config: {config_name}")
    
    # Get paths
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    static_folder = os.path.join(base_dir, 'frontend')
    
    logger.info(f"Base dir: {base_dir}")
    logger.info(f"Static folder: {static_folder}")
    logger.info(f"Static folder exists: {os.path.exists(static_folder)}")
    
    app = Flask(__name__, static_folder=static_folder, static_url_path='')
    
    # Load config
    try:
        app.config.from_object(config[config_name])
        logger.info("✓ Config loaded")
    except Exception as e:
        logger.error(f"✗ Failed to load config: {e}")
        # Use default config
        app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret')
        app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///absensi.db')
        if app.config['SQLALCHEMY_DATABASE_URI'].startswith('postgres://'):
            app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SQLALCHEMY_DATABASE_URI'].replace('postgres://', 'postgresql://', 1)
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'jwt-secret')
    
    logger.info(f"Database URI: {app.config.get('SQLALCHEMY_DATABASE_URI', 'NOT SET')[:50]}...")
    
    # Initialize extensions
    try:
        db.init_app(app)
        logger.info("✓ Database initialized")
    except Exception as e:
        logger.error(f"✗ Failed to init database: {e}")
    
    try:
        jwt.init_app(app)
        logger.info("✓ JWT initialized")
    except Exception as e:
        logger.error(f"✗ Failed to init JWT: {e}")
    
    CORS(app, origins=["*"], supports_credentials=True)
    logger.info("✓ CORS initialized")
    
    # Register blueprints
    try:
        app.register_blueprint(auth_bp)
        app.register_blueprint(attendance_bp)
        app.register_blueprint(leave_bp)
        app.register_blueprint(reports_bp)
        app.register_blueprint(employee_bp)
        logger.info("✓ Blueprints registered")
    except Exception as e:
        logger.error(f"✗ Failed to register blueprints: {e}")
    
    # JWT Error handlers
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return jsonify({'success': False, 'message': 'Token kadaluarsa'}), 401
    
    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return jsonify({'success': False, 'message': 'Token tidak valid'}), 401
    
    @jwt.unauthorized_loader
    def missing_token_callback(error):
        return jsonify({'success': False, 'message': 'Token diperlukan'}), 401
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(e):
        if request.path.startswith('/api'):
            return jsonify({'success': False, 'message': 'Endpoint tidak ditemukan'}), 404
        try:
            return send_from_directory(app.static_folder, 'index.html')
        except:
            return jsonify({'success': False, 'message': 'Frontend not found'}), 404
    
    @app.errorhandler(500)
    def server_error(e):
        logger.error(f"Server error: {e}")
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False, 
            'message': 'Terjadi kesalahan server',
            'error': str(e)
        }), 500
    
    # Health check - SIMPLE VERSION
    @app.route('/api/health')
    def health_check():
        result = {
            'status': 'running',
            'timestamp': datetime.now().isoformat(),
            'version': '1.0.0',
            'database': 'unknown'
        }
        
        try:
            db.session.execute(db.text('SELECT 1'))
            db.session.commit()
            result['database'] = 'connected'
        except Exception as e:
            result['database'] = f'error: {str(e)}'
            logger.error(f"Database health check failed: {e}")
        
        return jsonify(result), 200
    
    # Debug endpoint
    @app.route('/api/debug')
    def debug_info():
        return jsonify({
            'env': os.getenv('FLASK_ENV', 'not set'),
            'database_url_set': bool(os.getenv('DATABASE_URL')),
            'secret_key_set': bool(os.getenv('SECRET_KEY')),
            'jwt_secret_set': bool(os.getenv('JWT_SECRET_KEY')),
            'static_folder': app.static_folder,
            'static_exists': os.path.exists(app.static_folder) if app.static_folder else False
        }), 200
    
    # Serve frontend
    @app.route('/')
    def serve_index():
        try:
            return send_from_directory(app.static_folder, 'index.html')
        except Exception as e:
            logger.error(f"Error serving index: {e}")
            return jsonify({
                'message': 'Sistem Absensi Karyawan API',
                'health': '/api/health',
                'debug': '/api/debug'
            }), 200
    
    @app.route('/<path:path>')
    def serve_static(path):
        try:
            if app.static_folder and os.path.exists(os.path.join(app.static_folder, path)):
                return send_from_directory(app.static_folder, path)
            return send_from_directory(app.static_folder, 'index.html')
        except:
            return jsonify({'error': 'File not found'}), 404
    
    return app


def init_database(app):
    """Initialize database with tables and sample data"""
    
    with app.app_context():
        try:
            logger.info("Creating database tables...")
            db.create_all()
            logger.info("✓ Tables created")
        except Exception as e:
            logger.error(f"✗ Failed to create tables: {e}")
            return
        
        # Check if already initialized
        try:
            if Company.query.first():
                logger.info("Database already has data")
                return
        except Exception as e:
            logger.error(f"Error checking existing data: {e}")
        
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
            logger.info(f"✓ Company created with ID: {company.id}")
            
            # Create department
            dept = Department(company_id=company.id, name="IT", code="IT")
            db.session.add(dept)
            db.session.flush()
            logger.info(f"✓ Department created with ID: {dept.id}")
            
            # Create office location
            location = OfficeLocation(
                company_id=company.id,
                name="Kantor Pusat",
                latitude=-6.2088,
                longitude=106.8456,
                radius_meters=100
            )
            db.session.add(location)
            logger.info("✓ Office location created")
            
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
            logger.info(f"✓ Admin created with ID: {admin.id}")
            
            # Create leave balance
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
            logger.info("DATABASE INITIALIZED SUCCESSFULLY!")
            logger.info("="*50)
            logger.info("LOGIN CREDENTIALS:")
            logger.info("Admin: admin@contoh.co.id / admin123")
            logger.info("Employee: budi@contoh.co.id / password123")
            logger.info("="*50)
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"✗ Failed to insert data: {e}")
            logger.error(traceback.format_exc())


# Create app
logger.info("Creating application...")
app = create_app()

# Initialize database
logger.info("Initializing database...")
try:
    init_database(app)
except Exception as e:
    logger.error(f"Database init error (non-fatal): {e}")

logger.info("="*50)
logger.info("APPLICATION READY")
logger.info("="*50)

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_ENV') == 'development'
    logger.info(f"Starting server on port {port}...")
    app.run(host='0.0.0.0', port=port, debug=debug)
