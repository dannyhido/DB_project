from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import mysql.connector

app = Flask(__name__)
app.secret_key = "something"

# -------------------------
# ROLE-BASED ACCESS CONTROL
# -------------------------
def require_role(*allowed_roles):
    """Gate an API route to one or more roles. Returns 401 if not logged in,
    403 if the session role isn't in allowed_roles."""
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            role = session.get('role')
            if not role:
                return jsonify({"error": "not authenticated"}), 401
            if role not in allowed_roles:
                return jsonify({"error": "forbidden"}), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator

def require_self_or_admin(id_param):
    """For 'modify personal info except ID' rules: a user can only act on their
    own entity_id; admin can act on anyone. id_param is the URL kwarg name."""
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            role = session.get('role')
            if not role:
                return jsonify({"error": "not authenticated"}), 401
            if role == 'admin':
                return fn(*args, **kwargs)
            if kwargs.get(id_param) != session.get('entity_id'):
                return jsonify({"error": "forbidden"}), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator

# -------------------------
# DATABASE CONNECTION
# -------------------------
def db():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="db_project"
    )

def call_proc(proc_name, args=None, fetch=False):
    conn = db()
    cur = conn.cursor(dictionary=True)
    if args is None:
        args = []
    cur.callproc(proc_name, args)
    result = None
    if fetch:
        for r in cur.stored_results():
            result = r.fetchall()
    conn.commit()
    conn.close()
    return result

def query(sql, args=None, fetch=False):
    """Simple raw SQL helper using a fresh connection each time."""
    conn = db()
    cur = conn.cursor(dictionary=True)
    cur.execute(sql, args or [])
    result = cur.fetchall() if fetch else None
    conn.commit()
    conn.close()
    return result

