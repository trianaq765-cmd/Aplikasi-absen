"""
Attendance Routes - FIXED with DB Error Handling
"""

from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, date
from sqlalchemy.exc import OperationalError
from models import db, Employee, Attendance
from routes import attendance_bp
from utils.helpers import get_wib_now, get_wib_today, calculate_late_minutes, generate_qr_code
import logging
import time

logger = logging.getLogger(__name__)


def safe_db_query(query_func, max_retries=2):
    """Execute query with retry on connection errors"""
    for attempt in range(max_retries):
        try:
            return query_func()
        except OperationalError as e:
            error_str = str(e).lower()
            if 'ssl' in error_str or 'connection' in error_str or 'eof' in error_str:
                logger.warning(f"DB error (attempt {attempt + 1}): {e}")
                try:
                    db.session.rollback()
                    db.session.remove()
                except:
                    pass
                if attempt < max_retries - 1:
                    time.sleep(1)
                    continue
            raise
    return None


@attendance_bp.route('/clock-in', methods=['POST'])
@jwt_required()
def clock_in():
    try:
        employee_id = get_jwt_identity()
        data = request.get_json()
        
        today = get_wib_today()
        now = get_wib_now()
        
        # Get employee with retry
        employee = safe_db_query(lambda: Employee.query.get(employee_id))
        if not employee:
            return jsonify({'success': False, 'message': 'Karyawan tidak ditemukan'}), 404
        
        # Check existing attendance
        existing = safe_db_query(lambda: Attendance.query.filter_by(
            employee_id=employee_id, date=today
        ).first())
        
        if existing and existing.clock_in:
            return jsonify({
                'success': False,
                'message': 'Anda sudah absen masuk hari ini',
                'data': existing.to_dict()
            }), 400
        
        method = data.get('method', 'manual')
        work_type = data.get('work_type', 'wfo')
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        
        # Check WFH permission
        if work_type == 'wfh' and not employee.is_wfh_allowed:
            return jsonify({'success': False, 'message': 'Anda tidak diizinkan WFH'}), 403
        
        # Calculate late
        late_minutes = calculate_late_minutes(now, "08:00", 15)
        status = 'late' if late_minutes > 0 else 'present'
        
        # Create or update attendance
        if existing:
            existing.clock_in = now
            existing.clock_in_method = method
            existing.clock_in_latitude = latitude
            existing.clock_in_longitude = longitude
            existing.late_minutes = late_minutes
            existing.status = status
            existing.work_type = work_type
            attendance = existing
        else:
            attendance = Attendance(
                employee_id=employee_id,
                date=today,
                clock_in=now,
                clock_in_method=method,
                clock_in_latitude=latitude,
                clock_in_longitude=longitude,
                late_minutes=late_minutes,
                status=status,
                work_type=work_type
            )
            db.session.add(attendance)
        
        db.session.commit()
        
        message = f'Absen masuk berhasil pukul {now.strftime("%H:%M")} WIB'
        if late_minutes > 0:
            message += f'. Terlambat {late_minutes} menit.'
        
        return jsonify({
            'success': True,
            'message': message,
            'data': attendance.to_dict()
        }), 200
        
    except OperationalError as e:
        db.session.rollback()
        logger.error(f"DB error in clock-in: {e}")
        return jsonify({
            'success': False,
            'message': 'Koneksi database bermasalah. Silakan coba lagi.'
        }), 503
    except Exception as e:
        db.session.rollback()
        logger.error(f"Clock-in error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@attendance_bp.route('/clock-out', methods=['POST'])
@jwt_required()
def clock_out():
    try:
        employee_id = get_jwt_identity()
        data = request.get_json()
        
        today = get_wib_today()
        now = get_wib_now()
        
        # Get today's attendance with retry
        attendance = safe_db_query(lambda: Attendance.query.filter_by(
            employee_id=employee_id, date=today
        ).first())
        
        if not attendance or not attendance.clock_in:
            return jsonify({'success': False, 'message': 'Anda belum absen masuk hari ini'}), 400
        
        if attendance.clock_out:
            return jsonify({
                'success': False,
                'message': 'Anda sudah absen pulang hari ini',
                'data': attendance.to_dict()
            }), 400
        
        attendance.clock_out = now
        attendance.clock_out_method = data.get('method', 'manual')
        attendance.clock_out_latitude = data.get('latitude')
        attendance.clock_out_longitude = data.get('longitude')
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Absen pulang berhasil pukul {now.strftime("%H:%M")} WIB',
            'data': attendance.to_dict()
        }), 200
        
    except OperationalError as e:
        db.session.rollback()
        logger.error(f"DB error in clock-out: {e}")
        return jsonify({
            'success': False,
            'message': 'Koneksi database bermasalah. Silakan coba lagi.'
        }), 503
    except Exception as e:
        db.session.rollback()
        logger.error(f"Clock-out error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@attendance_bp.route('/today', methods=['GET'])
@jwt_required()
def get_today():
    try:
        employee_id = get_jwt_identity()
        today = get_wib_today()
        
        attendance = safe_db_query(lambda: Attendance.query.filter_by(
            employee_id=employee_id, date=today
        ).first())
        
        return jsonify({
            'success': True,
            'data': attendance.to_dict() if attendance else None,
            'server_time': get_wib_now().strftime('%Y-%m-%d %H:%M:%S WIB')
        }), 200
        
    except OperationalError as e:
        db.session.rollback()
        logger.error(f"DB error in today: {e}")
        return jsonify({
            'success': False,
            'message': 'Koneksi database bermasalah.'
        }), 503
    except Exception as e:
        logger.error(f"Today error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@attendance_bp.route('/history', methods=['GET'])
@jwt_required()
def get_history():
    try:
        employee_id = get_jwt_identity()
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        
        def get_paginated():
            return Attendance.query.filter_by(
                employee_id=employee_id
            ).order_by(Attendance.date.desc()).paginate(
                page=page, per_page=per_page, error_out=False
            )
        
        pagination = safe_db_query(get_paginated)
        
        if pagination:
            return jsonify({
                'success': True,
                'data': [a.to_dict() for a in pagination.items],
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': pagination.total
                }
            }), 200
        else:
            return jsonify({'success': True, 'data': []}), 200
        
    except Exception as e:
        logger.error(f"History error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@attendance_bp.route('/qr-code', methods=['GET'])
@jwt_required()
def get_qr():
    try:
        employee_id = get_jwt_identity()
        
        employee = safe_db_query(lambda: Employee.query.get(employee_id))
        if not employee:
            return jsonify({'success': False, 'message': 'Karyawan tidak ditemukan'}), 404
        
        today = get_wib_today()
        qr_data = f"ABSEN|{employee_id}|{employee.nip}|{today.isoformat()}"
        qr_base64 = generate_qr_code(qr_data)
        
        return jsonify({
            'success': True,
            'data': {
                'qr_image': f'data:image/png;base64,{qr_base64}',
                'valid_date': today.isoformat(),
                'employee_name': employee.name
            }
        }), 200
        
    except Exception as e:
        logger.error(f"QR error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500        return jsonify({'success': False, 'message': str(e)}), 500
