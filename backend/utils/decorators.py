from functools import wraps
from flask import jsonify
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from models import Employee

def admin_required():
    def wrapper(fn):
        @wraps(fn)
        def decorator(*args, **kwargs):
            verify_jwt_in_request()
            employee = Employee.query.get(get_jwt_identity())
            if not employee or employee.role != 'admin':
                return jsonify({'success': False, 'message': 'Admin only'}), 403
            return fn(*args, **kwargs)
        return decorator
    return wrapper

def active_employee_required():
    def wrapper(fn):
        @wraps(fn)
        def decorator(*args, **kwargs):
            verify_jwt_in_request()
            employee = Employee.query.get(get_jwt_identity())
            if not employee or not employee.is_active:
                return jsonify({'success': False, 'message': 'Akun tidak aktif'}), 403
            return fn(*args, **kwargs)
        return decorator
    return wrapper
