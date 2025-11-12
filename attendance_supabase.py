from db_supabase import supabase, BUCKET, cv2_to_jpg_bytes, hash_password, check_password
import datetime as dt
from typing import Dict, List, Any, Optional
import numpy as np
import cv2

# ---------- Registration ----------
def register_in_database(name, rollno, branch, section, phone_no, dob, image, username, password):
    from pprint import pprint

    file_bytes = cv2_to_jpg_bytes(image)
    if not file_bytes:
        return {"success": False, "error": "Image conversion failed"}

    path = f"{rollno}.jpg"

    # Upload image to Supabase storage bucket
    try:
        upload_res = supabase.storage.from_(BUCKET).upload(path, file_bytes)
        print("UPLOAD RESULT:")
        pprint(upload_res)
    except Exception as e:
        return {"success": False, "error": f"Upload exception: {e}"}

    if isinstance(upload_res, dict) and upload_res.get("error"):
        return {"success": False, "error": f"Upload failed: {upload_res['error']}"}

    # Prepare student record payload
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

    try:
        res = supabase.table("student_record").upsert(payload).execute()
        print("UPSERT RESULT:")
        pprint(res.model_dump())  # works in Supabase-py 2.x
    except Exception as e:
        return {"success": False, "error": f"DB insert exception: {e}"}

    data = getattr(res, "data", None)
    if getattr(res, "error", None) or not data:
        return {"success": False, "error": f"DB insert failed: {getattr(res, 'error', 'Unknown error')}"}

    return {"success": True, "roll_no": rollno}


# ---------- Access / Auth ----------
def check_access(role, username, password):
    try:
        if role == "student":
            res = supabase.table("student_record").select("roll_no, password_hash").eq("username", username).limit(1).execute()
        else:  # teacher
            res = supabase.table("teacher_record").select("teacher_username, password_hash").eq("teacher_username", username).limit(1).execute()

        data = getattr(res, "data", None)
        if not data:
            return "Username not found"

        row = data[0]
        if check_password(password, row["password_hash"]):
            return row.get("roll_no", "Grant Access")
        else:
            return "Password is wrong"

    except Exception as e:
        print("Error in check_access:", e)
        import traceback
        traceback.print_exc()
        return "Server error"


# ---------- Get student (profile) ----------
def get_student_by_id(username):
    try:
        res = supabase.table("student_record").select(
            "name, roll_no, branch, section, phone_no, dob, username, image_path"
        ).eq("username", username).limit(1).execute()

        if getattr(res, "error", None) or not getattr(res, "data", None):
            return None

        data = res.data[0]
        return {
            "name": data["name"],
            "roll_no": data["roll_no"],
            "branch": data["branch"],
            "section": data["section"],
            "phone_no": data["phone_no"],
            "dob": str(data["dob"]) if data.get("dob") else None,
            "username": data["username"],
            "image_path": data.get("image_path")
        }
    except Exception as e:
        print("Error in get_student_by_id:", e)
        return None


# ---------- Get student roll number ----------
def get_student_roll_no(username):
    res = supabase.table("student_record").select("roll_no").eq("username", username).limit(1).execute()
    if getattr(res, "error", None) or not getattr(res, "data", None):
        return None
    return res.data[0]["roll_no"]


# ---------- Get student images for recognition ----------
def get_student_images():
    res = supabase.table("student_record").select("roll_no, image_path").execute()
    if getattr(res, "error", None) or not getattr(res, "data", None):
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
    rows = [
        {
            "roll_no": str(roll),
            "date": date,
            "subject_name": subject_name,
            "start_time": start_time,
            "end_time": end_time,
            "name": None,
            "mode": mode,
            "marked_status": "P" if present else "A"
        }
        for roll, present in present_students.items()
    ]
    res = supabase.table("student_attendance").insert(rows).execute()
    if getattr(res, "error", None):
        print("Error inserting attendance:", res.error)
        return False
    return True


# ---------- Get today's attendance ----------
def get_today_attendance(username):
    date = dt.date.today().isoformat()
    roll_no= get_student_roll_no(username)
    res = supabase.table("student_attendance").select("subject_name, marked_status, start_time, end_time").eq("date", date).eq("roll_no", roll_no).execute()
    if getattr(res, "error", None):
        return None
    return [
            {
            "subject_name":r["subject_name"],
             "start_time":r["start_time"],
             "end_time":r["end_time"],
             "Marked_status":r["Marked_status"]
            }
        for r in res.data
    ]


