import mysql.connector
import cv2
import datetime as dt

def convert_timedelta_to_str(value):
    if isinstance(value, dt.timedelta):
        total_seconds = int(value.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02}:{minutes:02}:{seconds:02}"
    return value

def connect_to_mysql():
    try:
        connection = mysql.connector.connect(
            host="localhost",
            user="root",
            password="Harshit@1324",
            database="attendencesystem"
        )
        if connection.is_connected():
            return connection
    except mysql.connector.Error:
        return None


def check_status(data, attendance):
    status = {}
    for row in data:
        subject_name, start_time, end_time = row
        for col in attendance:
            start, end = col
            if start == start_time:
                status[start_time] = True
                break
            else:
                status[start_time] = False
    return status


def register_in_database(name, rollno, branch, section, phone_no, dob, image, username, password):
    mydb = connect_to_mysql()
    if mydb is None:
        return False
    try:
        cur = mydb.cursor()
        success, encoded_image = cv2.imencode(".jpg", image)
        image_bytes = encoded_image.tobytes()
        sql = """INSERT INTO student_record 
                 (name, roll_no, branch, section, phone_no, dob, student_image, Username, Password) 
                 VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"""
        val = (name, rollno, branch, section, phone_no, dob, image_bytes, username, password)
        cur.execute(sql, val)
        mydb.commit()
        return True
    except Exception:
        return False
    finally:
        cur.close()
        mydb.close()


def mark_attendence(present_students, subject_name, start_time, end_time, date, mode):
    mydb = connect_to_mysql()
    if mydb is None:
        print("Cannot connect to database!")
    try:
        for key, value in present_students.items():
            cur = mydb.cursor()
            cur.execute("SELECT name FROM student_record WHERE roll_no=%s", (key,))
            name = cur.fetchone()
            cur.close()
            if name is None:
                continue
            cur = mydb.cursor()
            sql = """INSERT INTO student_attendence
                     (roll_no, Date, suject_name, start_time, end_time, name, mode, Marked_status) 
                     VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"""
            val = (key, date, subject_name, start_time, end_time, name[0], mode, 'P' if value else 'A')
            cur.execute(sql, val)
            mydb.commit()
            cur.close()
            cur = mydb.cursor()
            cur.execute("UPDATE student_record SET total_classes=total_classes+1 WHERE roll_no=%s", (key,))
            mydb.commit()
            cur.close()
            if value:
                cur = mydb.cursor()
                cur.execute("UPDATE student_record SET present=present+1 WHERE roll_no=%s", (key,))
                mydb.commit()
                cur.close()
    except Exception:
        print("some error occured!")
    finally:
        mydb.close()


def get_student_images():
    mydb = connect_to_mysql()
    if mydb is None:
        return []
    try:
        cur = mydb.cursor()
        cur.execute("SELECT roll_no, student_image FROM student_record")
        images = cur.fetchall()
        cur.close()
        return images
    except Exception:
        return []
    finally:
        mydb.close()


def check_access(role, username, password):
    mydb = connect_to_mysql()
    if mydb is None:
        return "Database connection error"
    try:
        cur = mydb.cursor()
        if role == 'student':
            cur.execute("SELECT roll_no, Username, Password FROM student_record WHERE Username = %s", (username,))
            data = cur.fetchone()
            if not data:
                return "Username not found"
            if data[2] == password:
                return data[0]
            else:
                return "Password is wrong"
        else:
            cur.execute("SELECT * FROM teacher_record WHERE teacher_Username = %s", (username,))
            data = cur.fetchone()
            if not data:
                return "Username not found"
            if data[2] == password:
                return "Grant Access"
            else:
                return "Password is wrong"
    finally:
        cur.close()
        mydb.close()


def get_student_roll_no(username):
    mydb = connect_to_mysql()
    if mydb is None:
        return None
    try:
        cur = mydb.cursor()
        cur.execute("SELECT roll_no FROM student_record WHERE Username = %s", (username,))
        data = cur.fetchone()
        if data:
            return data[0]
        else:
            return None
    finally:
        cur.close()
        mydb.close()


def get_student_by_id(username):
    mydb = connect_to_mysql()
    if mydb is None:
        return None
    try:
        cur = mydb.cursor()
        cur.execute(
            "SELECT name, roll_no, branch, section, phone_no, dob, Username FROM student_record WHERE Username = %s",
            (username,)
        )
        data = cur.fetchone()
        if not data:
            return None
        student_dict = {
            'name': data[0],
            'roll_no': data[1],
            'branch': data[2],
            'section': data[3],
            'phone_no': data[4],
            'dob': data[5],
            'username': data[6]
        }
        return student_dict
    finally:
        cur.close()
        mydb.close()


