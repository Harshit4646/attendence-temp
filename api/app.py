from flask import Flask, render_template, request, redirect, jsonify, session
import register_face
from attendance import attendance
import attendance_supabase
from datetime import timedelta, datetime, timezone
from qr_attendence import generate_qr_code
import os
from flask_cors import CORS

app = Flask(__name__)
app.secret_key = "12345678"
CORS(app, origins=["https://your-vercel-frontend-domain.vercel.app"])

def convert_timedelta_to_str(value):
    if isinstance(value, timedelta):
        total_seconds = int(value.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02}:{minutes:02}:{seconds:02}"
    return value

@app.route('/api/mark_attendance_by_camera',methods=['GET','POST'])
def mark_attendance():
    try:
        data=request.get_json()
        student_images = attendance_supabase.get_student_images()
        present_students = attendance(student_images)
        date = datetime.today().date()
        attendance_supabase.mark_attendence(present_students, data.get('subject_name'),data.get('start_time'),data.get('end_time'),date, "camera")
        return jsonify({'messege':'attendance marked'})
    except Exception:
        pass

@app.route('/api/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        data = request.get_json()
        if not data:
            return "Invalid data", 400
        
        name = data.get('name')
        rollno = data.get('rollno')
        branch = data.get('branch')
        section = data.get('section')
        phone = data.get('phone')
        dob = data.get('dob')
        username = data.get('username')
        password = data.get('password')
        
        if None in (name, rollno, branch, section, phone, dob, username, password):
            return "Missing required fields", 400

        image = register_face.register_face(rollno)
        if image is None:
            return "Face registration failed", 400
        reg_success = attendance_supabase.register_in_database(name, rollno, branch,section, phone, dob,image, username, password)
        if reg_success:
            return f"Registration successful for {name} (Roll No: {rollno})!"
        else:
            return "Registration failed", 500
    return render_template('register.html')

@app.route('/api/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        role = request.form.get('role')
        if not username or not password or not role:
            error = "All fields are required"
            return render_template('login.html', error=error)
        value = attendance_supabase.check_access(role, username, password)
        if value not in ["Password is wrong", "Username not found"]:
            if role == 'student':
                session['username'] = username
                return redirect('/student_home_page')
            else:
                session['teacher_Username'] = username
                return redirect('/teacher_home_page')
        else:
            error = value
    return render_template('login.html', error=error)

@app.route('/api/student_home_page')
def student_home_page():
    if 'username' not in session:
        return redirect('/login')
    return render_template('student_home_page.html')

@app.route('/api/student_details')
def student_details():
    username = session.get('username')
    if not username:
        return jsonify({"error": "User not logged in"}), 401
    student = attendance_supabase.get_student_by_id(username)
    if 'dob' in student and student['dob']:
        student['dob'] = student['dob'].strftime("%Y-%m-%d")
    return jsonify(student)

@app.route('/api/attendance/today')
def attendance_today_route():
    username = session.get('username')
    if not username:
        return jsonify({"error": "User not logged in"}), 401
    data = attendance_supabase.get_today_attendance_by_username(username)
    if data is None:
        return jsonify({"message": "No attendance data found for today"}), 404
    def convert_row(row):
        return {k: convert_timedelta_to_str(v) for k, v in row.items()}
    if isinstance(data, list):
        data = [convert_row(row) for row in data]
    elif isinstance(data, dict):
        data = convert_row(data)
    return jsonify(data)

@app.route('/api/attendance/semester')
def attendance_semester_route():
    username = session.get('username')
    if not username:
        return jsonify({"error": "User not logged in"}), 401
    data = attendance_supabase.get_semester_attendance(username)
    return jsonify(data)

@app.route('/api/attendance/datewise')
def attendance_datewise_route():
    username = session.get('username')
    if not username:
        return jsonify({"error": "User not logged in"}), 401
    startdate = request.args.get('start_date')
    enddate = request.args.get('end_date')
    roll_no = attendance_supabase.get_student_roll_no(username)
    data = attendance_supabase.get_datewise_attendance(roll_no, startdate, enddate)
    return jsonify(data)

@app.route('/api/teacher_home_page')
def teacher_home_page():
    if 'teacher_Username' not in session:
        return redirect('/login')
    return render_template('teacher_home_page.html')

@app.route('/api/classes',methods=['GET'])
def classes():
    username = session.get('teacher_Username')
    if not username:
        return jsonify({"error": "User not logged in"}), 401
    classes_list = attendance_supabase.classes(username)
    return jsonify(classes_list)

@app.route('/api/mark_attendance')
def mark():
    return render_template('mark_attendance.html')

@app.route('/api/student_attendance', methods=['GET', 'POST'])
def student_attendance():
    if request.method == 'POST':
        data_dict = request.get_json()
        roll = data_dict.get('roll')
        if not roll:
            return jsonify({"error": "Roll number missing"}), 400
        data = attendance_supabase.get_attendance(roll)
        return jsonify(data)
    return jsonify({"error": "GET method not supported"}), 405

@app.route('/api/details', methods=['POST'])
def details():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data received"}), 400
    session['start_time'] = data.get('start_time')
    session['end_time'] = data.get('end_time')
    return jsonify({'message': 'Data sent successfully'})

@app.route('/api/lecture', methods=['GET','POST'])
def lecture():
    start_time = session.get('start_time')
    end_time = session.get('end_time')
    if not start_time or not end_time:
        return jsonify({"error": "Start and end times not set"}), 400
    lecture_details = attendance_supabase.get_lecture(start_time, end_time)
    session['subject_name'] = lecture_details.get('subject_name')
    return jsonify(lecture_details)

@app.route('/api/students')
def students():
    students_list = attendance_supabase.students()
    return jsonify(students_list)

@app.route('/api/attendance', methods=['GET','POST'])
def attendance_route():
    start_time = session.get('start_time')
    end_time = session.get('end_time')
    attendance_list = attendance_supabase.get_today_attendance(start_time, end_time)
    return jsonify(attendance_list)

@app.route('/api/save_attendance', methods=['POST'])
def save_attendance():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data received"}), 400
    attendance_data = attendance_supabase.get_all_attendance(data)
    date = datetime.today().date()
    attendance_supabase.mark_attendence(attendance_data, session.get('subject_name'),session.get('start_time'), session.get('end_time'),date, 'Manual')
    return jsonify({'message': 'Saved'})

@app.route('/api/update_attendance', methods=['POST'])
def update_attendance():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data received"}), 400
    date = datetime.today().date()
    attendance_supabase.update_attendance(data, session.get('start_time'), session.get('end_time'), date, 'Manual')
    return jsonify({'message': 'Updated'})

@app.route('/api/time_table')
def time_table():
    return render_template('timetable.html',)

@app.route('/api/timetable')
def timetable():
    time_table=attendance_supabase.get_time_table()
    return jsonify(time_table)

@app.route('/api/generate_qr_code', methods=['POST'])
def generate_qr_code_route():
    print("generate_qr_code")
    data = request.get_json()
    start = data.get('start_time')
    end = data.get('end_time')
    subject = data.get('subject_name')
    latitude=data.get('latitude')
    longitude=data.get('longitude')

    if not (start and end and subject):
        return jsonify({"error": "Missing parameters"}), 400
    
    BASE_URL = os.getenv('BASE_URL', 'http://192.168.125.231:5000')
    print(BASE_URL)
    attendance_url = f"{BASE_URL}/attendance_form?start={start}&end={end}"
    session_id_raw = f"{start}_{subject}"
    teacher_username=session['teacher_Username']
    session_id = session_id_raw.replace(":", "-").replace(" ", "_")
    attendance_supabase.update_location(latitude,longitude,teacher_username)
    qr_url = generate_qr_code(attendance_url, session_id)

    return jsonify({
        'qr_url': qr_url,
        'attendance_url': attendance_url,
    })

@app.route('/api/attendance_form')
def attendance_form():
    return render_template('attendance_form.html')

@app.route('/api/verify_and_mark_attendance',methods=['POST'])
def verify_and_mark():
    data=request.get_json()
    start = datetime.strptime(data.get('start_time'), "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc).astimezone()
    end = datetime.strptime(data.get('end_time'), "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc).astimezone()
    start_hour=start.hour
    start_min=start.minute
    start_sec=start.second
    return jsonify({"access_granted":True})

if __name__ == '__main__':
    app.run(debug=True)




