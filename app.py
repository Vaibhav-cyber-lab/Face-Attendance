import os, sqlite3, base64, io, csv, secrets, calendar
from datetime import datetime, date
from functools import wraps
from urllib.parse import quote
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_file
import cv2
import numpy as np

app = Flask(__name__, template_folder=".")
app.secret_key = os.environ.get("SECRET_KEY", "replace-this-secret")
DATA_DIR = os.environ.get("DATA_DIR", os.path.join(os.path.dirname(__file__), "data"))
os.makedirs(DATA_DIR, exist_ok=True)
FACES = os.path.join(DATA_DIR, "faces")
os.makedirs(FACES, exist_ok=True)
DB = os.path.join(DATA_DIR, "attendance.db")
MODEL = os.path.join(DATA_DIR, "trainer.yml")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "ChangeMe123!")
PERIODS = [("Period 1","09:00","09:50"),("Period 2","09:50","10:40"),("Period 3","10:40","11:30"),
           ("Period 4","11:30","12:20"),("Period 5","12:20","13:10"),("Period 6","14:00","14:50"),
           ("Period 7","14:50","15:40")]

def connect():
    c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; return c

with connect() as c:
    c.execute("CREATE TABLE IF NOT EXISTS students(id INTEGER PRIMARY KEY, roll TEXT UNIQUE, name TEXT, phone TEXT DEFAULT '')")
    c.execute("""CREATE TABLE IF NOT EXISTS attendance(id INTEGER PRIMARY KEY, student_id INTEGER, day TEXT, period TEXT, marked_at TEXT,
              UNIQUE(student_id,day,period))""")

def admin(fn):
    @wraps(fn)
    def inner(*a,**kw):
        if not session.get("admin"): return redirect(url_for("login"))
        return fn(*a,**kw)
    return inner

def current_period():
    hm=datetime.now().strftime("%H:%M")
    return next((p[0] for p in PERIODS if p[1] <= hm < p[2]), None)

def face_from(gray):
    detector=cv2.CascadeClassifier(cv2.data.haarcascades+"haarcascade_frontalface_default.xml")
    found=detector.detectMultiScale(gray,1.2,5,minSize=(80,80))
    if len(found)==0: return None
    x,y,w,h=max(found,key=lambda r:r[2]*r[3])
    return cv2.resize(gray[y:y+h,x:x+w],(200,200))

@app.route("/")
def home():
    if not session.get("admin"): return render_template("home.html")
    with connect() as c:
        students=c.execute("SELECT * FROM students ORDER BY roll").fetchall()
        count=c.execute("SELECT COUNT(*) FROM attendance WHERE day=?",(date.today().isoformat(),)).fetchone()[0]
    return render_template("dashboard.html",students=students,count=count,period=current_period(),periods=PERIODS)

@app.route("/login",methods=["GET","POST"])
def login():
    if request.method=="POST":
        if secrets.compare_digest(request.form.get("password",""),ADMIN_PASSWORD):
            session["admin"]=True; return redirect(url_for("home"))
        flash("Incorrect password.")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear(); return redirect(url_for("home"))

@app.route("/students/add",methods=["POST"])
@admin
def add_student():
    roll=request.form.get("roll","").strip(); name=request.form.get("name","").strip()
    phone=request.form.get("phone","").strip(); photo=request.files.get("photo")
    if not roll or not name or not photo: flash("Roll, name and face photo are required."); return redirect(url_for("home"))
    img=cv2.imdecode(np.frombuffer(photo.read(),np.uint8),cv2.IMREAD_GRAYSCALE)
    face=face_from(img) if img is not None else None
    if face is None: flash("No face found. Upload a clear front-facing photo."); return redirect(url_for("home"))
    try:
        with connect() as c: sid=c.execute("INSERT INTO students(roll,name,phone) VALUES(?,?,?)",(roll,name,phone)).lastrowid
        os.makedirs(os.path.join(FACES,str(sid)),exist_ok=True)
        cv2.imwrite(os.path.join(FACES,str(sid),"face.png"),face)
        flash("Student added. Train the model next.")
    except sqlite3.IntegrityError: flash("Roll number already exists.")
    return redirect(url_for("home"))

@app.route("/students/delete/<int:sid>",methods=["POST"])
@admin
def delete_student(sid):
    with connect() as c:
        c.execute("DELETE FROM attendance WHERE student_id=?",(sid,))
        c.execute("DELETE FROM students WHERE id=?",(sid,))
    import shutil; shutil.rmtree(os.path.join(FACES,str(sid)),ignore_errors=True)
    flash("Student and their attendance records deleted."); return redirect(url_for("home"))

@app.route("/train",methods=["POST"])
@admin
def train():
    if not hasattr(cv2,"face"): flash("Face module missing. Install opencv-contrib-python-headless."); return redirect(url_for("home"))
    imgs=[]; labels=[]
    with connect() as c: students=c.execute("SELECT id FROM students").fetchall()
    for s in students:
        folder=os.path.join(FACES,str(s["id"]))
        if os.path.isdir(folder):
            for fn in os.listdir(folder):
                im=cv2.imread(os.path.join(folder,fn),0)
                if im is not None: imgs.append(cv2.resize(im,(200,200))); labels.append(s["id"])
    if not imgs: flash("Add student photos first."); return redirect(url_for("home"))
    model=cv2.face.LBPHFaceRecognizer_create(); model.train(imgs,np.array(labels,dtype=np.int32)); model.save(MODEL)
    flash(f"Model trained with {len(imgs)} face photo(s)."); return redirect(url_for("home"))