# -------------------------
# LOGIN / LOGOUT / REGISTER
# -------------------------
@app.route('/')
def home():
    return render_template('login.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        conn = db()
        cur = conn.cursor(dictionary=True)
        cur.callproc('LoginUser', (username, password))
        user = None
        for r in cur.stored_results():
            user = r.fetchone()
        conn.close()

        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']

            # Try to find the linked instructor_id or student_id
            # The users table stores id which maps to instructor/student by convention
            # We store user_id from users table and look up the real entity id
            role = user['role']
            uid = user['id']

            if role == 'instructor':
                # Find instructor whose instructor_id matches users.id
                rows = query("SELECT instructor_id FROM instructor WHERE instructor_id = %s", [uid], fetch=True)
                if rows:
                    session['entity_id'] = rows[0]['instructor_id']
                else:
                    # fallback: just use users.id
                    session['entity_id'] = uid
                return redirect(url_for('instructor_dashboard'))

            elif role == 'student':
                rows = query("SELECT student_id FROM student WHERE student_id = %s", [uid], fetch=True)
                if rows:
                    session['entity_id'] = rows[0]['student_id']
                else:
                    session['entity_id'] = uid
                return redirect(url_for('student_dashboard'))

            elif role == 'admin':
                session['entity_id'] = uid
                return redirect(url_for('admin_dashboard'))

        return render_template('login.html', error="Invalid username or password.")

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']
        call_proc('RegisterUser', (username, password, role))
        return redirect(url_for('home'))
    return render_template('register.html')

# -------------------------
# DASHBOARD PAGES
# -------------------------
@app.route('/admin')
def admin_dashboard():
    if session.get('role') != 'admin':
        return redirect(url_for('home'))
    return render_template('admin.html')

@app.route('/instructor')
def instructor_dashboard():
    if session.get('role') != 'instructor':
        return redirect(url_for('home'))
    return render_template('instructor.html', instructor_id=session.get('entity_id'))

@app.route('/student')
def student_dashboard():
    if session.get('role') != 'student':
        return redirect(url_for('home'))
    return render_template('student.html', student_id=session.get('entity_id'))

# -------------------------
# ADMIN - GET ALL
# -------------------------
@app.route("/api/courses")
@require_role('admin', 'instructor', 'student')
def get_courses():
    return jsonify(call_proc("GetAllCourses", fetch=True))

@app.route("/api/students")
@require_role('admin', 'instructor')
def get_students():
    return jsonify(call_proc("GetAllStudents", fetch=True))

@app.route("/api/instructors")
@require_role('admin', 'instructor', 'student')
def get_instructors():
    return jsonify(call_proc("GetAllInstructors", fetch=True))

@app.route("/api/departments")
@require_role('admin', 'instructor', 'student')
def get_departments():
    return jsonify(call_proc("GetAllDepartments", fetch=True))

@app.route("/api/sections")
@require_role('admin', 'instructor', 'student')
def get_sections():
    return jsonify(call_proc("GetAllSections", fetch=True))

@app.route("/api/classrooms")
@require_role('admin')
def get_classrooms():
    return jsonify(call_proc("GetAllClassrooms", fetch=True))

@app.route("/api/timeslots")
@require_role('admin', 'instructor', 'student')
def get_timeslots():
    return jsonify(call_proc("GetAllTimeSlots", fetch=True))

@app.route("/api/building")
@require_role('admin')
def get_buildings():
    return jsonify(call_proc("GetAllBuildings", fetch=True))

@app.route("/api/available_sections")
@require_role('admin', 'student')
def get_available_sections():
    return jsonify(call_proc("GetAllSections", fetch=True))

# -------------------------
# ADMIN - CREATE
# -------------------------
@app.route("/api/create_course", methods=["POST"])
@require_role('admin')
def create_course():
    data = request.json
    call_proc("CreateCourse", [data["name"], data["department_id"], data["credits"]])
    return jsonify({"status": "created"})

@app.route("/api/create_student", methods=["POST"])
@require_role('admin')
def create_student():
    data = request.json
    call_proc("CreateStudent", [data["first_name"], data["last_name"], data["department"], data["advisor_id"]])
    return jsonify({"status": "created"})

@app.route("/api/create_instructor", methods=["POST"])
@require_role('admin')
def create_instructor():
    data = request.json
    call_proc("CreateInstructor", [data["first_name"], data["last_name"], data["department_id"], data["salary"]])
    return jsonify({"status": "created"})

@app.route("/api/create_department", methods=["POST"])
@require_role('admin')
def create_department():
    data = request.json
    call_proc("CreateDepartment", [data["name"], data["building"], data["budget"]])
    return jsonify({"status": "created"})

@app.route("/api/create_classroom", methods=["POST"])
@require_role('admin')
def create_classroom():
    data = request.json
    call_proc("CreateClassroom", [data["room_number"], data["building"]])
    return jsonify({"status": "created"})

@app.route("/api/create_timeslot", methods=["POST"])
@require_role('admin')
def create_timeslot():
    data = request.json
    call_proc("CreateTimeSlot", [data["day"], data["start_hr"], data["start_min"], data["end_hr"], data["end_min"]])
    return jsonify({"status": "created"})

@app.route("/api/create_section", methods=["POST"])
@require_role('admin')
def create_section():
    data = request.json
    call_proc("CreateSection", [data["course_id"], data["semester"], data["year"], data["classroom_id"], data["time_slot_id"]])
    return jsonify({"status": "created"})

# -------------------------
# ADMIN - UPDATE
# -------------------------
@app.route("/api/update_course/<int:id>", methods=["PUT"])
@require_role('admin')
def update_course(id):
    data = request.json
    call_proc("UpdateCourse", [id, data["title"], data["department"], data["credits"]])
    return jsonify({"status": "updated"})

@app.route("/api/update_student/<int:id>", methods=["PUT"])
@require_role('admin')
def update_student(id):
    data = request.json
    call_proc("UpdateStudent", [id, data["first_name"], data["last_name"], data["department"], data["advisor_id"]])
    return jsonify({"status": "updated"})

@app.route("/api/update_instructor/<int:id>", methods=["PUT"])
@require_role('admin')
def update_instructor(id):
    data = request.json
    call_proc("UpdateInstructor", [id, data["first_name"], data["last_name"], data["department_id"], data["salary"]])
    return jsonify({"status": "updated"})

@app.route("/api/update_department/<int:id>", methods=["PUT"])
@require_role('admin')
def update_department(id):
    data = request.json
    call_proc("UpdateDepartment", [id, data["name"], data["building"], data["budget"]])
    return jsonify({"status": "updated"})

@app.route("/api/update_classroom/<int:id>", methods=["PUT"])
@require_role('admin')
def update_classroom(id):
    data = request.json
    call_proc("UpdateClassroom", [id, data["room_number"], data["building"]])
    return jsonify({"status": "updated"})

@app.route("/api/update_timeslot/<int:id>", methods=["PUT"])
@require_role('admin')
def update_timeslot(id):
    data = request.json
    call_proc("UpdateTimeSlot", [id, data["day"], data["start_hr"], data["start_min"], data["end_hr"], data["end_min"]])
    return jsonify({"status": "updated"})

@app.route("/api/update_section/<int:id>", methods=["PUT"])
@require_role('admin')
def update_section(id):
    data = request.json
    call_proc("UpdateSection", [id, data["course_id"], data["semester"], data["year"], data["classroom_id"], data["time_slot_id"]])
    return jsonify({"status": "updated"})

# -------------------------
# ADMIN - DELETE
# -------------------------
@app.route("/api/delete_course/<int:id>", methods=["DELETE"])
@require_role('admin')
def delete_course(id):
    try:
        call_proc("DeleteCourse", [id])
        return jsonify({"status": "deleted"})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/api/delete_student/<int:id>", methods=["DELETE"])
@require_role('admin')
def delete_student(id):
    try:
        call_proc("DeleteStudent", [id])
        return jsonify({"status": "deleted"})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/api/delete_instructor/<int:id>", methods=["DELETE"])
@require_role('admin')
def delete_instructor(id):
    try:
        call_proc("DeleteInstructor", [id])
        return jsonify({"status": "deleted"})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/api/delete_department/<int:id>", methods=["DELETE"])
@require_role('admin')
def delete_department(id):
    try:
        call_proc("DeleteDepartment", [id])
        return jsonify({"status": "deleted"})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/api/delete_classroom/<int:id>", methods=["DELETE"])
@require_role('admin')
def delete_classroom(id):
    try:
        call_proc("DeleteClassroom", [id])
        return jsonify({"status": "deleted"})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/api/delete_timeslot/<int:id>", methods=["DELETE"])
@require_role('admin')
def delete_timeslot(id):
    try:
        call_proc("DeleteTimeSlot", [id])
        return jsonify({"status": "deleted"})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/api/delete_section/<int:id>", methods=["DELETE"])
@require_role('admin')
def delete_section(id):
    try:
        call_proc("DeleteSection", [id])
        return jsonify({"status": "deleted"})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# -------------------------
# ADMIN - ASSIGN/REMOVE INSTRUCTOR
# -------------------------
@app.route("/api/assign_instructor", methods=["POST"])
@require_role('admin')
def assign_instructor():
    data = request.json
    try:
        call_proc("AssignInstructorToSection", [None, data["instructor_id"], data["section_id"]])
        return jsonify({"status": "assigned"})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/api/remove_instructor/<int:section_id>", methods=["DELETE"])
@require_role('admin')
def remove_instructor(section_id):
    try:
        # Remove all instructors from section
        query("DELETE FROM teaches WHERE section_id = %s", [section_id])
        return jsonify({"status": "removed"})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# -------------------------
# ADMIN - ADDITIONAL ANALYTICS
# -------------------------
@app.route("/api/avg_grade_by_department")
@require_role('admin', 'instructor')
def avg_grade_by_department():
    return jsonify(call_proc("GetAvgGradeByDepartment", fetch=True))

@app.route("/api/avg_grade_for_course")
@require_role('admin', 'instructor')
def avg_grade_for_course():
    course_id = request.args.get("course_id")
    start_year = request.args.get("start_year", "2024")
    end_year = request.args.get("end_year", "2026")
    return jsonify(call_proc("GetAvgGradeForCourseRange", [course_id, start_year, end_year], fetch=True))

@app.route("/api/best_worst_classes")
@require_role('admin', 'instructor')
def best_worst_classes():
    semester = request.args.get("semester", "Fall")
    year = request.args.get("year", "2026")
    return jsonify(call_proc("GetBestWorstClasses", [semester, year], fetch=True))

@app.route("/api/total_students_by_department")
@require_role('admin', 'instructor')
def total_students_by_department():
    return jsonify(call_proc("GetTotalStudentsByDepartment", fetch=True))

@app.route("/api/currently_enrolled_by_department")
@require_role('admin', 'instructor')
def currently_enrolled_by_department():
    return jsonify(call_proc("GetCurrentlyEnrolledByDepartment", fetch=True))

# -------------------------
# INSTRUCTOR ROUTES
# -------------------------
@app.route("/api/instructor/sections")
@require_role('instructor')
def instructor_sections():
    instructor_id = session.get('entity_id')
    semester = request.args.get("semester", "Fall")
    year = request.args.get("year", "2026")
    results = call_proc("GetInstructorSections", [instructor_id, semester, year], fetch=True)
    return jsonify(results or [])

@app.route("/api/instructor/sections_all")
@require_role('instructor')
def instructor_sections_all():
    instructor_id = session.get('entity_id')
    rows = query("""
        SELECT sec.section_id, c.title, sec.semester, sec.year
        FROM teaches t
        JOIN section sec ON t.section_id = sec.section_id
        JOIN course c ON sec.course_id = c.course_id
        WHERE t.instructor_id = %s
        ORDER BY sec.year DESC, sec.semester
    """, [instructor_id], fetch=True)
    return jsonify(rows or [])

@app.route("/api/section/<int:section_id>/roster")
@require_role('admin', 'instructor')
def section_roster(section_id):
    results = call_proc("GetSectionRoster", [section_id], fetch=True)
    # Rename columns to match what the HTML expects
    roster = []
    for r in (results or []):
        roster.append({
            "ID": r["student_id"],
            "name": r["first_name"] + " " + r["last_name"],
            "grade": r["grade"]
        })
    return jsonify(roster)

@app.route("/api/instructor/grade", methods=["POST"])
@require_role('instructor')
def submit_grade():
    data = request.json
    try:
        call_proc("GiveStudentGrade", [data["student_id"], data["section_id"], data["grade"]])
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/api/instructor/change_grade", methods=["POST"])
@require_role('instructor')
def change_grade():
    data = request.json
    try:
        call_proc("ChangeStudentGrade", [data["student_id"], data["section_id"], data["grade"]])
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/api/instructor/advisees")
@require_role('instructor')
def get_advisees():
    instructor_id = session.get('entity_id')
    rows = query("""
        SELECT student_id as ID, CONCAT(first_name, ' ', last_name) as name
        FROM student WHERE advisor_id = %s
    """, [instructor_id], fetch=True)
    return jsonify(rows or [])

@app.route("/api/instructor/add_advisee", methods=["POST"])
@require_role('instructor')
def add_advisee():
    data = request.json
    instructor_id = session.get('entity_id')
    try:
        call_proc("AddStudentAsAdvisee", [data["student_id"], instructor_id])
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/api/instructor/remove_advisee", methods=["POST"])
@require_role('instructor')
def remove_advisee():
    data = request.json
    try:
        call_proc("RemoveStudentAsAdvisee", [data["student_id"]])
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/api/instructor/remove_from_section", methods=["POST"])
@require_role('instructor')
def remove_from_section():
    data = request.json
    try:
        call_proc("RemoveStudentFromSection", [data["student_id"], data["section_id"]])
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/api/instructor_details/<int:id>")
@require_role('admin', 'instructor', 'student')
def get_instructor_details(id):
    rows = query("""
        SELECT i.instructor_id, i.first_name, i.last_name, i.salary,
               d.name as dept_name, b.building_name as building
        FROM instructor i
        JOIN department d ON i.department_id = d.department_id
        JOIN building b ON d.building = b.building_id
        WHERE i.instructor_id = %s
    """, [id], fetch=True)
    return jsonify(rows[0] if rows else {})

@app.route("/api/update_instructor_name/<int:id>", methods=["PUT"])
@require_self_or_admin('id')
def update_instructor_name(id):
    data = request.json
    rows = query("SELECT department_id, salary FROM instructor WHERE instructor_id = %s", [id], fetch=True)
    if not rows:
        return jsonify({"error": "Not found"}), 404
    current = rows[0]
    call_proc("UpdateInstructor", [id, data["first_name"], data["last_name"], current["department_id"], current["salary"]])
    return jsonify({"status": "updated"})

# Prereqs
@app.route("/api/course_prereqs/<int:course_id>")
@require_role('admin', 'instructor', 'student')
def get_course_prereqs(course_id):
    return jsonify(call_proc("GetCoursePrereqs", [course_id], fetch=True) or [])

@app.route("/api/add_prereq", methods=["POST"])
@require_role('admin', 'instructor')
def add_prereq():
    data = request.json
    try:
        call_proc("AddPrereq", [data["course_id"], data["prereq_id"]])
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/api/remove_prereq", methods=["POST"])
@require_role('admin', 'instructor')
def remove_prereq():
    data = request.json
    try:
        call_proc("RemovePrereq", [data["course_id"], data["prereq_id"]])
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# -------------------------
# STUDENT ROUTES
# -------------------------
@app.route("/api/student/schedule")
@require_role('student')
def get_student_schedule():
    student_id = session.get('entity_id')
    semester = request.args.get('semester', 'Fall')
    year = request.args.get('year', '2026')
    results = call_proc("GetStudentSchedule", [student_id, semester, year], fetch=True)
    return jsonify(results or [])

@app.route("/api/student/current_enrollments")
@require_role('student')
def get_current_enrollments():
    student_id = session.get('entity_id')
    semester = request.args.get('semester', 'Fall')
    year = request.args.get('year', '2026')
    results = call_proc("GetStudentCoursesBySemester", [student_id, semester, year], fetch=True)
    return jsonify(results or [])

@app.route("/api/student/<int:id>/grades")
def get_student_grades(id):
    role = session.get('role')
    if not role:
        return jsonify({"error": "not authenticated"}), 401
    if role == 'student' and id != session.get('entity_id'):
        return jsonify({"error": "forbidden"}), 403
    return jsonify(call_proc("GetStudentGrades", [id], fetch=True) or [])

@app.route("/api/student/<int:id>/advisor")
def get_student_advisor(id):
    role = session.get('role')
    if not role:
        return jsonify({"error": "not authenticated"}), 401
    if role == 'student' and id != session.get('entity_id'):
        return jsonify({"error": "forbidden"}), 403
    results = call_proc("GetStudentAdvisorInfo", [id], fetch=True)
    return jsonify(results[0] if results else {})

@app.route("/api/student_details/<int:id>")
def get_student_details(id):
    role = session.get('role')
    if not role:
        return jsonify({"error": "not authenticated"}), 401
    if role == 'student' and id != session.get('entity_id'):
        return jsonify({"error": "forbidden"}), 403
    rows = query("""
        SELECT s.student_id, s.first_name, s.last_name, s.department as dept_id,
               d.name as dept_name
        FROM student s
        JOIN department d ON s.department = d.department_id
        WHERE s.student_id = %s
    """, [id], fetch=True)
    return jsonify(rows[0] if rows else {})

@app.route("/api/update_student_name/<int:id>", methods=["PUT"])
@require_self_or_admin('id')
def update_student_name(id):
    data = request.json
    rows = query("SELECT department, advisor_id FROM student WHERE student_id = %s", [id], fetch=True)
    if not rows:
        return jsonify({"error": "Not found"}), 404
    current = rows[0]
    call_proc("UpdateStudent", [id, data["first_name"], data["last_name"], current["department"], current["advisor_id"]])
    return jsonify({"status": "updated"})

@app.route("/api/enroll", methods=["POST"])
@require_role('student')
def enroll_student():
    data = request.json
    student_id = session.get('entity_id')
    try:
        call_proc("EnrollStudentInSection", [None, student_id, data["section_id"]])
        return jsonify({"status": "success", "message": "Enrolled successfully!"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route("/api/drop", methods=["POST"])
@require_role('student')
def drop_section():
    data = request.json
    student_id = session.get('entity_id')
    call_proc("RemoveStudentFromSection", [student_id, data["section_id"]])
    return jsonify({"status": "success"})

@app.route("/api/section_details/<int:section_id>")
@require_role('admin', 'instructor', 'student')
def get_section_info(section_id):
    results = call_proc("GetSectionInfo", [section_id], fetch=True)
    return jsonify(results[0] if results else {})

# -------------------------
# RUN SERVER
# -------------------------
if __name__ == '__main__':
    app.run(debug=True)