# app.py
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from connections import SessionLocal
from models import User, CompleteProfile, LiveClass, RevisionMaterial, Video, Teacher
from datetime import datetime
from functools import wraps
from sqlalchemy import func, or_
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import os

# -----------------------
# Config / Uploads
# -----------------------
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'ppt', 'pptx', 'xls', 'xlsx'}
UPLOAD_FOLDER = 'static/materials'

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

app = Flask(__name__)
app.secret_key = "silaswanyamarechosilasayangaamukowaivansamuel"
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# -----------------------
# Role-based decorator
# -----------------------
def role_required(required_role):
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if "user_id" not in session or "role" not in session:
                return redirect(url_for("login"))
            if session["role"] != required_role:
                return "Access Denied", 403
            return f(*args, **kwargs)
        return wrapped
    return decorator

# -----------------------
# Home
# -----------------------
@app.route('/')
def home():
    return render_template('admin/landing_page.html')

# -----------------------
# Login
# -----------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        db = SessionLocal()
        try:
            user = db.query(User).filter_by(username=username).first()

            if user:
                # Try secure check first, fallback to plain equality (backwards compatibility)
                valid = False
                try:
                    valid = check_password_hash(user.password, password)
                except Exception:
                    valid = False

                if not valid:
                    # fallback: maybe password is stored as plain text in older DBs
                    valid = (user.password == password)

                if valid:
                    session["user_id"] = user.id
                    session["role"] = user.role

                    # Admin login
                    if user.role == "admin":
                        return redirect(url_for("admin_dashboard"))

                    # Teacher login
                    elif user.role == "teacher":
                        teacher_profile = db.query(Teacher).filter_by(user_id=user.id).first()

                        if not teacher_profile:
                            # Teacher has not yet completed their profile
                            return redirect(url_for("complete_teacher_profile", user_id=user.id))

                        # ✅ Require admin approval before access
                        if not teacher_profile.is_approved:
                            flash("Your profile is awaiting admin approval. Please wait before accessing your dashboard.", "warning")
                            session.clear()
                            return redirect(url_for("login"))

                        # Approved teachers can access dashboard
                        return redirect(url_for("teacher_dashboard"))

                    # Student login
                    elif user.role == "student":
                        profile = db.query(CompleteProfile).filter_by(user_id=user.id).first()

                        if profile:
                            return redirect(url_for("student_dashboard"))
                        else:
                            return redirect(url_for("complete_profile"))

                    else:
                        return "Role not recognized", 403

                else:
                    flash("Invalid credentials", "danger")
            else:
                flash("Invalid credentials", "danger")

        finally:
            db.close()

    return render_template("login.html")

# -----------------------
# Register
# -----------------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    message = ""
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()
        confirm_password = request.form['confirm_password'].strip()
        role = request.form.get("role", "student")  # default role: student

        if password != confirm_password:
            message = "Passwords do not match"
        else:
            db = SessionLocal()
            try:
                existing_user = db.query(User).filter_by(username=username).first()
                if existing_user:
                    message = "Username already exists"
                else:
                    # store hashed password
                    hashed = generate_password_hash(password)
                    new_user = User(username=username, password=hashed, role=role)
                    db.add(new_user)
                    db.commit()

                    # Redirect based on role
                    # We'll redirect teacher to login so they can login then complete profile
                    if role == "teacher":
                        flash("Account created. Please login and complete your profile.", "success")
                        return redirect(url_for('login'))
                    elif role == "student":
                        flash("Account created. Please login.", "success")
                        return redirect(url_for('login'))
                    else:
                        flash("Account created. Please login.", "success")
                        return redirect(url_for('login'))
            finally:
                db.close()

    return render_template('register.html', message=message)

# -----------------------
# Logout
# -----------------------
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for("login"))

# -----------------------
# Forgot / Reset password
# -----------------------
@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    message = ""
    if request.method == 'POST':
        username = request.form['username']
        db = SessionLocal()
        try:
            user = db.query(User).filter_by(username=username).first()
            if user:
                # For now we redirect to reset page (no email). You might want to implement email.
                return redirect(url_for('reset_password', username=username))
            else:
                message = "No account found with that username."
        finally:
            db.close()
    return render_template('forgot_password.html', message=message)

