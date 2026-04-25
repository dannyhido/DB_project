from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import mysql.connector


app = Flask(__name__)
app.secret_key = "something"

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

conn = db()
cursor = conn.cursor(dictionary=True)


# call prodeduce template --- USE THIS
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

# -------------------------
# LOGIN PAGE (default route)
# -------------------------
@app.route('/')
def home():
    return render_template('login.html')


# -------------------------
# LOGIN HANDLER
# -------------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user_id = request.form.get('user_id')
        username = request.form.get('username') # You can use this for validation if needed
        password = request.form.get('password')

        cursor = conn.cursor(dictionary=True)
        
        # 1. Check if ID belongs to a Student
        cursor.execute("SELECT student_id FROM student WHERE student_id= %s", (user_id,))
        student = cursor.fetchone()
        
        if student:
            session['user_id'] = user_id
            session['role'] = 'student'
            return redirect(url_for('student_dashboard'))
            
        # 2. Check if ID belongs to an Instructor
        cursor.execute("SELECT student_id FROM instructor WHERE instructor_id = %s", (user_id,))
        instructor = cursor.fetchone()
        
        if instructor:
            session['user_id'] = user_id
            session['role'] = 'instructor'
            return redirect(url_for('instructor_dashboard'))

        # 3. Handle Failure
        return "Invalid ID or Role", 401
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))
# -------------------------
# REGISTER PAGE
# -------------------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':

        username = request.form['username']
        password = request.form['password']
        role = request.form['role']

        cursor.callproc('RegisterUser', (username, password, role))
        conn.commit()

        return redirect(url_for('home'))

    return render_template('register.html')
# -------------------------
# ROLE PAGES
# -------------------------
@app.route('/student')
def student():
    if session.get('role') != 'student':
        return "Access denied"
    return render_template('student.html')


@app.route('/instructor')
def instructor():
    if session.get('role') != 'instructor':
        return "Access denied"
    return render_template('instructor.html', instructor_id=session.get('user_id'))


@app.route('/admin')
def admin():
    if session.get('role') != 'admin':
        return "Access denied"
    return render_template('admin.html')

#admin functions

# admin get calls 

@app.route("/api/courses")
def get_courses():
    return jsonify(call_proc("GetAllCourses", fetch=True))

@app.route("/api/available_sections")
def get_available_sections():
    # This calls the procedure to show sections students can join
    return jsonify(call_proc("GetAllSections", fetch=True))

@app.route("/api/building")
def get_buildings():
    return jsonify(call_proc("GetAllBuildings", fetch=True))

@app.route("/api/students")
def get_students():
    return jsonify(call_proc("GetAllStudents", fetch=True))

@app.route("/api/instructors")
def get_instructors():
    return jsonify(call_proc("GetAllInstructors", fetch=True))

@app.route("/api/departments")
def get_departments():
    return jsonify(call_proc("GetAllDepartments", fetch=True))

@app.route("/api/sections")
def get_sections():
    return jsonify(call_proc("GetAllSections", fetch=True))

@app.route("/api/classrooms")
def get_classrooms():
    return jsonify(call_proc("GetAllClassrooms", fetch=True))

@app.route("/api/timeslots")
def get_timeslots():
    return jsonify(call_proc("GetAllTimeSlots", fetch=True))

# admin create calls 
@app.route("/api/create_course", methods=["POST"])
def create_course():
    data = request.json
    call_proc("CreateCourse", [
        data["name"],
        data["department_id"],
        data["credits"]
    ])
    return {"status": "created"}


from flask import request, jsonify

@app.route("/api/update_student/<int:student_id>", methods=["PUT"])
def update_student(student_id):
    data = request.json

    try:
        call_proc("UpdateStudent", [
            student_id,
            data["first_name"],
            data["last_name"],
            data["department"],
            data["advisor_id"]
        ])

        return jsonify({"status": "updated", "student_id": student_id}), 200

    except Exception as e:
        print(e)
        return jsonify({"error": str(e)}), 500
    
@app.route("/api/assign_instructor", methods=["POST"])
def assign_instructor_to_section():
    data = request.get_json()
    try:
        cursor.execute(
            "INSERT INTO teaches (instructor_id, section_id) VALUES (%s, %s)",
            (data["instructor_id"], data["section_id"])
        )
        conn.commit()
        return jsonify({"status": "ok"})
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
@app.route("/api/remove_instructor/<int:section_id>", methods=["DELETE"])
def remove_instructor_from_section(section_id):  # <-- must be here
    try:
        cursor.execute("DELETE FROM teaches WHERE section_id = %s", (section_id,))
        db.commit()
        return jsonify({"status": "ok"})
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500

