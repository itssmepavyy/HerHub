from flask import Flask, render_template, request, redirect, session, url_for

app = Flask(__name__)
app.secret_key = "supersecret"

# Temporary database
users = {}

# ---------------- HOME ----------------
@app.route('/')
def home():
    return redirect('/login')

# ---------------- SIGNUP ----------------
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == "POST":
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']

        users[username] = {"password": password, "role": role}
        return redirect('/login')

    return render_template("signup.html")

# ---------------- LOGIN ----------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == "POST":
        username = request.form['username']
        password = request.form['password']

        if username in users and users[username]['password'] == password:
            session['username'] = username
            session['role'] = users[username]['role']

            if session['role'] == "User":
                return redirect('/user')
            elif session['role'] == "Police":
                return redirect('/police')
            elif session['role'] == "Medical":
                return redirect('/medical')
            elif session['role'] == "Admin":
                return redirect('/admin')
        else:
            return "Invalid Credentials"

    return render_template("login.html")

# ---------------- USER DASHBOARD ----------------
@app.route('/user')
def user_dashboard():
    return render_template("user_dashboard.html", username=session['username'])

# ---------------- POLICE DASHBOARD ----------------
@app.route('/police')
def police_dashboard():
    return render_template("police_dashboard.html", username=session['username'])

# ---------------- MEDICAL DASHBOARD ----------------
@app.route('/medical')
def medical_dashboard():
    return render_template("medical_dashboard.html", username=session['username'])

# ---------------- ADMIN DASHBOARD ----------------
@app.route('/admin')
def admin_dashboard():
    return render_template("admin_dashboard.html", username=session['username'], users=users)

# ---------------- LOGOUT ----------------
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

if __name__ == "__main__":
    app.run(debug=True)