@app.route('/reset_password/<username>', methods=['GET', 'POST'])
def reset_password(username):
    message = ""
    if request.method == 'POST':
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']

        if new_password != confirm_password:
            message = "Passwords do not match."
        else:
            db = SessionLocal()
            try:
                user = db.query(User).filter_by(username=username).first()
                if user:
                    user.password = generate_password_hash(new_password)
                    db.commit()
                    flash("Password updated successfully! You can now log in.", "success")
            finally:
                db.close()
            return redirect(url_for('login'))
    return render_template('reset_password.html', message=message, username=username)

# -----------------------
# Complete Student Profile
# -----------------------
@app.route('/complete_profile', methods=['GET', 'POST'])
def complete_profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    db = SessionLocal()
    try:
        user = db.query(User).filter_by(id=user_id).first()
        if not user:
            flash("User not found", "danger")
            return redirect(url_for('login'))

        profile = db.query(CompleteProfile).filter_by(user_id=user.id).first()

        if request.method == 'POST':
            first_name = request.form.get('first_name', '').strip()
            middle_name = request.form.get('middle_name', '').strip()
            last_name = request.form.get('last_name', '').strip()
            contact_no = request.form.get('contact_no', '').strip()
            guardian_name = request.form.get('guardian_name', '').strip()
            form_selected = request.form.get('form', '').strip()

            if not first_name or not last_name or not contact_no or not guardian_name or not form_selected:
                flash("Please fill all required fields", "danger")
                profile_data = profile.__dict__ if profile else {}
                return render_template('students/complete_profile.html', profile=profile_data)

            if profile:
                profile.first_name = first_name
                profile.middle_name = middle_name
                profile.last_name = last_name
                profile.contact_no = contact_no
                profile.guardian_name = guardian_name
                profile.form = form_selected
            else:
                profile = CompleteProfile(
                    user_id=user.id,
                    first_name=first_name,
                    middle_name=middle_name,
                    last_name=last_name,
                    contact_no=contact_no,
                    guardian_name=guardian_name,
                    form=form_selected
                )
                db.add(profile)

            db.commit()
            flash("Profile saved successfully!", "success")
            return redirect(url_for("student_dashboard"))

        profile_data = profile.__dict__ if profile else {}
        return render_template('students/complete_profile.html', profile=profile_data)
    finally:
        db.close()

# -----------------------
# Complete Teacher Profile
# -----------------------
@app.route("/complete_teacher_profile/<int:user_id>", methods=["GET", "POST"])
def complete_teacher_profile(user_id):
    db = SessionLocal()
    try:
        user = db.query(User).filter_by(id=user_id, role="teacher").first()
        if not user:
            flash("Invalid or missing teacher account.", "danger")
            return redirect(url_for("login"))

        existing = db.query(Teacher).filter_by(user_id=user.id).first()
        if existing:
            flash("Profile already exists. Please login.", "info")
            return redirect(url_for("login"))

        if request.method == "POST":
            teacher_name = request.form.get("teacher_name").strip()
            phone_number = request.form.get("phone_number").strip()
            subject = request.form.get("subject").strip()

            new_teacher = Teacher(
                user_id=user.id,
                teacher_name=teacher_name,
                phone_number=phone_number,
                subject=subject
            )
            db.add(new_teacher)
            db.commit()
            flash("Profile completed successfully!", "success")
            return redirect(url_for("login"))

        return render_template("teachers/teachers.html", user=user)
    finally:
        db.close()

