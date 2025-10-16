# attendance_supabase.py
from db_supabase import supabase, BUCKET, cv2_to_jpg_bytes, hash_password, check_password
import datetime as dt
from typing import Dict, List, Any, Optional

# ---------- Registration ----------
def register_in_database(name, rollno, branch, section, phone_no, dob, image, username, password):
    file_bytes = cv2_to_jpg_bytes(image)
    if not file_bytes:
        return {"success": False, "error": "Image conversion failed"}

    path = f"{rollno}.jpg"
    upload_res = supabase.storage.from_(BUCKET).upload(path, file_bytes, {"upsert": True})
    if upload_res.get("error"):
        return {"success": False, "error": f"Upload failed: {upload_res['error']}"}

    payload = {
        "roll_no": str(rollno),
        "name": name,
        "branch": branch,
        "section": section,
        "phone_no": phone_no,
        "dob": dob,
        "image_path": path,
        "username": username,
        "password_hash": hash_password(password),
        "total_classes": 0,
        "present": 0,
        "semester_no": 1
    }
    res = supabase.table("student_record").upsert(payload).execute()
    if getattr(res, "error", None):
        return {"success": False, "error": f"DB insert failed: {res.error}"}

    return {"success": True, "roll_no": rollno}

# ---------- Access / Auth ----------
def check_access(role, username, password):
    """
    For students: returns roll_no if correct, otherwise error message.
    For teachers: returns "Grant Access" or error strings.
    """
    if role == 'student':
        q = supabase.table("student_record").select("roll_no, password_hash").eq("username", username).limit(1).execute()
        if q.error or not q.data:
            return "Username not found"
        row = q.data[0]
        if check_password(password, row["password_hash"]):
            return row["roll_no"]
        else:
            return "Password is wrong"
    else:
        q = supabase.table("teacher_record").select("teacher_Username, password_hash").eq("teacher_Username", username).limit(1).execute()
        if q.error or not q.data:
            return "Username not found"
        row = q.data[0]
        if check_password(password, row["password_hash"]):
            return "Grant Access"
        else:
            return "Password is wrong"

# ---------- Get student (profile) ----------
def get_student_by_id(username):
    q = supabase.table("student_record").select("name, roll_no, branch, section, phone_no, dob, username, image_path").eq("username", username).limit(1).execute()
    if q.error or not q.data:
        return None
    data = q.data[0]
    student_dict = {
        'name': data['name'],
        'roll_no': data['roll_no'],
        'branch': data['branch'],
        'section': data['section'],
        'phone_no': data['phone_no'],
        'dob': str(data['dob']) if data.get('dob') else None,
        'username': data['username'],
        'image_path': data.get('image_path')
    }
    return student_dict

# ---------- Get student roll number ----------
def get_student_roll_no(username):
    q = supabase.table("student_record").select("roll_no").eq("username", username).limit(1).execute()
    if q.error or not q.data:
        return None
    return q.data[0]["roll_no"]

# ---------- Get student images for recognition ----------
def get_student_images():
    """
    Returns list of tuples: (roll_no, cv2_image)
    """
    q = supabase.table("student_record").select("roll_no, image_path").execute()
    if q.error or not q.data:
        return []
    out = []
    for r in q.data:
        path = r.get("image_path")
        roll = r.get("roll_no")
        if not path:
            continue
        img = supabase.storage.from_(BUCKET).download(path)
        if not img:
            continue
        # convert bytes -> cv2
        import numpy as np, cv2
        arr = np.frombuffer(img, dtype=np.uint8)
        cv_img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        out.append((str(roll), cv_img))
    return out

# ---------- Mark attendance (bulk insert) ----------
def mark_attendence(present_students: Dict[str, bool], subject_name: str, start_time, end_time, date, mode):
    """
    Bulk-insert attendance rows into student_attendance table.
    Use Postgres trigger to increment student counters (recommended).
    """
    rows = []
    for roll, present in present_students.items():
        rows.append({
            "roll_no": str(roll),
            "date": date,
            "subject_name": subject_name,
            "start_time": start_time,
            "end_time": end_time,
            "name": None,
            "mode": mode,
            "marked_status": 'P' if present else 'A'
        })
    res = supabase.table("student_attendance").insert(rows).execute()
    if getattr(res, "error", None):
        print("Error inserting attendance:", res.error)
        return False
    return True

