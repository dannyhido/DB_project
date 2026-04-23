from flask import Flask, render_template, request, redirect, url_for, session
import mysql.connector


app = Flask(__name__)
app.secret_key = "something"

# -------------------------
# DATABASE CONNECTION
# -------------------------
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",
    database="db_project"
)

cursor = db.cursor(dictionary=True)

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
        db.commit()

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


# -------------------------
# RUN SERVER
# -------------------------
if __name__ == '__main__':
    app.run(debug=True)