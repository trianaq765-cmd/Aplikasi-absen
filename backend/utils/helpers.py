from datetime import datetime
import pytz
import qrcode
import io
import base64
import calendar

WIB = pytz.timezone('Asia/Jakarta')

def get_wib_now():
    return datetime.now(WIB)

def get_wib_today():
    return datetime.now(WIB).date()

def calculate_late_minutes(clock_in_time, office_start="08:00", tolerance=15):
    start_parts = office_start.split(':')
    start_minutes = int(start_parts[0]) * 60 + int(start_parts[1]) + tolerance
    clock_in_minutes = clock_in_time.hour * 60 + clock_in_time.minute
    late = clock_in_minutes - start_minutes
    return max(0, late)

def generate_qr_code(data):
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    return base64.b64encode(buffer.getvalue()).decode()

def get_working_days_in_month(year, month):
    cal = calendar.Calendar()
    working_days = 0
    for day in cal.itermonthdays2(year, month):
        if day[0] != 0 and day[1] < 5:
            working_days += 1
    return working_days
