from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, date
from models import db, Employee, Attendance, LeaveRequest, LeaveBalance
from routes import reports_bp
from utils.helpers import get_working_days_in_month

@reports_bp.route('/dashboard', methods=['GET'])
@jwt_required()
def dashboard():
    try:
        employee_id = get_jwt_identity()
        employee = Employee.query.get(employee_id)
        today = date.today()
        
        # Today's attendance
        today_att = Attendance.query.filter_by(employee_id=employee_id, date=today).first()
        
        # Monthly stats
        from calendar import monthrange
        start = date(today.year, today.month, 1)
        end = date(today.year, today.month, monthrange(today.year, today.month)[1])
        
        attendances = Attendance.query.filter(
            Attendance.employee_id == employee_id,
            Attendance.date >= start,
            Attendance.date <= end
        ).all()
        
        working_days = get_working_days_in_month(today.year, today.month)
        present = sum(1 for a in attendances if a.clock_in)
        late = sum(1 for a in attendances if a.status == 'late')
        wfh = sum(1 for a in attendances if a.work_type == 'wfh')
        
        # Leave balance
        balance = LeaveBalance.query.filter_by(employee_id=employee_id, year=today.year).first()
        
        data = {
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
            total_emp = Employee.query.filter_by(is_active=True).count()
            today_present = Attendance.query.filter(Attendance.date == today, Attendance.clock_in.isnot(None)).count()
            pending = LeaveRequest.query.filter_by(status='pending').count()
            
            data['admin_stats'] = {
                'total_employees': total_emp,
                'today_present': today_present,
                'today_absent': total_emp - today_present,
                'pending_approvals': pending
            }
        
        return jsonify({'success': True, 'data': data}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