# -----------------------
# Student Dashboard
# -----------------------
@app.route("/student")
def student_dashboard():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    db = SessionLocal()
    try:
        user = db.query(User).filter_by(id=session["user_id"]).first()
        if not user:
            return redirect(url_for("login"))

        profile = db.query(CompleteProfile).filter_by(user_id=user.id).first()
        if not profile:
            return redirect(url_for("complete_profile"))

        student_form = (profile.form or "").strip().lower()

        if not profile.is_active:
            flash("Your account is not active. Please contact admin to make payment.", "warning")
            return render_template(
                "students/student_dashboard.html",
                student={
                    "full_name": f"{profile.first_name} {profile.last_name}",
                    "form": profile.form,
                    "phone": profile.contact_no,
                    "guardian_name": profile.guardian_name,
                    "is_active": profile.is_active
                },
                live_classes=[],
                revision_materials=[],
                videos=[],
                current_year=datetime.now().year
            )

        live_classes = db.query(LiveClass).filter(
            func.lower(func.trim(LiveClass.form)).in_([student_form, "all", ""])
        ).all()

        revision_materials = db.query(RevisionMaterial).filter(
            func.lower(func.trim(RevisionMaterial.form)).in_([student_form, "all", ""])
        ).all()

        videos = db.query(Video).filter(
            func.lower(func.trim(Video.form)).in_([student_form, "all", ""])
        ).all()

        return render_template(
            "students/student_dashboard.html",
            student={
                "full_name": f"{profile.first_name} {profile.last_name}",
                "form": profile.form,
                "phone": profile.contact_no,
                "guardian_name": profile.guardian_name,
                "is_active": profile.is_active
            },
            live_classes=live_classes,
            revision_materials=revision_materials,
            videos=videos,
            current_year=datetime.now().year
        )
    finally:
        db.close()

# -----------------------
# Teacher Dashboard
# -----------------------
@app.route("/teacher_dashboard")
def teacher_dashboard():
    if 'user_id' not in session or session.get('role') != 'teacher':
        return redirect(url_for('login'))

    db = SessionLocal()
    try:
        teacher = db.query(Teacher).filter_by(user_id=session['user_id']).first()
        # provide teacher relevant lists
        live_classes = db.query(LiveClass).all()
        revision_materials = db.query(RevisionMaterial).all()
        # you can filter to teacher's items if you add a column (teacher_id) to models
        return render_template('teachers/teachers_dashboard.html', teacher=teacher,
                               live_classes=live_classes, revision_materials=revision_materials)
    finally:
        db.close()

# -----------------------
# Admin Dashboard
# -----------------------
@app.route('/admin')
@role_required("admin")
def admin_dashboard():
    db = SessionLocal()
    try:
        live_classes = db.query(LiveClass).all()
        revision_materials = db.query(RevisionMaterial).all()
        videos = db.query(Video).all()
        current_year = datetime.now().year

        # 🧩 Add counts for dashboard cards
        total_students = db.query(CompleteProfile).count()
        total_teachers = db.query(Teacher).count()

        # 🧩 Add pending approval counts
        pending_teachers = db.query(Teacher).filter_by(is_approved=False).count()
        pending_students = (
            db.query(CompleteProfile).filter_by(is_approved=False).count()
            if hasattr(CompleteProfile, 'is_approved')
            else 0
        )

        return render_template(
            "admin/admin_dashboard.html",
            live_classes=live_classes,
            revision_materials=revision_materials,
            videos=videos,
            current_year=current_year,
            total_students=total_students,
            total_teachers=total_teachers,
            pending_teachers=pending_teachers,
            pending_students=pending_students
        )
    finally:
        db.close()

# -----------------------
# Admin CRUD - Live Classes
# -----------------------
@app.route("/admin/live_class/add", methods=["POST","GET"])
@role_required("admin")
def add_live_class():
    db = SessionLocal()
    try:
        title = request.form.get("title")
        link = request.form.get("link")
        time = request.form.get("time")
        form = request.form.get("form")
        subject = request.form.get("subject")

        if not title or not link:
            flash("Title and Link are required!", "danger")
            return redirect(url_for("admin_dashboard"))

        new_class = LiveClass(
            title=title,
            link=link,
            time=time,
            form=form,
            subject=subject
        )

        db.add(new_class)
        db.commit()
        flash("✅ Live class added successfully!", "success")
    finally:
        db.close()

    return redirect(url_for("admin_dashboard"))


