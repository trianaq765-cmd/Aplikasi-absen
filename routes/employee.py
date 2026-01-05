"""
Employee Management Routes
CRUD Karyawan (Admin Only)
"""

from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from models import db, Employee, Department, Company, LeaveBalance
from routes import employee_bp
from utils.decorators import admin_required, hr_required


@employee_bp.route('/', methods=['GET'])
@jwt_required()
@hr_required()
def get_all_employees():
    """
    Get semua karyawan
    """
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        search = request.args.get('search', '')
        department_id = request.args.get('department_id', type=int)
        status = request.args.get('status')  # active, inactive
        
        query = Employee.query
        
        if search:
            query = query.filter(
                (Employee.name.ilike(f'%{search}%')) |
                (Employee.nip.ilike(f'%{search}%')) |
                (Employee.email.ilike(f'%{search}%'))
            )
        
        if department_id:
            query = query.filter_by(department_id=department_id)
        
        if status == 'active':
            query = query.filter_by(is_active=True)
        elif status == 'inactive':
            query = query.filter_by(is_active=False)
        
        query = query.order_by(Employee.name.asc())
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        
        return jsonify({
            'success': True,
            'data': [emp.to_dict() for emp in pagination.items],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': pagination.total,
                'pages': pagination.pages
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Terjadi kesalahan: {str(e)}'
        }), 500


@employee_bp.route('/<int:employee_id>', methods=['GET'])
@jwt_required()
@hr_required()
def get_employee(employee_id):
    """
    Get detail karyawan
    """
    try:
        employee = Employee.query.get(employee_id)
        
        if not employee:
            return jsonify({
                'success': False,
                'message': 'Karyawan tidak ditemukan'
            }), 404
        
        return jsonify({
            'success': True,
            'data': employee.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Terjadi kesalahan: {str(e)}'
        }), 500


@employee_bp.route('/<int:employee_id>', methods=['PUT'])
@jwt_required()
@hr_required()
def update_employee(employee_id):
    """
    Update data karyawan
    """
    try:
        employee = Employee.query.get(employee_id)
        
        if not employee:
            return jsonify({
                'success': False,
                'message': 'Karyawan tidak ditemukan'
            }), 404
        
        data = request.get_json()
        
        # Fields yang boleh diupdate
        updatable = [
            'name', 'phone', 'position', 'department_id',
            'role', 'employment_type', 'is_active', 'is_wfh_allowed'
        ]
        
        for field in updatable:
            if field in data:
                setattr(employee, field, data[field])
        
        # Handle join_date
        if 'join_date' in data:
            employee.join_date = datetime.strptime(data['join_date'], '%Y-%m-%d').date()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Data karyawan berhasil diupdate',
            'data': employee.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Terjadi kesalahan: {str(e)}'
        }), 500


@employee_bp.route('/<int:employee_id>', methods=['DELETE'])
@jwt_required()
@admin_required()
def delete_employee(employee_id):
    """
    Soft delete karyawan (set inactive)
    """
    try:
        employee = Employee.query.get(employee_id)
        
        if not employee:
            return jsonify({
                'success': False,
                'message': 'Karyawan tidak ditemukan'
            }), 404
        
        # Soft delete
        employee.is_active = False
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Karyawan berhasil dinonaktifkan'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Terjadi kesalahan: {str(e)}'
        }), 500


@employee_bp.route('/<int:employee_id>/reset-password', methods=['POST'])
@jwt_required()
@admin_required()
def reset_employee_password(employee_id):
    """
    Reset password karyawan
    """
    try:
        employee = Employee.query.get(employee_id)
        
        if not employee:
            return jsonify({
                'success': False,
                'message': 'Karyawan tidak ditemukan'
            }), 404
        
        data = request.get_json()
        new_password = data.get('new_password', 'password123')
        
        employee.set_password(new_password)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Password berhasil direset. Password baru: {new_password}'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Terjadi kesalahan: {str(e)}'
        }), 500


# Department endpoints
@employee_bp.route('/departments', methods=['GET'])
@jwt_required()
def get_departments():
    """
    Get semua departemen
    """
    try:
        departments = Department.query.all()
        
        return jsonify({
            'success': True,
            'data': [{
                'id': d.id,
                'name': d.name,
                'code': d.code,
                'employee_count': d.employees.count()
            } for d in departments]
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Terjadi kesalahan: {str(e)}'
        }), 500


@employee_bp.route('/departments', methods=['POST'])
@jwt_required()
@admin_required()
def create_department():
    """
    Buat departemen baru
    """
    try:
        data = request.get_json()
        
        if not data.get('name'):
            return jsonify({
                'success': False,
                'message': 'Nama departemen wajib diisi'
            }), 400
        
        department = Department(
            company_id=data.get('company_id', 1),
            name=data['name'],
            code=data.get('code')
        )
        
        db.session.add(department)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Departemen berhasil dibuat',
            'data': {
                'id': department.id,
                'name': department.name,
                'code': department.code
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Terjadi kesalahan: {str(e)}'
        }), 500
