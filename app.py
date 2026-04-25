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
@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']

    cursor.callproc('LoginUser', (username, password))

    user = None
    for result in cursor.stored_results():
        user = result.fetchone()

    if user:

        session['username'] = user['username']
        session['role'] = user['role']

        role = user['role']

        if role == "student":
            return redirect(url_for('student'))
        elif role == "instructor":
            return redirect(url_for('instructor'))
        elif role == "admin":
            return redirect(url_for('admin'))

    return "Invalid login"

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
    return render_template('instructor.html')


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

@app.route("/api/building")
def get_buildings():
    return jsonify(call_proc("GetBuildings", fetch=True))

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

@app.route("/api/update_student/<int:id>", methods=["PUT"])
def update_student(id):
    data = request.json

    call_proc("UpdateStudent", [
        id,
        data["first_name"],
        data["last_name"],
        data["department"],
        data["advisor_id"]

    ])

    return {"status": "updated"}

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
    call_proc("EnrollStudentInSection", [
        data["student_id"],
        data["section_id"]
    ])
    return {"status": "enrolled"}


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


# -------------------------
# RUN SERVER
# -------------------------
if __name__ == '__main__':
    app.run(debug=True)