def get_today_attendance_by_username(username):
    mydb = connect_to_mysql()
    if mydb is None:
        return None
    try:
        cur = mydb.cursor()
        date = dt.datetime.today().date()
        roll_no = get_student_roll_no(username)
        cur.execute(
            "SELECT start_time, end_time, suject_name, Marked_status FROM student_attendence WHERE Date=%s AND roll_no=%s",
            (date, roll_no))
        data = cur.fetchall()
        data_list=[]
        for row in data:
            start_time,end_time,subject_name,Marked_status=row
            temp={
                'start_time':start_time,
                'end_time':end_time,
                'subject_name':subject_name,
                'Marked_status':Marked_status
            }
            data_list.append(temp)
        return data_list
    finally:
        cur.close()
        mydb.close()


def get_semester_attendance(username):
    mydb = connect_to_mysql()
    if mydb is None:
        return []
    try:
        cur = mydb.cursor()
        cur.execute("SELECT total_classes, present, semester_no FROM student_record WHERE Username = %s", (username,))
        data = cur.fetchall()
        attendance = []
        for total_classes, present, semester_no in data:
            percentage = (present / total_classes) * 100 if total_classes != 0 else 0
            attendance.append({'semester_number': semester_no, 'percentage': percentage})
        return attendance
    finally:
        cur.close()
        mydb.close()


def get_datewise_attendance(roll_no, startdate, enddate):
    mydb = connect_to_mysql()
    if mydb is None:
        return []
    try:
        cur = mydb.cursor()
        start_date_obj = dt.datetime.strptime(startdate, "%Y-%m-%d").date()
        end_date_obj = dt.datetime.strptime(enddate, "%Y-%m-%d").date()

        query = """SELECT start_time, end_time, suject_name, Marked_status
                   FROM student_attendence
                   WHERE roll_no = %s AND Date >= %s AND Date <= %s"""
        cur.execute(query, (roll_no, start_date_obj, end_date_obj))
        data = cur.fetchall()

        result = []
        for start_time, end_time, subject, status in data:
            start_str = start_time.strftime('%H:%M:%S') if hasattr(start_time, 'strftime') else str(start_time)
            end_str = end_time.strftime('%H:%M:%S') if hasattr(end_time, 'strftime') else str(end_time)
            result.append({
                'start_time': start_str,
                'end_time': end_str,
                'subject_name': subject,
                'Marked_status': status
            })
        return result
    finally:
        cur.close()
        mydb.close()


def classes(username):
    mydb = connect_to_mysql()
    if mydb is None:
        return []
    try:
        cur = mydb.cursor()
        day = dt.date.today().strftime("%A")
        cur.execute(
            "SELECT section, subject_name, start_time, end_time FROM time_table WHERE teacher_Username = %s AND day = %s",
            (username, day))
        data = cur.fetchall()

        result = []
        for section, class_name, start, end in data:
            start_str = start.strftime('%H:%M') if hasattr(start, 'strftime') else str(start)
            end_str = end.strftime('%H:%M') if hasattr(end, 'strftime') else str(end)
            result.append({
                'section': section,
                'className': class_name,
                'start': start_str,
                'end': end_str
            })
        return result
    finally:
        cur.close()
        mydb.close()


def get_attendance(roll_no):
    mydb = connect_to_mysql()
    if mydb is None:
        return None
    try:
        cur = mydb.cursor(buffered=True)
        cur.execute("SELECT name FROM student_attendence WHERE roll_no = %s", (roll_no,))
        student_name_result = cur.fetchone()
        if not student_name_result:
            return None
        student_name = student_name_result[0]
    finally:
        cur.close()

    try:
        cur = mydb.cursor(buffered=True)
        cur.execute(
            "SELECT Date, suject_name, start_time, end_time, Marked_status FROM student_attendence WHERE roll_no = %s",
            (roll_no,))
        data = cur.fetchall()

        attendance_records = []
        for date_val, subject_name, start_time, end_time, status in data:
            start_str = start_time.strftime('%H:%M') if hasattr(start_time, 'strftime') else str(start_time)
            end_str = end_time.strftime('%H:%M') if hasattr(end_time, 'strftime') else str(end_time)
            attendance_records.append({
                'date': date_val.strftime('%Y-%m-%d'),
                'subject_name': subject_name,
                'start_time': start_str,
                'end_time': end_str,
                'status': status
            })
        return {
            'name': student_name,
            'records': attendance_records
        }
    finally:
        cur.close()
        mydb.close()