@app.route("/api/create_timeslot", methods=["POST"])
def create_timeslot():
    data = request.get_json()

    call_proc("CreateTimeSlot", [
        data["day"],
        data["start_hr"],
        data["start_min"],
        data["end_hr"],
        data["end_min"]
    ])

    return jsonify({"status": "success"})

@app.route("/api/create_classroom", methods=["POST"])
def create_classroom():
    data = request.json

    call_proc("CreateClassroom", [
        data["room_number"],
        data["building"]
    ])

    return {"status": "created"}

@app.route("/api/create_department", methods=["POST"])
def create_department():
    data = request.json

    call_proc("CreateDepartment", [
        data["name"],
        data["building"],
        data["budget"]
    ])

    return {"status": "created"}

@app.route("/api/create_student", methods=["POST"])
def create_student():
    data = request.get_json()

    call_proc("CreateStudent", [
        data["first_name"],
        data["last_name"],
        data["advisor_id"],
        data["department"]
    ])

    return jsonify({"success": True})

@app.route("/api/create_section", methods=["POST"])
def create_section():
    data = request.json

    call_proc("CreateSection", [
        data["course_id"],
        data["semester"],
        data["year"],
        data["classroom_id"],
        data["time_slot_id"]
    ])

    return {"status": "created"}
@app.route("/api/create_instructor", methods=["POST"])
def create_instructor():
    data = request.json

    call_proc("CreateInstructor", [
        data["first_name"],
        data["last_name"],
        data["department_id"],
        data["salary"]
    ])

    return {"status": "created"}

#admin update calls
@app.route("/api/update_course/<int:id>", methods=["PUT"])
def update_course(id):
    data = request.json
    call_proc("UpdateCourse", [
        id,
        data["title"],
        data["department"],
        data["credits"]
    ])
    return {"status": "updated"}


@app.route("/api/update_timeslot/<int:id>", methods=["PUT"])
def update_timeslot(id):
    data = request.get_json()

    call_proc("UpdateTimeSlot", [
        id,
        data["day"],
        data["start_hr"],
        data["start_min"],
        data["end_hr"],
        data["end_min"]
    ])

    return jsonify({"status": "updated"})


@app.route("/api/update_classroom/<int:id>", methods=["PUT"])
def update_classroom(id):
    data = request.json

    call_proc("UpdateClassroom", [
        id,
        data["room_number"],
        data["building"],
    ])

    return {"status": "updated"}

@app.route("/api/update_student_name/<int:id>", methods=["PUT"])
def update_student_name(id):
    data = request.json
    
    # First, get current student record to keep dept/advisor the same
    current = call_proc("GetStudentDetails", [id], fetch=True)[0]
    
    # Procedure: UpdateStudent(p_id, p_fname, p_lname, p_dept, p_advisor)
    call_proc("UpdateStudent", [
        id,
        data["first_name"],
        data["last_name"],
        current["dept_id"],
        current["advisor_id"]
    ])
    
    return jsonify({"status": "updated"})

@app.route("/api/section_details/<int:section_id>")
def get_section_info(section_id):
    # This calls the procedure: GetSectionDetails(p_section_id)
    # fetch=True is required because we want the classroom and course data
    results = call_proc("GetSectionDetails", [section_id], fetch=True)
    
    # Return the first row found, or an empty object if no section exists
    section_info = results[0] if results else {}
    return jsonify(section_info)
@app.route("/api/update_section/<int:id>", methods=["PUT"])
def update_section(id):
    data = request.json

    call_proc("UpdateSection", [
        id,
        data["course_id"],
        data["semester"],
        data["year"],
        data["classroom_id"],
        data["time_slot_id"]
    ])

    return {"status": "updated"}

@app.route('/api/instructor/sections')
def instructor_sections():
    # Example: getting these from session or request args
    instructor_id = session.get('user_id') 
    semester = request.args.get('semester')
    year = request.args.get('year')

    try:
        cursor = conn.cursor(dictionary=True)
        
        # Call the stored procedure
        # Params must be passed as a list or tuple
        cursor.callproc('GetInstructorSections', [instructor_id, semester, year])
        
        # Stored procedures can return multiple result sets, 
        # so we loop through them to get our data
        results = []
        for result in cursor.stored_results():
            results = result.fetchall()
        
        cursor.close()
        return jsonify(results)

    except mysql.connector.Error as err:
        print(f"Error: {err}")
        return jsonify({"error": "Database error"}), 500