@app.route("/admin/live_class/edit/<int:class_id>", methods=["GET", "POST"])
@role_required("admin")
def edit_live_class(class_id):
    db = SessionLocal()
    try:
        cls = db.query(LiveClass).get(class_id)
        if request.method == "POST":
            cls.title = request.form.get("title")
            cls.link = request.form.get("link")
            cls.time = request.form.get("time")
            cls.form = request.form.get("form")
            cls.subject = request.form.get("subject")
            db.commit()
            flash("Live class updated!", "success")
            return redirect(url_for("admin_dashboard"))
        return render_template("edit_live_class.html", cls=cls)
    finally:
        db.close()

@app.route("/admin/live_class/delete/<int:class_id>", methods=["POST"])
@role_required("admin")
def delete_live_class(class_id):
    db = SessionLocal()
    try:
        cls = db.query(LiveClass).get(class_id)
        if cls:
            db.delete(cls)
            db.commit()
            flash("Live class deleted!", "success")
        else:
            flash("Class not found.", "danger")
    finally:
        db.close()
    return redirect(url_for("admin_dashboard"))

# -----------------------
# Admin CRUD - Materials
# -----------------------
@app.route('/admin/material/add', methods=['GET', 'POST'])
@role_required("admin")
def add_material():
    if request.method == 'POST':
        db = SessionLocal()
        try:
            title = request.form.get('title', '').strip()
            subject = request.form.get('subject', '').strip()
            form_class = request.form.get('form', '').strip()
            link = request.form.get('link', '').strip()
            file = request.files.get('file')

            if not title or not subject or not form_class:
                flash("All fields are required", "danger")
                return redirect(url_for('admin_dashboard'))

            # Case 1: Google Drive link
            if link:
                if "drive.google.com/file/d/" in link:
                    file_id = link.split("/d/")[1].split("/")[0]
                    link = f"https://drive.google.com/uc?export=download&id={file_id}"

            # Case 2: File upload
            elif file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                link = url_for('static', filename=f'materials/{filename}')

            else:
                flash("You must provide either a file or a Google Drive link.", "danger")
                return redirect(url_for('admin_dashboard'))

            new_material = RevisionMaterial(
                title=title,
                subject=subject,
                form=form_class,
                link=link
            )
            db.add(new_material)
            db.commit()
            flash("Material added successfully!", "success")
        finally:
            db.close()

    return redirect(url_for('admin_dashboard'))

@app.route("/admin/material/edit/<int:material_id>", methods=["GET", "POST"])
@role_required("admin")
def edit_material(material_id):
    db = SessionLocal()
    try:
        mat = db.query(RevisionMaterial).get(material_id)
        if request.method == "POST":
            mat.title = request.form.get("title")
            mat.link = request.form.get("link")
            mat.form = request.form.get("form")
            db.commit()
            flash("Material updated!", "success")
            return redirect(url_for("admin_dashboard"))
        return render_template("edit_material.html", mat=mat)
    finally:
        db.close()

@app.route("/admin/material/delete/<int:material_id>", methods=["POST"])
@role_required("admin")
def delete_material(material_id):
    db = SessionLocal()
    try:
        mat = db.query(RevisionMaterial).get(material_id)
        if not mat:
            flash("Material not found!", "danger")
            return redirect(url_for("admin_dashboard"))
        db.delete(mat)
        db.commit()
        flash("Material deleted!", "success")
    finally:
        db.close()
    return redirect(url_for("admin_dashboard"))

# -----------------------
# Admin CRUD - Videos
# -----------------------
@app.route('/admin/video/add', methods=['GET', 'POST'])
@role_required("admin")
def add_video():
    if request.method == 'POST':
        db = SessionLocal()
        try:
            title = request.form.get('title', '').strip()
            link = request.form.get('link', '').strip()
            form_class = request.form.get('form', '').strip()
            subject = request.form.get('subject', '').strip()

            if not title or not link or not form_class or not subject:
                flash("All fields are required", "danger")
                return redirect(url_for('admin_dashboard'))

            if "drive.google.com/file/d/" in link:
                file_id = link.split("/d/")[1].split("/")[0]
                link = f"https://drive.google.com/file/d/{file_id}/preview"

            new_video = Video(
                title=title,
                link=link,
                form=form_class,
                subject=subject
            )
            db.add(new_video)
            db.commit()
            flash("Video added successfully!", "success")
        finally:
            db.close()

    return redirect(url_for('admin_dashboard'))

