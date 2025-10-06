import os
import qrcode
from flask import url_for, current_app
from datetime import datetime, timezone

def sanitize_filename(s):
    return s.replace(":", "-").replace(" ", "_")

def generate_qr_code(attendance_url, session_id):
    qr = qrcode.QRCode(box_size=10, border=4)
    qr.add_data(attendance_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    qr_folder = os.path.join(current_app.root_path, 'static', 'qrcodes')
    os.makedirs(qr_folder, exist_ok=True)

    session_id_clean = sanitize_filename(session_id)
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')

    filename = f"{session_id_clean}_{timestamp}.png"
    file_path = os.path.join(qr_folder, filename)

    img.save(file_path)

    qr_image_url = url_for('static', filename=f'qrcodes/{filename}', _external=True)
    return qr_image_url