from db_supabase import supabase, BUCKET, cv2_to_jpg_bytes, hash_password, check_password
import datetime as dt
from typing import Dict, List, Any, Optional
import numpy as np
import cv2

# ---------- Registration ----------
def register_in_database(name, rollno, branch, section, phone_no, dob, image, username, password):
    # Convert image to bytes
    file_bytes = cv2_to_jpg_bytes(image)
    if not file_bytes:
        return {"success": False, "error": "Image conversion failed"}

    # File path in bucket
    path = f"{rollno}.jpg"

    # Upload to Supabase storage
    try:
        upload_res = supabase.storage.from_(BUCKET).upload(
            path,
            file_bytes,
            file_options={"upsert": "true"}  # ✅ must be a string
        )
    except Exception as e:
        return {"success": False, "error": f"Upload exception: {e}"}

    # If the upload returned an error field
    if isinstance(upload_res, dict) and upload_res.get("error"):
        return {"success": False, "error": f"Upload failed: {upload_res['error']}"}

    # Prepare data for student_record table
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

    # Insert or update record
    try:
        res = supabase.table("student_record").upsert(payload).execute()
    except Exception as e:
        return {"success": False, "error": f"DB insert exception: {e}"}

    if getattr(res, "status_code", None) not in (200, 201, 204):
        return {"success": False, "error": f"DB insert failed, status: {res.status_code}"}

    return {"success": True, "roll_no": rollno}

# ---------- Access / Auth ----------
def check_access(role, username, password):
    try:
        if role == 'student':
            res = supabase.table("student_record") \
                .select("roll_no, password_hash") \
                .eq("username", username) \
                .limit(1) \
                .execute()

            data = getattr(res, "data", None)  # handle Supabase APIResponse format
            if not data or len(data) == 0:
                return "Username not found"

            row = data[0]
            if check_password(password, row["password_hash"]):
                return row["roll_no"]
            else:
                return "Password is wrong"

        else:  # teacher
            res = supabase.table("teacher_record") \
                .select("teacher_username, password_hash") \
                .eq("teacher_username", username) \
                .limit(1) \
                .execute()

            data = getattr(res, "data", None)
            if not data or len(data) == 0:
                return "Username not found"

            row = data[0]
            if check_password(password, row["password_hash"]):
                return "Grant Access"
            else:
                return "Password is wrong"

    except Exception as e:
        print("Error in check_access:", e)
        import traceback; traceback.print_exc()
        return "Server error"


# ---------- Get student (profile) ----------
def get_student_by_id(username):
    res = supabase.table("student_record").select(
        "name, roll_no, branch, section, phone_no, dob, username, image_path"
    ).eq("username", username).limit(1).execute()

    if res.status_code != 200 or not res.data:
        return None

    data = res.data[0]
    return {
        'name': data['name'],
        'roll_no': data['roll_no'],
        'branch': data['branch'],
        'section': data['section'],
        'phone_no': data['phone_no'],
        'dob': str(data['dob']) if data.get('dob') else None,
        'username': data['username'],
        'image_path': data.get('image_path')
    }

# ---------- Get student roll number ----------
def get_student_roll_no(username):
    res = supabase.table("student_record").select("roll_no").eq("username", username).limit(1).execute()
    if res.status_code != 200 or not res.data:
        return None
    return res.data[0]["roll_no"]

# ---------- Get student images for recognition ----------
def get_student_images():
    res = supabase.table("student_record").select("roll_no, image_path").execute()
    if res.status_code != 200 or not res.data:
        return []

    out = []
    for r in res.data:
        path = r.get("image_path")
        roll = r.get("roll_no")
        if not path:
            continue
        img_bytes = supabase.storage.from_(BUCKET).download(path)
        if not img_bytes:
            continue
        arr = np.frombuffer(img_bytes, dtype=np.uint8)
        cv_img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        out.append((str(roll), cv_img))
    return out

# ---------- Mark attendance (bulk insert) ----------
def mark_attendence(present_students: Dict[str, bool], subject_name: str, start_time, end_time, date, mode):
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
    if res.status_code != 200:
        print("Error inserting attendance, status:", res.status_code)
        return False
    return True

# ---------- Get today's attendance ----------
def get_today_attendance(start_time, end_time):
    date = dt.date.today().isoformat()
    res = supabase.table("student_attendance").select("roll_no, marked_status").eq("date", date).eq("start_time", start_time).eq("end_time", end_time).execute()
    if res.status_code != 200:
        return None
    return {str(r["roll_no"]): r["marked_status"] == 'P' for r in res.data}

# ---------- Update attendance ----------
def update_attendance(attendance: Dict[str,bool], start_time, end_time, date, mode):
    for roll, present in attendance.items():
        status = 'P' if present else 'A'
        res = supabase.table("student_attendance").update({"marked_status": status, "mode": mode}).eq("roll_no", roll).eq("start_time", start_time).eq("end_time", end_time).eq("date", date).execute()
        if res.status_code != 200:
            print("Failed updating", roll, "status:", res.status_code)
    return True

# ---------- Get attendance for a student ----------
def get_attendance(roll_no):
    r = supabase.table("student_record").select("name").eq("roll_no", roll_no).limit(1).execute()
    if r.status_code != 200 or not r.data:
        return None
    name = r.data[0]["name"]

    rows = supabase.table("student_attendance").select("date, subject_name, start_time, end_time, marked_status").eq("roll_no", roll_no).execute()
    if rows.status_code != 200:
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
    if rows.status_code != 200 or not rows.data:
        return []
    return [{"section": r["section"], "className": r["subject_name"], "start": str(r["start_time"]), "end": str(r["end_time"])} for r in rows.data]

# ---------- Students list ----------
def students():
    rows = supabase.table("student_record").select("name, roll_no, branch, section, phone_no").execute()
    if rows.status_code != 200 or not rows.data:
        return []
    return [{"name": r["name"], "roll_no": r["roll_no"], "branch": r.get("branch"), "section": r.get("section"), "phone_no": r.get("phone_no")} for r in rows.data]

# ---------- Datewise attendance ----------
def get_datewise_attendance(roll_no, startdate, enddate):
    rows = supabase.table("student_attendance").select("start_time, end_time, subject_name, marked_status").eq("roll_no", roll_no).gte("date", startdate).lte("date", enddate).execute()
    if rows.status_code != 200 or not rows.data:
        return []
    return [{"start_time": str(r["start_time"]), "end_time": str(r["end_time"]), "subject_name": r["subject_name"], "Marked_status": r["marked_status"]} for r in rows.data]

# ---------- Get time table ----------
def get_time_table():
    days = ['Monday','Tuesday','Wednesday','Thursday','Friday']
    data_dict = {}
    for d in days:
        rows = supabase.table("time_table").select("start_time, end_time, subject_name, teacher_name").eq("day", d).execute()
        if rows.status_code != 200 or not rows.data:
            continue
        data_dict[d] = [{"start": str(r["start_time"]), "end": str(r["end_time"]), "subject": r["subject_name"], "faculty": r["teacher_name"]} for r in rows.data]
    return data_dict

# ---------- Update location ----------
def update_location(latitude, longitude, username):
    res = supabase.table("teacher_record").update({"latitude": latitude, "longitude": longitude}).eq("teacher_Username", username).execute()
    if res.status_code != 200:
        print("Error updating location, status:", res.status_code)