@app.route("/admin/video/edit/<int:video_id>", methods=["GET", "POST"])
@role_required("admin")
def edit_video(video_id):
    db = SessionLocal()
    try:
        video = db.query(Video).get(video_id)
        if request.method == "POST":
            video.title = request.form.get("title")
            video.link = request.form.get("link")
            video.form = request.form.get("form")
            db.commit()
            flash("Video updated!", "success")
            return redirect(url_for("admin_dashboard"))
        return render_template("edit_video.html", video=video)
    finally:
        db.close()

@app.route("/admin/video/delete/<int:video_id>")
@role_required("admin")
def delete_video(video_id):
    db = SessionLocal()
    try:
        video = db.query(Video).get(video_id)
        db.delete(video)
        db.commit()
        flash("Video deleted!", "success")
    finally:
        db.close()
    return redirect(url_for("admin_dashboard"))

# -----------------------
# Manage students (admin)
# -----------------------
@app.route("/admin/manage_students")
@role_required("admin")
def manage_students():
    db = SessionLocal()
    try:
        search_query = request.args.get("search", "").strip().lower()
        sort_by = request.args.get("sort", "id")
        sort_order = request.args.get("order", "asc")

        students = db.query(CompleteProfile)

        if search_query:
            students = students.filter(
                (func.lower(CompleteProfile.first_name).like(f"%{search_query}%")) |
                (func.lower(CompleteProfile.last_name).like(f"%{search_query}%")) |
                (func.lower(CompleteProfile.form).like(f"%{search_query}%")) |
                (func.lower(CompleteProfile.contact_no).like(f"%{search_query}%"))
            )

        sort_column = getattr(CompleteProfile, sort_by, CompleteProfile.id)
        if sort_order == "desc":
            sort_column = sort_column.desc()

        students = students.order_by(sort_column).all()
        return render_template("admin/admin_manage_students.html",
                               students=students, sort_by=sort_by, sort_order=sort_order)
    finally:
        db.close()

@app.route('/mark_paid/<int:student_id>')
@role_required("admin")
def mark_paid(student_id):
    db = SessionLocal()
    try:
        student = db.query(CompleteProfile).filter_by(id=student_id).first()
        if not student:
            flash("Student not found.", "danger")
            return redirect(url_for("admin_dashboard"))

        student.is_active = True
        db.commit()
        flash(f"{student.first_name} {student.last_name} has been activated (paid).", "success")
    except Exception as e:
        db.rollback()
        flash("Error activating student.", "danger")
        print(f"Error: {e}")
    finally:
        db.close()

    return redirect(url_for("admin_dashboard"))

@app.route('/mark_blocked/<int:student_id>')
@role_required("admin")
def mark_blocked(student_id):
    db = SessionLocal()
    try:
        student = db.query(CompleteProfile).filter_by(id=student_id).first()
        if not student:
            flash("Student not found.", "danger")
            return redirect(url_for("admin_dashboard"))

        student.is_active = False
        db.commit()
        flash(f"{student.first_name} {student.last_name} has been blocked.", "warning")
    except Exception as e:
        db.rollback()
        flash("Error blocking student. Please try again.", "danger")
        print(f"Error: {e}")
    finally:
        db.close()

    return redirect(url_for("admin_dashboard"))