@app.route("/api/instructor/sections_all")
def instructor_sections_all():
    instructor_id = session.get("user_id")
    cursor.execute("""
        SELECT s.section_id, c.title, s.semester, s.year
        FROM teaches t
        JOIN section s ON t.section_id = s.section_id
        JOIN course c ON s.course_id = c.course_id
        WHERE t.instructor_id = %s
    """, (instructor_id,))
    rows = cursor.fetchall()
    columns = [d[0] for d in cursor.description]
    return jsonify([dict(zip(columns, r)) for r in rows])

@app.route("/api/section/<int:section_id>/roster")
def section_roster(section_id):
    cursor.execute("""
        SELECT s.student_id as ID, 
               CONCAT(s.first_name, ' ', s.last_name) as name,
               t.grade
        FROM takes t
        JOIN student s ON t.student_id = s.student_id
        WHERE t.section_id = %s
    """, (section_id,))
    rows = cursor.fetchall()
    columns = [d[0] for d in cursor.description]
    return jsonify([dict(zip(columns, r)) for r in rows])

@app.route("/api/instructor/grade", methods=["POST"])
def submit_grade():
    data = request.get_json()
    cursor.execute("""
        UPDATE takes SET grade = %s 
        WHERE student_id = %s AND section_id = %s
    """, (data["grade"], data["student_id"], data["section_id"]))
    conn.commit()
    return jsonify({"status": "ok"})

@app.route("/api/instructor/advisees")
def get_advisees():
    instructor_id = session.get("user_id")
    cursor.execute("""
        SELECT student_id as ID,
               CONCAT(first_name, ' ', last_name) as name
        FROM student WHERE advisor_id = %s
    """, (instructor_id,))
    rows = cursor.fetchall()
    columns = [d[0] for d in cursor.description]
    return jsonify([dict(zip(columns, r)) for r in rows])

@app.route("/api/instructor/add_advisee", methods=["POST"])
def add_advisee():
    data = request.get_json()
    instructor_id = session.get("user_id")
    cursor.execute(
        "UPDATE student SET advisor_id = %s WHERE student_id = %s",
        (instructor_id, data["student_id"])
    )
    conn.commit()
    return jsonify({"status": "ok"})

@app.route("/api/instructor/remove_from_section", methods=["POST"])
def remove_from_section():
    data = request.get_json()
    cursor.execute(
        "DELETE FROM takes WHERE student_id = %s AND section_id = %s",
        (data["student_id"], data["section_id"])
    )
    conn.commit()
    return jsonify({"status": "ok"})


@app.route('/instructor_dashboard')
def instructor_dashboard():
    if session.get('role') != 'instructor':
        return redirect(url_for('login'))
    return render_template('instructor.html')

@app.route('/student_dashboard')
def student_dashboard():
    if session.get('role') != 'student':
        return redirect(url_for('login'))
    return render_template('student.html')

@app.route("/api/instructor_details/<int:id>")
def get_instructor_details(id):
    # Uses your call_proc helper to safely fetch advisor info
    results = call_proc("GetInstructorDetails", [id], fetch=True)
    instructor_info = results[0] if results else {}
    return jsonify(instructor_info)

@app.route("/api/update_instructor/<int:id>", methods=["PUT"])
def update_instructor(id):
    data = request.json

    call_proc("UpdateInstructor", [
        id,
        data["first_name"],
        data["last_name"],
        data["department_id"],
        data["salary"]
    ])

    return {"status": "updated"}


@app.route("/api/update_department/<int:id>", methods=["PUT"])
def update_department(id):
    data = request.json
    call_proc("UpdateDepartment", [
        id,
        data["name"],
        data["building"],
        data["budget"]
    ])
    return {"status": "updated"}


#admin delete calls 
@app.route("/api/delete_course/<int:id>", methods=["DELETE"])
def delete_course(id):
    call_proc("DeleteCourse", [id])
    return {"status": "deleted"}

@app.route("/api/delete_section/<int:id>", methods=["DELETE"])
def delete_section(id):
    call_proc("DeleteSection", [id])
    return {"status": "deleted"}

@app.route("/api/delete_timeslot/<int:id>", methods=["DELETE"])
def delete_timeslot(id):
    call_proc("DeleteTimeSlot", [id])
    return jsonify({"status": "deleted"})

@app.route("/api/delete_student/<int:id>", methods=["DELETE"])
def delete_student(id):
    call_proc("DeleteStudent", [id])
    return {"status": "deleted"}

