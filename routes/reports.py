"""
Reports Routes
Laporan Kehadiran, Export Excel/PDF
"""

from flask import request, jsonify, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, date, timedelta
from models import db, Employee, Attendance, LeaveRequest, AttendanceSummary, Department
from routes import reports_bp
from utils.helpers import get_working_days_in_month
from utils.decorators import hr_required, manager_required
import pandas as pd
import io


@reports_bp.route('/daily', methods=['GET'])
@jwt_required()
@manager_required()
def get_daily_report():
    """
    Laporan harian kehadiran
    """
    try:
        report_date = request.args.get('date', date.today().isoformat())
        department_id = request.args.get('department_id', type=int)
        
        report_date = datetime.strptime(report_date, '%Y-%m-%d').date()
        
        # Query employees
        query = Employee.query.filter_by(is_active=True)
        if department_id:
            query = query.filter_by(department_id=department_id)
        
        employees = query.all()
        
        report_data = []
        summary = {
            'total_employees': len(employees),
            'present': 0,
            'late': 0,
            'absent': 0,
            'leave': 0,
            'wfh': 0
        }
        
        for emp in employees:
            attendance = Attendance.query.filter_by(
                employee_id=emp.id,
                date=report_date
            ).first()
            
            status = 'absent'
            clock_in = None
            clock_out = None
            late_mins = 0
            
            if attendance:
                status = attendance.status
                clock_in = attendance.clock_in.strftime('%H:%M') if attendance.clock_in else None
                clock_out = attendance.clock_out.strftime('%H:%M') if attendance.clock_out else None
                late_mins = attendance.late_minutes or 0
                
                if status == 'present':
                    summary['present'] += 1
                elif status == 'late':
                    summary['late'] += 1
                elif status in ['leave', 'sick']:
                    summary['leave'] += 1
                elif attendance.work_type == 'wfh':
                    summary['wfh'] += 1
            else:
                summary['absent'] += 1
            
            report_data.append({
                'employee_id': emp.id,
                'nip': emp.nip,
                'name': emp.name,
                'department': emp.department.name if emp.department else '-',
                'position': emp.position,
                'clock_in': clock_in,
                'clock_out': clock_out,
                'status': status,
                'late_minutes': late_mins
            })
        
        return jsonify({
            'success': True,
            'data': {
                'date': report_date.isoformat(),
                'summary': summary,
                'details': report_data
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Terjadi kesalahan: {str(e)}'
        }), 500


@reports_bp.route('/monthly', methods=['GET'])
@jwt_required()
@manager_required()
def get_monthly_report():
    """
    Laporan bulanan kehadiran
    """
    try:
        month = request.args.get('month', datetime.now().month, type=int)
        year = request.args.get('year', datetime.now().year, type=int)
        department_id = request.args.get('department_id', type=int)
        
        # Query employees
        query = Employee.query.filter_by(is_active=True)
        if department_id:
            query = query.filter_by(department_id=department_id)
        
        employees = query.all()
        
        # Calculate working days
        working_days = get_working_days_in_month(year, month)
        
        report_data = []
        
        for emp in employees:
            # Get all attendance for month
            from calendar import monthrange
            start_date = date(year, month, 1)
            end_date = date(year, month, monthrange(year, month)[1])
            
            attendances = Attendance.query.filter(
                Attendance.employee_id == emp.id,
                Attendance.date >= start_date,
                Attendance.date <= end_date
            ).all()
            
            # Calculate stats
            present = sum(1 for a in attendances if a.status == 'present' and a.clock_in)
            late = sum(1 for a in attendances if a.status == 'late')
            leave = sum(1 for a in attendances if a.status in ['leave', 'sick'])
            wfh = sum(1 for a in attendances if a.work_type == 'wfh' and a.clock_in)
            total_late_mins = sum(a.late_minutes or 0 for a in attendances)
            total_overtime = sum(a.overtime_minutes or 0 for a in attendances)
            
            absent = working_days - present - late - leave - wfh
            
            report_data.append({
                'employee_id': emp.id,
                'nip': emp.nip,
                'name': emp.name,
                'department': emp.department.name if emp.department else '-',
                'position': emp.position,
                'working_days': working_days,
                'present': present,
                'late': late,
                'absent': max(0, absent),
                'leave': leave,
                'wfh': wfh,
                'total_late_minutes': total_late_mins,
                'total_overtime_minutes': total_overtime,
                'attendance_percentage': round((present + late + wfh) / working_days * 100, 1) if working_days > 0 else 0
            })
        
        return jsonify({
            'success': True,
            'data': {
                'month': month,
                'year': year,
                'working_days': working_days,
                'total_employees': len(employees),
                'details': report_data
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Terjadi kesalahan: {str(e)}'
        }), 500


@reports_bp.route('/export/excel', methods=['GET'])
@jwt_required()
@hr_required()
def export_excel():
    """
    Export laporan ke Excel
    """
    try:
        month = request.args.get('month', datetime.now().month, type=int)
        year = request.args.get('year', datetime.now().year, type=int)
        report_type = request.args.get('type', 'monthly')  # monthly, daily
        
        employees = Employee.query.filter_by(is_active=True).all()
        
        if report_type == 'monthly':
            # Build monthly data
            from calendar import monthrange
            start_date = date(year, month, 1)
            end_date = date(year, month, monthrange(year, month)[1])
            working_days = get_working_days_in_month(year, month)
            
            data = []
            for emp in employees:
                attendances = Attendance.query.filter(
                    Attendance.employee_id == emp.id,
                    Attendance.date >= start_date,
                    Attendance.date <= end_date
                ).all()
                
                present = sum(1 for a in attendances if a.status == 'present' and a.clock_in)
                late = sum(1 for a in attendances if a.status == 'late')
                leave = sum(1 for a in attendances if a.status in ['leave', 'sick'])
                wfh = sum(1 for a in attendances if a.work_type == 'wfh' and a.clock_in)
                total_late_mins = sum(a.late_minutes or 0 for a in attendances)
                
                data.append({
                    'NIP': emp.nip or '-',
                    'Nama': emp.name,
                    'Departemen': emp.department.name if emp.department else '-',
                    'Jabatan': emp.position or '-',
                    'Hari Kerja': working_days,
                    'Hadir': present,
                    'Terlambat': late,
                    'Cuti/Izin': leave,
                    'WFH': wfh,
                    'Tidak Hadir': max(0, working_days - present - late - leave - wfh),
                    'Total Menit Terlambat': total_late_mins,
                    'Persentase Kehadiran (%)': round((present + late + wfh) / working_days * 100, 1) if working_days > 0 else 0
                })
            
            df = pd.DataFrame(data)
            
        else:
            # Daily report
            report_date = request.args.get('date', date.today().isoformat())
            report_date = datetime.strptime(report_date, '%Y-%m-%d').date()
            
            data = []
            for emp in employees:
                attendance = Attendance.query.filter_by(
                    employee_id=emp.id,
                    date=report_date
                ).first()
                
                data.append({
                    'NIP': emp.nip or '-',
                    'Nama': emp.name,
                    'Departemen': emp.department.name if emp.department else '-',
                    'Jam Masuk': attendance.clock_in.strftime('%H:%M') if attendance and attendance.clock_in else '-',
                    'Jam Pulang': attendance.clock_out.strftime('%H:%M') if attendance and attendance.clock_out else '-',
                    'Status': attendance.status if attendance else 'absent',
                    'Terlambat (menit)': attendance.late_minutes if attendance else 0,
                    'Keterangan': attendance.notes if attendance else '-'
                })
            
            df = pd.DataFrame(data)
        
        # Create Excel file
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Laporan Kehadiran')
        
        output.seek(0)
        
        filename = f'laporan_kehadiran_{month}_{year}.xlsx' if report_type == 'monthly' else f'laporan_kehadiran_{report_date}.xlsx'
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Terjadi kesalahan: {str(e)}'
        }), 500