# -----------------------
# AJAX endpoints (admin)
# -----------------------
@app.route("/api/add_item", methods=["POST"])
@role_required("admin")
def add_item():
    data = request.json
    db = SessionLocal()
    try:
        if data["type"] == "live":
            new = LiveClass(
                title=data["title"],
                link=data["link"],
                time=data.get("time"),
                form=data.get("form"),
                subject=data.get("subject"),
                active=data.get("active", False)
            )
        elif data["type"] == "material":
            new = RevisionMaterial(
                title=data["title"],
                link=data["link"],
                form=data.get("form"),
                subject=data.get("subject")
            )
        elif data["type"] == "video":
            new = Video(
                title=data["title"],
                link=data["link"],
                form=data.get("form"),
                subject=data.get("subject")
            )
        db.add(new)
        db.commit()
        return jsonify({"success": True, "id": new.id})
    except Exception as e:
        db.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        db.close()

@app.route("/api/update_item/<string:item_type>/<int:item_id>", methods=["PUT"])
@role_required("admin")
def update_item(item_type, item_id):
    data = request.json
    db = SessionLocal()
    try:
        model = {"live": LiveClass, "material": RevisionMaterial, "video": Video}.get(item_type)
        item = db.query(model).get(item_id)
        if not item:
            return jsonify({"success": False, "error": "Not found"}), 404

        for k, v in data.items():
            setattr(item, k, v)
        db.commit()
        return jsonify({"success": True})
    except Exception as e:
        db.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        db.close()

@app.route("/api/delete_item/<string:item_type>/<int:item_id>", methods=["DELETE"])
@role_required("admin")
def delete_item(item_type, item_id):
    db = SessionLocal()
    try:
        model = {"live": LiveClass, "material": RevisionMaterial, "video": Video}.get(item_type)
        item = db.query(model).get(item_id)
        if not item:
            return jsonify({"success": False, "error": "Not found"}), 404
        db.delete(item)
        db.commit()
        return jsonify({"success": True})
    except Exception as e:
        db.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        db.close()

# -----------------------
# Teacher CRUD - Live Classes & Materials (single, non-duplicate implementations)
# -----------------------
@app.route("/teacher/live_class/add", methods=["GET", "POST"])
@role_required("teacher")
def teacher_add_live_class():
    if request.method == "POST":
        db = SessionLocal()
        try:
            title = request.form.get("title", "").strip()
            link = request.form.get("link", "").strip()
            time = request.form.get("time", "").strip()
            form = request.form.get("form", "").strip()
            subject = request.form.get("subject", "").strip()

            if not title or not link:
                flash("Title and link are required.", "danger")
                return redirect(url_for("teacher_dashboard"))

            new_class = LiveClass(
                title=title,
                link=link,
                time=time,
                form=form,
                subject=subject
            )
            # If you add teacher_id to the LiveClass model, set it here:
            # new_class.teacher_id = session["user_id"]

            db.add(new_class)
            db.commit()
            flash("✅ Live class added successfully!", "success")
        finally:
            db.close()
        return redirect(url_for("teacher_dashboard"))

    return render_template("teachers/add_live_class.html")

@app.route("/teacher/material/add", methods=["GET", "POST"])
@role_required("teacher")
def teacher_add_material():
    if request.method == "POST":
        db = SessionLocal()
        try:
            title = request.form.get("title", "").strip()
            subject = request.form.get("subject", "").strip()
            form_class = request.form.get("form", "").strip()
            link = request.form.get("link", "").strip()
            file = request.files.get("file")

            if not title or not subject or not form_class:
                flash("All fields are required!", "danger")
                return redirect(url_for("teacher_dashboard"))

            if link:
                if "drive.google.com/file/d/" in link:
                    file_id = link.split("/d/")[1].split("/")[0]
                    link = f"https://drive.google.com/uc?export=download&id={file_id}"
            elif file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                file.save(file_path)
                link = url_for("static", filename=f"materials/{filename}")
            else:
                flash("Please upload a valid file or Google Drive link.", "danger")
                return redirect(url_for("teacher_dashboard"))

            new_material = RevisionMaterial(
                title=title,
                subject=subject,
                form=form_class,
                link=link
            )
            # If adding teacher relationship, set new_material.teacher_id = session["user_id"]

            db.add(new_material)
            db.commit()
            flash("✅ Material uploaded successfully!", "success")
        finally:
            db.close()
        return redirect(url_for("teacher_dashboard"))

    return render_template("teachers/add_material.html")