def students():
    mydb = connect_to_mysql()
    if mydb is None:
        return None
    try:
        cur = mydb.cursor(buffered=True)
        cur.execute("SELECT name, roll_no, branch, section, phone_no FROM student_record")
        data = cur.fetchall()
        students_details = []
        for row in data:
            name, roll_no, branch, section, phone_no = row
            students_details.append({
                'name': name,
                'roll_no': roll_no,
                'branch': branch,
                'section': section,
                'phone_no': phone_no
            })
        return students_details
    finally:
        cur.close()
        mydb.close()


def get_today_attendance(start_time, end_time):
    mydb = connect_to_mysql()
    if mydb is None:
        return None
    try:
        cur = mydb.cursor(buffered=True)
        date = dt.datetime.today().date()
        cur.execute("SELECT roll_no, Marked_status FROM student_attendence WHERE start_time=%s AND end_time=%s AND Date=%s",
                    (start_time, end_time, date))
        data = cur.fetchall()
        attendance = {}
        for row in data:
            roll_no, Marked_status = row
            attendance[roll_no] = True if Marked_status == 'P' else False
        return attendance
    finally:
        cur.close()
        mydb.close()


def get_lecture(start_time, end_time):
    mydb = connect_to_mysql()
    if mydb is None:
        return None
    try:
        cur = mydb.cursor(buffered=True)
        day = dt.date.today().strftime("%A")
        cur.execute(
            "SELECT subject_name, teacher_name FROM time_table WHERE start_time=%s AND end_time=%s AND day=%s",
            (start_time, end_time, day))
        data = cur.fetchone()
        if data:
            subject_name, faculty = data
            return {'subject_name': subject_name, 'start_time': start_time, 'end_time': end_time, 'faculty': faculty}
        return None
    finally:
        cur.close()
        mydb.close()


def get_all_attendance(present_students):
    mydb = connect_to_mysql()
    if mydb is None:
        return None
    try:
        cur = mydb.cursor(buffered=True)
        cur.execute("SELECT roll_no FROM student_record")
        data = cur.fetchall()
        for row in data:
            roll_no = str(row[0])
            if not present_students.get(roll_no, False):
                present_students[roll_no] = False
        return present_students
    finally:
        cur.close()
        mydb.close()


def update_attendance(attendance, start_time, end_time, date, mode):
    mydb = connect_to_mysql()
    if mydb is None:
        return None
    try:
        for key, value in attendance.items():
            cur = mydb.cursor(buffered=True)
            val = ('P' if value else 'A', mode, key, start_time, end_time, date)
            cur.execute("UPDATE student_attendence SET Marked_status=%s, mode=%s WHERE roll_no=%s AND start_time=%s AND end_time=%s AND Date=%s", val)
            mydb.commit()
            cur.close()
            cur = mydb.cursor(buffered=True)
            if(value):
                cur.execute("UPDATE student_record SET present=present+1 WHERE roll_no=%s",(key,))
            else:
                cur.execute("UPDATE student_record SET present=present-1 WHERE roll_no=%s",(key,))
            mydb.commit()
            cur.close()
    finally:
        mydb.close()

def get_time_table():
    mydb = connect_to_mysql()
    if mydb is None:
        return None
    
    data_dict={}

    try:
        days=['Monday','Tuesday','Wednesday','Thursday','Friday']
        for i in days:
            cur = mydb.cursor(buffered=True)
            day_list=[]
            cur.execute("SELECT start_time,end_time,subject_name,teacher_name FROM time_table WHERE day=%s",(i,))
            data=cur.fetchall()
            if data:
                for j in data:
                    temp={
                        'start':convert_timedelta_to_str(j[0]),
                        'end':convert_timedelta_to_str(j[1]),
                        'subject':j[2],
                        'faculty':j[3]
                    }
                    day_list.append(temp)
                data_dict[i]=day_list
            cur.close()
        return data_dict
    finally:
        mydb.close()

def update_location(latitude,longitude,username):
    mydb = connect_to_mysql()
    if mydb is None:
        print("Not connected to database")
        return
    cur=mydb.cursor(buffered=True)

    try:
        print(latitude,longitude)
        cur.execute("UPDATE teacher_record SET latitude=%s,longitude=%s WHERE teacher_Username=%s",(latitude,longitude,username))
        mydb.commit()
    finally:
        cur.close()
        mydb.close()