@reports_bp.route('/dashboard', methods=['GET'])
@jwt_required()
def get_dashboard_stats():
    """
    Get statistik untuk dashboard
    """
    try:
        employee_id = get_jwt_identity()
        employee = Employee.query.get(employee_id)
        
        today = date.today()
        current_month = today.month
        current_year = today.year
        
        # Stats for today
        today_attendance = Attendance.query.filter_by(
            employee_id=employee_id,
            date=today
        ).first()
        
        # Monthly stats
        from calendar import monthrange
        start_date = date(current_year, current_month, 1)
        end_date = date(current_year, current_month, monthrange(current_year, current_month)[1])
        
        month_attendances = Attendance.query.filter(
            Attendance.employee_id == employee_id,
            Attendance.date >= start_date,
            Attendance.date <= end_date
        ).all()
        
        working_days = get_working_days_in_month(current_year, current_month)
        present_days = sum(1 for a in month_attendances if a.clock_in)
        late_days = sum(1 for a in month_attendances if a.status == 'late')
        
        # Pending leave requests
        pending_leaves = LeaveRequest.query.filter_by(
            employee_id=employee_id,
            status='pending'
        ).count()
        
        # Leave balance
        from models import LeaveBalance
        leave_balance = LeaveBalance.query.filter_by(
            employee_id=employee_id,
            year=current_year
        ).first()
        
        dashboard_data = {
            'today': {
                'date': today.isoformat(),
                'clock_in': today_attendance.clock_in.strftime('%H:%M') if today_attendance and today_attendance.clock_in else None,
                'clock_out': today_attendance.clock_out.strftime('%H:%M') if today_attendance and today_attendance.clock_out else None,
                'status': today_attendance.status if today_attendance else 'not_yet'
            },
            'monthly': {
                'month': current_month,
                'year': current_year,
                'working_days': working_days,
                'present': present_days,
                'late': late_days,
                'absent': max(0, working_days - present_days),
                'attendance_rate': round(present_days / working_days * 100, 1) if working_days > 0 else 0
            },
            'leave_balance': {
                'remaining': leave_balance.annual_remaining if leave_balance else 12,
                'used': leave_balance.annual_used if leave_balance else 0
            },
            'pending_requests': pending_leaves
        }
        
        # Admin/HR additional stats
        if employee.role in ['admin', 'hr', 'manager']:
            total_employees = Employee.query.filter_by(is_active=True).count()
            today_present = Attendance.query.filter(
                Attendance.date == today,
                Attendance.clock_in.isnot(None)
            ).count()
            
            pending_approvals = LeaveRequest.query.filter_by(status='pending').count()
            
            dashboard_data['admin_stats'] = {
                'total_employees': total_employees,
                'today_present': today_present,
                'today_absent': total_employees - today_present,
                'pending_approvals': pending_approvals
            }
        
        return jsonify({
            'success': True,
            'data': dashboard_data
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Terjadi kesalahan: {str(e)}'
        }), 500