# Optional teacher edit/delete routes (allowing teachers to edit/delete any item - change if you add ownership fields)
@app.route("/teacher/live_class/edit/<int:class_id>", methods=["GET", "POST"])
@role_required("teacher")
def teacher_edit_live_class(class_id):
    db = SessionLocal()
    try:
        cls = db.query(LiveClass).get(class_id)
        if request.method == "POST":
            cls.title = request.form.get("title")
            cls.link = request.form.get("link")
            cls.time = request.form.get("time")
            cls.form = request.form.get("form")
            cls.subject = request.form.get("subject")
            db.commit()
            flash("✅ Live class updated!", "success")
            return redirect(url_for("teacher_dashboard"))
        return render_template("edit_live_class.html", cls=cls)
    finally:
        db.close()

@app.route("/teacher/live_class/delete/<int:class_id>", methods=["POST"])
@role_required("teacher")
def teacher_delete_live_class(class_id):
    db = SessionLocal()
    try:
        cls = db.query(LiveClass).get(class_id)
        if cls:
            db.delete(cls)
            db.commit()
            flash("✅ Live class deleted!", "success")
        else:
            flash("Class not found.", "danger")
    finally:
        db.close()
    return redirect(url_for("teacher_dashboard"))

@app.route("/teacher/material/edit/<int:material_id>", methods=["GET", "POST"])
@role_required("teacher")
def teacher_edit_material(material_id):
    db = SessionLocal()
    try:
        mat = db.query(RevisionMaterial).get(material_id)
        if request.method == "POST":
            mat.title = request.form.get("title")
            mat.link = request.form.get("link")
            mat.form = request.form.get("form")
            mat.subject = request.form.get("subject")
            db.commit()
            flash("Material updated!", "success")
            return redirect(url_for("teacher_dashboard"))
        return render_template("edit_material.html", mat=mat)
    finally:
        db.close()

@app.route("/teacher/material/delete/<int:material_id>", methods=["POST"])
@role_required("teacher")
def teacher_delete_material(material_id):
    db = SessionLocal()
    try:
        mat = db.query(RevisionMaterial).get(material_id)
        if mat:
            db.delete(mat)
            db.commit()
            flash("Material deleted!", "success")
        else:
            flash("Material not found.", "danger")
    finally:
        db.close()
    return redirect(url_for("teacher_dashboard"))



# -----------------------
# Manage teachers (admin)
# -----------------------
@app.route("/admin/manage_teachers")
@role_required("admin")
def manage_teachers():
    db = SessionLocal()
    try:
        teachers = db.query(Teacher).all()
        return render_template("admin/admin_manage_teachers.html", teachers=teachers)
    finally:
        db.close()

@app.route("/admin/approve_teacher/<int:teacher_id>")
@role_required("admin")
def approve_teacher(teacher_id):
    db = SessionLocal()
    try:
        teacher = db.query(Teacher).filter_by(id=teacher_id).first()
        if not teacher:
            flash("Teacher not found.", "danger")
            return redirect(url_for("manage_teachers"))

        teacher.is_approved = True
        db.commit()
        flash(f"{teacher.teacher_name} has been approved!", "success")
    finally:
        db.close()
    return redirect(url_for("manage_teachers"))

@app.route("/admin/block_teacher/<int:teacher_id>")
@role_required("admin")
def block_teacher(teacher_id):
    db = SessionLocal()
    try:
        teacher = db.query(Teacher).filter_by(id=teacher_id).first()
        if not teacher:
            flash("Teacher not found.", "danger")
            return redirect(url_for("manage_teachers"))

        teacher.is_approved = False
        db.commit()
        flash(f"{teacher.teacher_name} has been blocked.", "warning")
    finally:
        db.close()
    return redirect(url_for("manage_teachers"))


# -----------------------
# Run
# -----------------------
if __name__ == "__main__":
    app.run(debug=True)