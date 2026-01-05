"""
Routes Package Initialization
"""

from flask import Blueprint

# Create blueprints
auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')
attendance_bp = Blueprint('attendance', __name__, url_prefix='/api/attendance')
leave_bp = Blueprint('leave', __name__, url_prefix='/api/leave')
reports_bp = Blueprint('reports', __name__, url_prefix='/api/reports')
employee_bp = Blueprint('employee', __name__, url_prefix='/api/employees')