@app.route("/api/delete_instructor/<int:id>", methods=["DELETE"])
def delete_instructor(id):
    call_proc("DeleteInstructor", [id])
    return {"status": "deleted"}
@app.route("/api/delete_department/<int:id>", methods=["DELETE"])
def delete_department(id):
    call_proc("DeleteDepartment", [id])
    return {"status": "deleted"}

@app.route("/api/delete_classroom/<int:id>", methods=["DELETE"])
def delete_classroom(id):
    call_proc("DeleteClassroom", [id])
    return {"status": "deleted"}

# final admin calls
@app.route("/api/enroll", methods=["POST"])
def enroll_student():
    data = request.json
    try:
        # We pass 3 arguments now: [takes_id, student_id, section_id]
        # None is passed for takes_id so the DB auto-increments it.
        call_proc("EnrollStudentInSection", [
            None, 
            data["student_id"], 
            data["section_id"]
        ])
        return jsonify({"status": "success", "message": "Enrolled successfully!"})
    except Exception as e:
        # This will catch errors like 'Student is already enrolled' from your SQL
        return jsonify({"status": "error", "message": str(e)}), 400
    
@app.route("/api/student/current_enrollments")
def get_current_enrollments():
    # 1. Pull the ID from the active session instead of hardcoding '1'
    student_id = session.get("user_id")
    role = session.get("role")

    # 2. Safety check: Ensure they are logged in as a student
    if not student_id or role != 'student':
        return jsonify({"error": "Unauthorized access. Please login as a student."}), 401

    try:
        # 3. Call your stored procedure using the session ID
        # Using "Fall" and "2026" as requested to match your SQL dump
        results = call_proc("GetStudentCoursesBySemester", [student_id, "Fall", "2026"], fetch=True)
        
        return jsonify(results)
        
    except Exception as e:
        print(f"Error fetching enrollments: {e}")
        return jsonify({"error": "Could not retrieve enrollment data"}), 500

@app.route("/api/drop", methods=["POST"])
def drop_section():
    data = request.json
    # Procedure: RemoveStudentFromSection(p_student_id, p_section_id)
    call_proc("RemoveStudentFromSection", [data["student_id"], data["section_id"]])
    return jsonify({"status": "success"})

@app.route("/api/student/schedule")
def get_student_schedule():
    # Get parameters from the URL (defaulting to Fall 2026 if not provided)
    semester = request.args.get('semester', 'Fall')
    year = request.args.get('year', '2026')
    
    # Use session['user_id'] in production; hardcoded to 1 for now
    session['user_id'] = user['id']  # or whatever the first column is named
    
    # Procedure: GetStudentSchedule(p_student_id, p_semester, p_year)
    #
    schedule = call_proc("GetStudentSchedule", [student_id, semester, year], fetch=True)
    return jsonify(schedule)

@app.route("/api/student/<int:id>/grades")
def get_student_grades(id):
    # Uses your call_proc helper to handle the connection and cleanup
    # fetch=True tells it to return the SELECT results from the procedure
    results = call_proc("GetStudentGrades", [id], fetch=True)
    return jsonify(results)

@app.route("/api/student/<int:id>/advisor")
def get_student_advisor(id):
    results = call_proc("GetStudentAdvisorInfo", [id], fetch=True)
    
    advisor_info = results[0] if results else {}
    return jsonify(advisor_info)

@app.route("/api/update_student_profile/<int:id>", methods=["PUT"])
def update_student_profile(id):
    data = request.json
    # Uses the UpdateStudent procedure from your SQL file
    call_proc("UpdateStudent", [
        id,
        data["first_name"],
        data["last_name"],
        data["department"],
        data["advisor_id"]
    ])
    return {"status": "profile updated"}

@app.route("/api/assign_instructor", methods=["POST"])
def assign_instructor():
    data = request.json
    call_proc("AssignInstructorToSection", [
        data["instructor_id"],
        data["section_id"]
    ])
    return {"status": "assigned"}


@app.route("/api/grade", methods=["POST"])
def give_grade():
    data = request.json
    call_proc("GiveStudentGrade", [
        data["student_id"],
        data["section_id"],
        data["grade"]
    ])
    return {"status": "graded"}


# ---------------- SAME PATTERN FOR ALL TABLES ----------------
# You just copy this for:
#student funcitons


# -------------------------
# RUN SERVER
# -------------------------
if __name__ == '__main__':
    app.run(debug=True)