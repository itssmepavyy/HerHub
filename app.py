from flask import Flask, render_template, request, redirect, session
from werkzeug.security import generate_password_hash, check_password_hash
import json, os

app = Flask(__name__)
app.secret_key="secret123"
DB="database.json"

def load_db():
    if not os.path.exists(DB):
        with open(DB,'w') as f:
            json.dump({"users":{}, "complaints":[], "medicines":[], "orders":[]},f)
    with open(DB) as f:
        return json.load(f)

def save_db(data):
    with open(DB,'w') as f:
        json.dump(data,f,indent=4)

def login_required(role=None):
    if 'username' not in session:
        return redirect('/login')
    if role and session['role']!=role:
        return "Unauthorized"

@app.route('/')
def home():
    return redirect('/login')

# -------- AUTH --------
@app.route('/signup',methods=['GET','POST'])
def signup():
    db=load_db()
    if request.method=="POST":
        u=request.form['username']
        p=generate_password_hash(request.form['password'])
        r=request.form['role']
        db['users'][u]={"password":p,"role":r}
        save_db(db)
        return redirect('/login')
    return render_template("signup.html")

@app.route('/login',methods=['GET','POST'])
def login():
    db=load_db()
    if request.method=="POST":
        u=request.form['username']
        p=request.form['password']
        if u in db['users'] and check_password_hash(db['users'][u]['password'],p):
            session['username']=u
            session['role']=db['users'][u]['role']
            return redirect('/dashboard')
    return render_template("login.html")

@app.route('/dashboard')
def dash():
    if 'username' not in session:
        return redirect('/login')
    return redirect('/'+session['role'].lower())

# -------- USER --------
@app.route('/user')
def user():
    check=login_required("User")
    if check:return check
    return render_template("user_dashboard.html",username=session['username'])

@app.route('/safety',methods=['GET','POST'])
def safety():
    check=login_required("User")
    if check:return check
    db=load_db()
    if request.method=="POST":
        db['complaints'].append({
            "user":session['username'],
            "text":request.form['text'],
            "status":"Pending"
        })
        save_db(db)
    return render_template("safety.html",complaints=db['complaints'])

@app.route('/shop',methods=['GET','POST'])
def shop():
    check=login_required("User")
    if check:return check
    db=load_db()
    if request.method=="POST":
        db['orders'].append({
            "user":session['username'],
            "medicine":request.form['med']
        })
        save_db(db)
    return render_template("shop.html",medicines=db['medicines'])

# -------- POLICE --------
@app.route('/police',methods=['GET','POST'])
def police():
    check=login_required("Police")
    if check:return check
    db=load_db()
    if request.method=="POST":
        i=int(request.form['id'])
        db['complaints'][i]['status']="Resolved"
        save_db(db)
    return render_template("police_dashboard.html",complaints=db['complaints'])

# -------- MEDICAL --------
@app.route('/medical',methods=['GET','POST'])
def medical():
    check=login_required("Medical")
    if check:return check
    db=load_db()
    if request.method=="POST":
        db['medicines'].append({
            "name":request.form['name'],
            "price":request.form['price']
        })
        save_db(db)
    return render_template("medical_dashboard.html",medicines=db['medicines'])

# -------- ADMIN --------
@app.route('/admin',methods=['GET','POST'])
def admin():
    check=login_required("Admin")
    if check:return check
    db=load_db()
    if request.method=="POST":
        db['users'].pop(request.form['user'],None)
        save_db(db)
    return render_template("admin_dashboard.html",users=db['users'])

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

if __name__=="__main__":
    app.run(debug=True)
