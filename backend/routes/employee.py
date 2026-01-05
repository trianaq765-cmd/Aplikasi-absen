from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Employee, Department
from routes import employee_bp

@employee_bp.route('/', methods=['GET'])
@jwt_required()
def get_all():
    try:
        employees = Employee.query.filter_by(is_active=True).all()
        return jsonify({'success': True, 'data': [e.to_dict() for e in employees]}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@employee_bp.route('/departments', methods=['GET'])
@jwt_required()
def get_departments():
    try:
        depts = Department.query.all()
        return jsonify({
            'success': True,
            'data': [{'id': d.id, 'name': d.name, 'code': d.code} for d in depts]
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
