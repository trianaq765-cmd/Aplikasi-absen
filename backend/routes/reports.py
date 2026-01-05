"""
Reports Routes - FIXED with DB Error Handling
"""

from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, date
from calendar import monthrange
from sqlalchemy.exc import OperationalError
from models import db, Employee, Attendance, LeaveRequest, LeaveBalance
from routes import reports_bp
from utils.helpers import get_working_days_in_month
import logging
import time

logger = logging.getLogger(__name__)


def safe_db_query(query_func, max_retries=2):
    """Execute query with retry"""
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


@reports_bp.route('/dashboard', methods=['GET'])
@jwt_required()
def dashboard():
    try:
        employee_id = get_jwt_identity()
        today = date.today()
        
        # Get employee with retry
        employee = safe_db_query(lambda: Employee.query.get(employee_id))
        if not employee:
            return jsonify({'success': False, 'message': 'Karyawan tidak ditemukan'}), 404
        
        # Get today's attendance
        today_att = safe_db_query(lambda: Attendance.query.filter_by(
            employee_id=employee_id, date=today
        ).first())
        
        # Get monthly stats
        year = today.year
        month = today.month
        start = date(year, month, 1)
        end = date(year, month, monthrange(year, month)[1])
        
        attendances = safe_db_query(lambda: Attendance.query.filter(
            Attendance.employee_id == employee_id,
            Attendance.date >= start,
            Attendance.date <= end
        ).all()) or []
        
        working_days = get_working_days_in_month(year, month)
        present = sum(1 for a in attendances if a.clock_in)
        late = sum(1 for a in attendances if a.status == 'late')
        wfh = sum(1 for a in attendances if a.work_type == 'wfh')
        
        # Get leave balance
        balance = safe_db_query(lambda: LeaveBalance.query.filter_by(
            employee_id=employee_id, year=year
        ).first())
        
        result = {
            'today': {
                'date': today.isoformat(),
                'clock_in': today_att.clock_in.strftime('%H:%M') if today_att and today_att.clock_in else None,
                'clock_out': today_att.clock_out.strftime('%H:%M') if today_att and today_att.clock_out else None,
                'status': today_att.status if today_att else 'not_yet'
            },
            'monthly': {
                'working_days': working_days,
                'present': present,
                'late': late,
                'wfh': wfh
            },
            'leave_balance': {
                'remaining': balance.annual_remaining if balance else 12,
                'used': balance.annual_used if balance else 0
            }
        }
        
        # Admin stats
        if employee.role in ['admin', 'hr', 'manager']:
            total_emp = safe_db_query(lambda: Employee.query.filter_by(is_active=True).count()) or 0
            today_present = safe_db_query(lambda: Attendance.query.filter(
                Attendance.date == today,
                Attendance.clock_in.isnot(None)
            ).count()) or 0
            pending = safe_db_query(lambda: LeaveRequest.query.filter_by(status='pending').count()) or 0
            
            result['admin_stats'] = {
                'total_employees': total_emp,
                'today_present': today_present,
                'today_absent': total_emp - today_present,
                'pending_approvals': pending
            }
        
        return jsonify({'success': True, 'data': result}), 200
        
    except OperationalError as e:
        db.session.rollback()
        logger.error(f"DB error in dashboard: {e}")
        return jsonify({
            'success': False,
            'message': 'Koneksi database bermasalah. Silakan refresh halaman.'
        }), 503
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