@app.route("/camera")
@admin
def camera(): return render_template("camera.html",period=current_period())

@app.route("/api/recognize",methods=["POST"])
@admin
def recognize():
    if not os.path.exists(MODEL): return jsonify(message="Train the model first.")
    if not hasattr(cv2,"face"): return jsonify(message="Face recognizer not installed.")
    try:
        raw=request.json.get("image","").split(",",1)[-1]
        frame=cv2.imdecode(np.frombuffer(base64.b64decode(raw),np.uint8),0)
        face=face_from(frame) if frame is not None else None
        if face is None: return jsonify(message="No face detected.")
        rec=cv2.face.LBPHFaceRecognizer_create(); rec.read(MODEL)
        sid,confidence=rec.predict(face)
        if confidence>60: return jsonify(message="Face not recognized; improve lighting.")
        period=current_period()
        if not period: return jsonify(message="No active class period. Check timetable.")
        with connect() as c:
            s=c.execute("SELECT * FROM students WHERE id=?",(int(sid),)).fetchone()
            if not s: return jsonify(message="Student not found.")
            c.execute("INSERT OR IGNORE INTO attendance(student_id,day,period,marked_at) VALUES(?,?,?,?)",
                      (sid,date.today().isoformat(),period,datetime.now().isoformat(timespec="seconds")))
        return jsonify(message=f"Attendance checked: {s['name']} ({s['roll']}) — {period}")
    except Exception:
        app.logger.exception("Recognition failed"); return jsonify(message="Recognition error; check server logs.")

@app.route("/attendance")
@admin
def attendance():
    day=request.args.get("day",date.today().isoformat())
    with connect() as c:
        rows=c.execute("""SELECT s.roll,s.name,a.day,a.period,a.marked_at FROM attendance a JOIN students s ON s.id=a.student_id
                          WHERE a.day=? ORDER BY a.period,s.roll""",(day,)).fetchall()
    return render_template("attendance.html",rows=rows,day=day)

@app.route("/student")
def student():
    roll=request.args.get("roll","").strip(); rows=[]
    if roll:
        with connect() as c:
            s=c.execute("SELECT id FROM students WHERE roll=?",(roll,)).fetchone()
            if s: rows=c.execute("SELECT day,period,marked_at FROM attendance WHERE student_id=? ORDER BY day DESC",(s["id"],)).fetchall()
    return render_template("student.html",roll=roll,rows=rows)

@app.route("/reports/monthly")
@admin
def monthly():
    month=request.args.get("month",date.today().strftime("%Y-%m"))
    yy,mm=map(int,month.split("-"))
    scheduled=sum(date(yy,mm,d).weekday()<5 for d in range(1,calendar.monthrange(yy,mm)[1]+1))*7
    with connect() as c:
        students=c.execute("SELECT * FROM students ORDER BY roll").fetchall()
        counts={r["student_id"]:r["n"] for r in c.execute("SELECT student_id,COUNT(*) n FROM attendance WHERE substr(day,1,7)=? GROUP BY student_id",(month,))}
    report=[{"roll":s["roll"],"name":s["name"],"attended":counts.get(s["id"],0),
             "scheduled":scheduled,"pct":round(counts.get(s["id"],0)*100/scheduled,1) if scheduled else 0} for s in students]
    return render_template("monthly.html",month=month,report=report)

@app.route("/reports/export")
@admin
def export():
    month=request.args.get("month",date.today().strftime("%Y-%m"))
    with connect() as c:
        rows=c.execute("""SELECT s.roll,s.name,COUNT(a.id) attended FROM students s LEFT JOIN attendance a
        ON a.student_id=s.id AND substr(a.day,1,7)=? GROUP BY s.id ORDER BY s.roll""",(month,)).fetchall()
    out=io.StringIO(); w=csv.writer(out); w.writerow(["Month","Roll","Name","Periods Attended"])
    for r in rows: w.writerow([month,r["roll"],r["name"],r["attended"]])
    return send_file(io.BytesIO(out.getvalue().encode("utf-8-sig")),mimetype="text/csv",as_attachment=True,download_name=f"attendance_{month}.csv")

@app.route("/whatsapp")
@admin
def whatsapp():
    month=request.args.get("month",date.today().strftime("%Y-%m")); yy,mm=map(int,month.split("-"))
    scheduled=sum(date(yy,mm,d).weekday()<5 for d in range(1,calendar.monthrange(yy,mm)[1]+1))*7
    with connect() as c:
        students=c.execute("SELECT * FROM students WHERE phone!='' ORDER BY roll").fetchall()
        counts={r["student_id"]:r["n"] for r in c.execute("SELECT student_id,COUNT(*) n FROM attendance WHERE substr(day,1,7)=? GROUP BY student_id",(month,))}
    links=[]
    for s in students:
        n=counts.get(s["id"],0); pct=round(n*100/scheduled,1) if scheduled else 0
        phone="".join(ch for ch in s["phone"] if ch.isdigit())
        if len(phone)==10: phone="91"+phone
        msg=quote(f"Attendance report {month}: {s['name']} ({s['roll']}) attended {n}/{scheduled} periods ({pct}%).")
        links.append({"name":s["name"],"phone":s["phone"],"url":f"https://wa.me/{phone}?text={msg}"})
    return render_template("whatsapp.html",links=links,month=month)

if __name__=="__main__": app.run(host="0.0.0.0",port=int(os.environ.get("PORT","5000")))
