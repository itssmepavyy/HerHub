from flask import Flask, render_template, request, redirect, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import json, os
from datetime import datetime

app = Flask(__name__)
app.secret_key = "secret123"

DB = "database.json"
MEDICAL_DB = "medical_db.json"
UPLOAD_FOLDER = os.path.join('static','uploads')
ALLOWED_EXTENSIONS = {'png','jpg','jpeg','gif'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# nearby police stations (sample data)
POLICE_STATIONS = [
    {"id":1, "name":"Central Police Station", "address":"1 Main St, City", "email":"central@police.example.com"},
    {"id":2, "name":"North Police Station", "address":"10 North Ave, City", "email":"north@police.example.com"},
    {"id":3, "name":"East Police Station", "address":"5 East Rd, City", "email":"east@police.example.com"}
]

# Expanded states -> districts mapping (sample districts for each state/UT)
STATE_DISTRICT_MAP = {
    "Andhra Pradesh": ["Visakhapatnam","Vijayawada","Guntur","Tirupati"],
    "Arunachal Pradesh": ["Itanagar","Tawang","Pasighat"],
    "Assam": ["Guwahati","Jorhat","Silchar","Dibrugarh"],
    "Bihar": ["Patna","Gaya","Bhagalpur","Muzaffarpur"],
    "Chhattisgarh": ["Raipur","Bilaspur","Durg"],
    "Goa": ["Panaji","Margao","Mapusa"],
    "Gujarat": ["Ahmedabad","Surat","Vadodara","Rajkot"],
    "Haryana": ["Gurugram","Faridabad","Panipat","Ambala"],
    "Himachal Pradesh": ["Shimla","Dharamshala","Mandi"],
    "Jharkhand": ["Ranchi","Jamshedpur","Dhanbad"],
    "Karnataka": ["Bengaluru","Mysore","Mangalore","Hubli"],
    "Kerala": ["Thiruvananthapuram","Kochi","Kozhikode","Thrissur"],
    "Madhya Pradesh": ["Bhopal","Indore","Jabalpur","Gwalior"],
    "Maharashtra": ["Mumbai","Pune","Nagpur","Nashik","Thane"],
    "Manipur": ["Imphal","Churachandpur"],
    "Meghalaya": ["Shillong","Tura"],
    "Mizoram": ["Aizawl","Lunglei"],
    "Nagaland": ["Kohima","Dimapur"],
    "Odisha": ["Bhubaneswar","Cuttack","Rourkela"],
    "Punjab": ["Chandigarh","Ludhiana","Amritsar","Jalandhar"],
    "Rajasthan": ["Jaipur","Jodhpur","Udaipur","Bikaner"],
    "Sikkim": ["Gangtok"],
    "Tamil Nadu": ["Chennai","Coimbatore","Madurai","Tiruchirappalli"],
    "Telangana": ["Hyderabad","Warangal","Nizamabad"],
    "Tripura": ["Agartala"],
    "Uttar Pradesh": ["Lucknow","Kanpur","Varanasi","Agra"],
    "Uttarakhand": ["Dehradun","Haridwar"],
    "West Bengal": ["Kolkata","Howrah","Siliguri","Durgapur"],
    "Andaman and Nicobar Islands": ["Port Blair"],
    "Chandigarh": ["Chandigarh"],
    "Dadra and Nagar Haveli and Daman and Diu": ["Daman","Diu","Silvassa"],
    "Delhi": ["New Delhi","North Delhi","South Delhi"],
    "Jammu and Kashmir": ["Srinagar","Jammu"],
    "Ladakh": ["Leh","Kargil"],
    "Lakshadweep": ["Kavaratti"]
}

# ---------------- DATABASE ----------------
def load_db():
    if not os.path.exists(DB):
        with open(DB,'w') as f:
            json.dump({"users":{}, "complaints":[], "medicines":[], "orders":[]},f)
    with open(DB) as f:
        return json.load(f)

def save_db(data):
    with open(DB,'w') as f:
        json.dump(data,f,indent=4)

def load_medical_db():
    if not os.path.exists(MEDICAL_DB):
        with open(MEDICAL_DB,'w') as f:
            json.dump({"stores":[]},f)
    with open(MEDICAL_DB) as f:
        return json.load(f)

def save_medical_db(data):
    with open(MEDICAL_DB,'w') as f:
        json.dump(data,f,indent=4)

# ---------------- HELPERS ----------------
def login_required(role=None):
    if 'username' not in session:
        return redirect('/login')
    if role and session['role'] != role:
        return "Unauthorized"

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.',1)[1].lower() in ALLOWED_EXTENSIONS

def profile_is_complete(profile):
    if not profile:
        return False
    required = ['email','phone','aadhar','gender','dob','blood_group','bio','interests','profile_pic','address','location']
    return all(profile.get(k) for k in required)

@app.template_filter('calculate_age')
def calculate_age(dob_str):
    try:
        dob = datetime.strptime(dob_str,'%Y-%m-%d')
        today = datetime.today()
        return today.year - dob.year - ((today.month,today.day)<(dob.month,dob.day))
    except:
        return ""


@app.context_processor
def inject_sos_alerts():
    try:
        db = load_db()
        sos_alerts = [c for c in db.get('complaints', []) if c.get('text') == 'SOS' and c.get('status') == 'Pending']
        return dict(sos_alerts=sos_alerts, sos_count=len(sos_alerts))
    except:
        return dict(sos_alerts=[], sos_count=0)

# ---------------- ROUTES ----------------
@app.route('/')
def home():
    return redirect('/login')

# -------- AUTH --------
@app.route('/signup',methods=['GET','POST'])
def signup():
    db=load_db()
    if request.method=="POST":
        u=request.form.get('username','').strip()
        p=request.form.get('password','')
        r=request.form.get('role','')

        if not u or not p or not r:
            flash("All fields required","error")
            return render_template("signup.html")

        if u in db['users']:
            flash("Username already exists","error")
            return render_template("signup.html")

        db['users'][u]={
            "password":generate_password_hash(p),
            "role":r,
            "profile":{} if r=="User" else None
        }
        save_db(db)
        # Auto-login Medical users, others go to login
        if r == 'Medical':
            session['username'] = u
            session['role'] = r
            flash("Account created and logged in.", "success")
            return redirect('/medical/details')
        # For non-medical users, set a one-time prefill for the login page
        session['prefill_login'] = {'username': u, 'password': p}
        flash("Account created. Login now.","success")
        return redirect('/login')

    return render_template("signup.html")


@app.route('/login',methods=['GET','POST'])
def login():
    if 'username' in session:
        return redirect('/dashboard')

    db=load_db()
    if request.method=="POST":
        u=request.form.get('username','').strip()
        p=request.form.get('password','')
        # explicit checks: unknown user vs wrong password
        if u not in db['users']:
            flash("Username not found. Please sign up.","error")
            return render_template("login.html", prefill=session.get('prefill_login'))

        if check_password_hash(db['users'][u]['password'], p):
            session['username']=u
            session['role']=db['users'][u]['role']
            # if user role, require complete profile before dashboard
            if session['role']=='User':
                profile = db['users'][u].get('profile')
                if not profile_is_complete(profile):
                    return redirect('/complete_profile')
                return redirect('/dashboard')
            # medical users: require store details before dashboard
            if session['role']=='Medical':
                profile = db['users'][u].get('profile')
                if not profile or not profile.get('store_info'):
                    return redirect('/medical/details')
                return redirect('/medical')
            return redirect('/dashboard')
        else:
            flash("Invalid password","error")
    # one-time prefill data after signup
    prefill = session.pop('prefill_login', None)
    return render_template("login.html", prefill=prefill)

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect('/login')
    return redirect('/'+session['role'].lower())

# -------- USER --------
@app.route('/user')
def user():
    check=login_required("User")
    if check: return check
    db=load_db()
    profile=db['users'][session['username']].get('profile')
    return render_template("user_dashboard.html",
                           username=session['username'],
                           profile_complete=profile_is_complete(profile))

@app.route('/profile')
def profile():
    if 'username' not in session:
        return redirect('/login')
    db=load_db()
    profile=db['users'][session['username']].get('profile',{})
    return render_template("profile.html",
                           username=session['username'],
                           profile=profile)


@app.route('/profile/edit', methods=['GET','POST'])
def edit_profile():
    if 'username' not in session:
        return redirect('/login')
    db = load_db()
    user = session['username']
    profile = db['users'][user].get('profile', {})

    if request.method == 'POST':
        errors = []
        email = request.form.get('email','').strip()
        phone = request.form.get('phone','').strip()
        # aadhar cannot be changed
        aadhar = profile.get('aadhar','')
        gender = request.form.get('gender','').strip()
        dob = request.form.get('dob','').strip()
        blood_group = request.form.get('blood_group','').strip()
        address = request.form.get('address','').strip()
        location = request.form.get('location','').strip()
        bio = request.form.get('bio','').strip()
        interests = request.form.getlist('interests')
        other = request.form.get('other','').strip()

        if not email or not email.endswith('@gmail.com'):
            errors.append('Email must be a valid @gmail.com address')
        if not phone or not phone.isdigit() or len(phone) != 10:
            errors.append('Phone must be a 10 digit number')
        if not aadhar or not aadhar.isdigit() or len(aadhar) != 12:
            errors.append('Aadhar missing or invalid (cannot be changed)')
        if gender.lower() != 'women':
            errors.append('Gender must be Women')
        if not dob:
            errors.append('Date of birth is required')
        if not address:
            errors.append('Address is required')
        if not location:
            errors.append('Location is required')
        if not blood_group:
            errors.append('Blood group is required')
        if other:
            interests.append(other)
        if not (interests and len(interests) > 0):
            errors.append('Please select at least one interest')
        if not bio:
            errors.append('Bio is required')

        # handle profile picture
        file = request.files.get('profile_pic')
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            path = os.path.join(UPLOAD_FOLDER, filename)
            file.save(path)
            profile['profile_pic'] = filename

        # update profile fields (preserve username and aadhar)
        profile.update({
            'email': email,
            'phone': phone,
            'aadhar': aadhar,
            'gender': gender,
            'dob': dob,
            'blood_group': blood_group,
            'bio': bio,
            'interests': interests,
            'address': address,
            'location': location
        })

        if errors:
            for e in errors:
                flash(e, 'error')
            db['users'][user]['profile'] = profile
            save_db(db)
            return render_template('profile_edit.html', username=user, profile=profile)

        db['users'][user]['profile'] = profile
        save_db(db)
        flash('Profile updated', 'success')
        return redirect('/profile')

    return render_template('profile_edit.html', username=user, profile=profile)

@app.route('/complete_profile',methods=['GET','POST'])
def complete_profile():
    if 'username' not in session:
        return redirect('/login')

    db = load_db()
    user = session['username']
    profile = db['users'][user].get('profile', {})

    if request.method == "POST":
        errors = []
        email = request.form.get('email','').strip()
        phone = request.form.get('phone','').strip()
        aadhar = request.form.get('aadhar','').strip()
        gender = request.form.get('gender','').strip()
        dob = request.form.get('dob','').strip()
        blood_group = request.form.get('blood_group','').strip()
        bio = request.form.get('bio','').strip()
        interests = request.form.getlist('interests')
        other = request.form.get('other','').strip()
        address = request.form.get('address','').strip()
        location = request.form.get('location','').strip()

        # server-side validation
        if not email or not email.endswith('@gmail.com'):
            errors.append('Email must be a valid @gmail.com address')
        if not phone or not phone.isdigit() or len(phone) != 10:
            errors.append('Phone must be a 10 digit number')
        if not aadhar or not aadhar.isdigit() or len(aadhar) != 12:
            errors.append('Aadhar must be a 12 digit number')
        if gender.lower() != 'women':
            errors.append('Gender must be Women')
        if not dob:
            errors.append('Date of birth is required')
        if not address:
            errors.append('Address is required')
        if not location:
            errors.append('Location is required')
        if not blood_group:
            errors.append('Blood group is required')
        if not bio:
            errors.append('Bio is required')

        if other:
            interests.append(other)

        if not (interests and len(interests) > 0):
            errors.append('Please select at least one interest')

        file = request.files.get('profile_pic')
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            path = os.path.join(UPLOAD_FOLDER, filename)
            file.save(path)
            profile['profile_pic'] = filename

        # populate profile with submitted values so form can re-render
        profile.update({
            'email': email,
            'phone': phone,
            'aadhar': aadhar,
            'gender': gender,
            'dob': dob,
            'blood_group': blood_group,
            'bio': bio,
            'interests': interests,
            'address': address,
            'location': location
        })

        if errors:
            for e in errors:
                flash(e, 'error')
            db['users'][user]['profile'] = profile
            save_db(db)
            return render_template('complete_profile.html', profile=profile)

        db['users'][user]['profile'] = profile
        save_db(db)
        flash('Profile saved', 'success')
        return redirect('/dashboard')

    return render_template('complete_profile.html', profile=profile)

# -------- SAFETY --------
@app.route('/safety',methods=['GET','POST'])
def safety():
    check=login_required("User")
    if check: return check
    db=load_db()
    if request.method=="POST":
        text = request.form.get('text')
        station_id = request.form.get('station')
        station_name = None
        if station_id:
            st = next((s for s in POLICE_STATIONS if str(s['id'])==str(station_id)), None)
            if st:
                station_name = st['name']
        db['complaints'].append({
            "user":session['username'],
            "text": text,
            "station": station_id,
            "station_name": station_name,
            "status":"Pending"
        })
        save_db(db)
    return render_template("safety.html",complaints=db['complaints'])


@app.route('/safety/nearby')
def safety_nearby():
    check = login_required('User')
    if check: return check
    return render_template('nearby_police.html', stations=POLICE_STATIONS, username=session.get('username'))


@app.route('/safety/complaint', methods=['GET','POST'])
def safety_complaint():
    check = login_required('User')
    if check: return check
    db = load_db()
    if request.method=='POST':
        station = request.form.get('station')
        text = request.form.get('text')
        station_name = None
        if station:
            st = next((s for s in POLICE_STATIONS if str(s['id'])==str(station)), None)
            if st:
                station_name = st['name']
        db['complaints'].append({
            'user': session['username'],
            'text': text,
            'station': station,
            'station_name': station_name,
            'status': 'Pending'
        })
        save_db(db)
        flash('Complaint filed', 'success')
        return redirect('/safety/status')

    # pass stations JSON for client-side compose
    import json as _json
    return render_template('file_complaint.html', stations=POLICE_STATIONS, stations_json=_json.dumps(POLICE_STATIONS), username=session.get('username'))


@app.route('/safety/status')
def safety_status():
    check = login_required('User')
    if check: return check
    db = load_db()
    user_complaints = [c for c in db['complaints'] if c.get('user')==session.get('username')]
    return render_template('complaint_status.html', complaints=user_complaints)

# -------- SHOP (FIXED ROUTE) --------
@app.route('/shop',methods=['GET','POST'])
def shop():
    check=login_required("User")
    if check: return check

    db=load_db()

    # ensure profile completed before shopping
    profile=db['users'][session['username']].get('profile')
    if not profile_is_complete(profile):
        flash("Complete profile before ordering","error")
        return redirect('/complete_profile')

    if request.method=="POST":
        db['orders'].append({
            "user":session['username'],
            "medicine":request.form.get('med')
        })
        save_db(db)

    return render_template("shop.html",medicines=db['medicines'])

# -------- POLICE --------
@app.route('/police',methods=['GET','POST'])
def police():
    check=login_required("Police")
    if check: return check
    db=load_db()

    # station context login: if station not set in session, allow station login
    if request.method == 'POST' and request.form.get('station_login'):
        station_id = request.form.get('station_id','').strip()
        station_email = request.form.get('station_email','').strip()
        station_state = request.form.get('station_state','').strip()
        station_district = request.form.get('station_district','').strip()
        station_location = request.form.get('station_location','').strip()

        errors = []
        if not station_id: errors.append('Station ID required')
        if not station_email: errors.append('Station email required')
        if not station_state: errors.append('Station state required')
        if not station_district: errors.append('Station district required')
        if not station_location: errors.append('Station location required')

        if errors:
            for e in errors: flash(e,'error')
            return redirect('/police')

        # set station info in session
        session['station'] = {
            'id': station_id,
            'email': station_email,
            'state': station_state,
            'district': station_district,
            'location': station_location,
            'logged_in': True
        }
        # persist station details into the police user's profile
        try:
            db_user = db['users'].get(session.get('username'))
            if db_user is None:
                db['users'][session.get('username')] = {'password':'', 'role':'Police', 'profile':{}}
                db_user = db['users'][session.get('username')]
            db_user.setdefault('profile', {})
            db_user['profile']['station_info'] = {
                'station_id': station_id,
                'email': station_email,
                'state': station_state,
                'district': station_district,
                'location': station_location
            }
            save_db(db)
        except Exception:
            pass
        flash('Station logged in','success')
        return redirect('/police')

    # handle complaint resolution (only when station logged in)
    if request.method=="POST" and request.form.get('resolve_id'):
        try:
            i=int(request.form.get('resolve_id'))
            db['complaints'][i]['status']="Resolved"
            save_db(db)
            # remember which complaint was just resolved so template can auto-expand it
            session['just_resolved'] = i
            flash('Complaint marked resolved','success')
            return redirect('/police')
        except Exception:
            flash('Invalid complaint id','error')

    # compute lists for police dashboard
    complaints = db.get('complaints', [])
    pending = [{'idx': i, **c} for i, c in enumerate(complaints) if c.get('status') == 'Pending']
    resolved = [{'idx': i, **c} for i, c in enumerate(complaints) if c.get('status') == 'Resolved']
    locations = [{'idx': i, 'user': c.get('user'), 'station_name': c.get('station_name'), 'text': c.get('text')} for i, c in enumerate(complaints) if c.get('station_name') or c.get('station')]

    just_resolved = session.pop('just_resolved', None)

    import json as _json
    state_districts_json = _json.dumps(STATE_DISTRICT_MAP)

    return render_template("police_dashboard.html", complaints=complaints, pending=pending, resolved=resolved, locations=locations, just_resolved=just_resolved, state_districts_json=state_districts_json)


@app.route('/police/portal', methods=['GET','POST'])
def police_portal():
    # public portal for station login
    if request.method == 'POST':
        station_id = request.form.get('station_id','').strip()
        station_email = request.form.get('station_email','').strip()
        password = request.form.get('password','')

        if not station_id or not station_email or not password:
            flash('All fields required','error')
            return render_template('police_portal.html')

        st = next((s for s in POLICE_STATIONS if str(s['id'])==str(station_id) and s['email']==station_email), None)
        if not st:
            flash('Station ID or email not found','error')
            return render_template('police_portal.html')

        # create or update user entry for this station
        db = load_db()
        if station_email not in db['users']:
            db['users'][station_email] = {
                'password': generate_password_hash(password),
                'role': 'Police',
                'profile': {}
            }
        else:
            # update stored password if provided
            db['users'][station_email]['password'] = generate_password_hash(password)
            db['users'][station_email]['role'] = 'Police'
            db['users'][station_email].setdefault('profile', {})
        save_db(db)

        session['username'] = station_email
        session['role'] = 'Police'
        flash('Logged in to Police Portal','success')
        return redirect('/police')

    return render_template('police_portal.html')

# -------- MEDICAL --------
@app.route('/medical',methods=['GET','POST'])
def medical():
    check=login_required("Medical")
    if check: return check

    data = load_medical_db()
    db = load_db()

    if request.method == 'POST':
        action = request.form.get('action')

        # Add a new store (legacy)
        if request.form.get('store_name') and request.form.get('address'):
            name = request.form.get('store_name')
            addr = request.form.get('address')
            data['stores'].append({"name":name,"address":addr,"medicines":[]})
            save_medical_db(data)

        # Add medicine to a store
        if action == 'add_medicine':
            store_name = request.form.get('store')
            med_name = request.form.get('med_name')
            med_price = request.form.get('med_price')
            if store_name and med_name and med_price:
                st = next((s for s in data['stores'] if s['name']==store_name), None)
                if st is not None:
                    st.setdefault('medicines',[]).append({'name':med_name,'price':med_price})
                    save_medical_db(data)

        # Update medicine price/name
        if action == 'update_medicine':
            store_name = request.form.get('store')
            old_name = request.form.get('old_med')
            new_name = request.form.get('new_med')
            new_price = request.form.get('new_price')
            st = next((s for s in data['stores'] if s['name']==store_name), None)
            if st:
                m = next((m for m in st.get('medicines',[]) if m['name']==old_name), None)
                if m:
                    if new_name: m['name']=new_name
                    if new_price: m['price']=new_price
                    save_medical_db(data)

        # Remove medicine
        if action == 'remove_medicine':
            store_name = request.form.get('store')
            rem_name = request.form.get('rem_med')
            st = next((s for s in data['stores'] if s['name']==store_name), None)
            if st:
                st['medicines'] = [m for m in st.get('medicines',[]) if m['name'] != rem_name]
                save_medical_db(data)

    # prepare orders from main DB to show
    orders = db.get('orders', [])

    return render_template('medical_dashboard.html', stores=data['stores'], orders=orders)


@app.route('/medical/orders')
def medical_orders():
    check = login_required('Medical')
    if check: return check
    db = load_db()
    orders = db.get('orders', [])
    return render_template('medical_orders.html', orders=orders)


@app.route('/medical/details', methods=['GET','POST'])
def medical_details():
    check = login_required('Medical')
    if check: return check
    db = load_db()
    mdb = load_medical_db()
    user = session['username']

    # ensure profile dict exists
    if db['users'][user].get('profile') is None:
        db['users'][user]['profile'] = {}

    if request.method == 'POST':
        store_name = request.form.get('store_name','').strip()
        place = request.form.get('place','').strip()
        store_license = request.form.get('store_license','').strip()
        start_date = request.form.get('start_date','').strip()
        working_time = request.form.get('working_time','').strip()

        errors = []
        if not store_name: errors.append('Store name required')
        if not place: errors.append('Place required')
        if not store_license: errors.append('Store licence required')
        if not start_date: errors.append('Start date required')
        if not working_time: errors.append('Working time required')

        if errors:
            for e in errors: flash(e,'error')
            return render_template('medical_details.html')

        # save to medical_db with owner
        mdb['stores'].append({
            'name': store_name,
            'place': place,
            'license': store_license,
            'start_date': start_date,
            'working_time': working_time,
            'medicines': [],
            'owner': user
        })
        save_medical_db(mdb)

        # save to user profile
        db['users'][user]['profile']['store_info'] = {
            'name': store_name,
            'place': place,
            'license': store_license,
            'start_date': start_date,
            'working_time': working_time
        }
        save_db(db)
        flash('Store details saved','success')
        return redirect('/medical')

    return render_template('medical_details.html')

# -------- ADMIN --------
@app.route('/admin',methods=['GET','POST'])
def admin():
    check=login_required("Admin")
    if check: return check
    db=load_db()
    if request.method=="POST":
        db['users'].pop(request.form.get('user'),None)
        save_db(db)
    return render_template("admin_dashboard.html",users=db['users'])

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

# -------- RUN --------
if __name__=="__main__":
    app.run(debug=True)