# ---------- Update attendance ----------
def update_attendance(attendance: Dict[str, bool], start_time, end_time, date, mode):
    for roll, present in attendance.items():
        status = "P" if present else "A"
        res = supabase.table("student_attendance").update(
            {"marked_status": status, "mode": mode}
        ).eq("roll_no", roll).eq("start_time", start_time).eq("end_time", end_time).eq("date", date).execute()
        if getattr(res, "error", None):
            print("Failed updating", roll, ":", res.error)
    return True


# ---------- Get attendance for a student ----------
def get_semester_attendance(roll_no):
    r = supabase.table("student_record").select("total_classes,semester_no,present").eq("roll_no", roll_no).execute()
    if getattr(r, "error", None) or not getattr(r, "data", None):
        return None
    total=r.data[0]["total_classes"]
    present=r.data[0]["present"]
    percent=(present*100)/total
    return {
        "semester_number":r.data[0]["semester_no"],
            "percentage": percent 
           }


# ---------- Classes (teacher timetable for the day) ----------
def classes(username):
    today=dt.date.today()
    day=today.day
    rows = supabase.table("time_table").select("section, subject_name, start_time, end_time").eq("teacher_username", username).eq("day", day).execute()
    data = rows.data
    if getattr(rows,"error", None) or not data:
        return []
    data_list=[]
    for d in rows.data:
        data_dict={
            "section":d["section"],
            "subject_name":d["subject_name"],
            "start_time":d["start_time"],
            "end_time":d["end_time"]
        }
        data_list.append(data_dict)
    return data_list


# ---------- Students list ----------
def students():
    rows = supabase.table("student_record").select("name, roll_no, branch, section, phone_no").execute()
    if getattr(rows, "error", None) or not getattr(rows, "data", None):
        return []
    return [
        {
            "name": r["name"],
            "roll_no": r["roll_no"],
            "branch": r.get("branch"),
            "section": r.get("section"),
            "phone_no": r.get("phone_no")
        }
        for r in rows.data
    ]


# ---------- Datewise attendance ----------
def get_datewise_attendance(roll_no, startdate, enddate):
    rows = supabase.table("student_attendance").select(
        "start_time, end_time, subject_name, marked_status"
    ).eq("roll_no", roll_no).gte("date", startdate).lte("date", enddate).execute()
    if getattr(rows, "error", None) or not getattr(rows, "data", None):
        return []
    return [
        {
            "start_time": str(r["start_time"]),
            "end_time": str(r["end_time"]),
            "subject_name": r["subject_name"],
            "Marked_status": r["marked_status"]
        }
        for r in rows.data
    ]


# ---------- Get time table ----------
def get_time_table():
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    data_dict = {}
    for d in days:
        rows = supabase.table("time_table").select("start_time, end_time, subject_name, teacher_name").eq("day", d).execute()
        if getattr(rows, "error", None) or not getattr(rows, "data", None):
            continue
        data_dict[d] = [
            {
                "start": str(r["start_time"]),
                "end": str(r["end_time"]),
                "subject": r["subject_name"],
                "faculty": r["teacher_name"]
            }
            for r in rows.data
        ]
    return data_dict


# ---------- Update location ----------
def update_location(latitude, longitude, username):
    res = supabase.table("teacher_record").update(
        {"latitude": latitude, "longitude": longitude}
    ).eq("teacher_username", username).execute()
    if getattr(res, "error", None):
        print("Error updating location:", res.error)


def get_attendance(roll_no):
    re = supabase.table("student_record").select("name").eq("roll_no",roll_no).execute()
    name=re.data[0]["name"]
    res = supabase.table("student_attendance").select("subject_name,start_time,end_time,marked_status").eq("roll_no",roll_no).execute()
    data_list=[]
    for r in res.data:
        data_dict={
            "start_time":r["start_time"],
            "end_time":r["end_time"],
            "subject_name":r["subject_name"],
            "Marked_status":r["marked_status"]
        }
        data_list.append(data_dict)
    rec={"name":name,"records":data_list}
    return rec


def get_lecture(start_time,end_time):
    day=dt.date.today().day
    res = supabase.table("time_table").select("subject_name,start_time,end_time,faculty").eq("start_time",start_time).eq("end_time",end_time).execute()
    for r in res.data:
        data_dict={
            "subject_name":r["subject_name"],
            "start_time":r["start_time"],
            "end_time":r["end_time"],
            "faculty":r["faculty"]
        }
    return data_dict