# ---------- Get today's attendance for a given slot ----------
def get_today_attendance(start_time, end_time):
    date = dt.date.today().isoformat()
    q = supabase.table("student_attendance").select("roll_no, marked_status").eq("date", date).eq("start_time", start_time).eq("end_time", end_time).execute()
    if q.error:
        return None
    attendance = {}
    for r in q.data:
        attendance[str(r["roll_no"])] = True if r["marked_status"] == 'P' else False
    return attendance

# ---------- Update attendance (manual corrections) ----------
def update_attendance(attendance: Dict[str,bool], start_time, end_time, date, mode):
    # Update each row; this implementation issues an update per student.
    # If you have many students, consider using a SQL function or batch operations.
    for roll, present in attendance.items():
        status = 'P' if present else 'A'
        res = supabase.table("student_attendance").update({"marked_status": status, "mode": mode}).eq("roll_no", roll).eq("start_time", start_time).eq("end_time", end_time).eq("date", date).execute()
        if getattr(res, "error", None):
            print("Failed updating", roll, res.error)
    return True

# ---------- Get attendance for a student ----------
def get_attendance(roll_no):
    # fetch name from student_record
    r = supabase.table("student_record").select("name").eq("roll_no", roll_no).limit(1).execute()
    if r.error or not r.data:
        return None
    name = r.data[0]["name"]
    rows = supabase.table("student_attendance").select("date, subject_name, start_time, end_time, marked_status").eq("roll_no", roll_no).execute()
    if rows.error:
        return {"name": name, "records": []}
    recs = []
    for row in rows.data:
        recs.append({
            "date": str(row["date"]),
            "subject_name": row["subject_name"],
            "start_time": str(row["start_time"]),
            "end_time": str(row["end_time"]),
            "status": row["marked_status"]
        })
    return {"name": name, "records": recs}

# ---------- Classes (teacher timetable for the day) ----------
def classes(username):
    day = dt.date.today().strftime("%A")
    rows = supabase.table("time_table").select("section, subject_name, start_time, end_time").eq("teacher_Username", username).eq("day", day).execute()
    if rows.error:
        return []
    result = []
    for r in rows.data:
        result.append({
            "section": r["section"],
            "className": r["subject_name"],
            "start": str(r["start_time"]),
            "end": str(r["end_time"])
        })
    return result

# ---------- Students list ----------
def students():
    rows = supabase.table("student_record").select("name, roll_no, branch, section, phone_no").execute()
    if rows.error:
        return None
    result = []
    for r in rows.data:
        result.append({
            "name": r["name"],
            "roll_no": r["roll_no"],
            "branch": r.get("branch"),
            "section": r.get("section"),
            "phone_no": r.get("phone_no")
        })
    return result

# ---------- Datewise attendance ----------
def get_datewise_attendance(roll_no, startdate, enddate):
    rows = supabase.table("student_attendance").select("start_time, end_time, subject_name, marked_status").eq("roll_no", roll_no).gte("date", startdate).lte("date", enddate).execute()
    if rows.error:
        return []
    out = []
    for r in rows.data:
        out.append({
            "start_time": str(r["start_time"]),
            "end_time": str(r["end_time"]),
            "subject_name": r["subject_name"],
            "Marked_status": r["marked_status"]
        })
    return out

# ---------- Get time table (all weekdays) ----------
def get_time_table():
    days = ['Monday','Tuesday','Wednesday','Thursday','Friday']
    data_dict = {}
    for d in days:
        rows = supabase.table("time_table").select("start_time, end_time, subject_name, teacher_name").eq("day", d).execute()
        if rows.error or not rows.data:
            continue
        day_list = []
        for r in rows.data:
            day_list.append({
                "start": str(r["start_time"]),
                "end": str(r["end_time"]),
                "subject": r["subject_name"],
                "faculty": r["teacher_name"]
            })
        data_dict[d] = day_list
    return data_dict

# ---------- Update location ----------
def update_location(latitude, longitude, username):
    res = supabase.table("teacher_record").update({"latitude": latitude, "longitude": longitude}).eq("teacher_Username", username).execute()
    if getattr(res, "error", None):
        print("error updating location:", res.error)

