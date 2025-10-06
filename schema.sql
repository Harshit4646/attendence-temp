-- schema.sql
CREATE TABLE IF NOT EXISTS student_record (
  roll_no TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  branch TEXT,
  section TEXT,
  phone_no TEXT,
  dob DATE,
  image_path TEXT,
  username TEXT UNIQUE,
  password_hash TEXT,
  total_classes INTEGER DEFAULT 0,
  present INTEGER DEFAULT 0,
  semester_no INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS student_attendance (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  roll_no TEXT NOT NULL REFERENCES student_record(roll_no) ON DELETE CASCADE,
  date DATE NOT NULL,
  subject_name TEXT,
  start_time TIME,
  end_time TIME,
  name TEXT,
  mode TEXT,
  marked_status CHAR(1)
);

CREATE TABLE IF NOT EXISTS teacher_record (
  teacher_Username TEXT PRIMARY KEY,
  teacher_name TEXT,
  password_hash TEXT,
  latitude DOUBLE PRECISION,
  longitude DOUBLE PRECISION
);

CREATE TABLE IF NOT EXISTS time_table (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  day TEXT,
  section TEXT,
  subject_name TEXT,
  teacher_name TEXT,
  teacher_Username TEXT,
  start_time TIME,
  end_time TIME
);

CREATE OR REPLACE FUNCTION update_counts_after_attendance() RETURNS trigger AS $$
BEGIN
  UPDATE student_record
  SET total_classes = COALESCE(total_classes,0) + 1,
      present = COALESCE(present,0) + (CASE WHEN NEW.marked_status = 'P' THEN 1 ELSE 0 END)
  WHERE roll_no = NEW.roll_no;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_update_counts
AFTER INSERT ON student_attendance
FOR EACH ROW
EXECUTE FUNCTION update_counts_after_attendance();
