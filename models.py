from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from datetime import datetime
import os
from functools import wraps
from models import db, User, Department, Complaint, ComplaintUpdate, Notification
from database import init_db

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-this'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///complaint_system.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'

# Initialize database
init_db(app)

# Login decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login first!', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'role' not in session or session['role'] not in roles:
                flash('Access denied!', 'danger')
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Routes
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username, password=password).first()
        
        if user and user.status:
            session['user_id'] = user.id
            session['username'] = user.username
            session['full_name'] = user.full_name
            session['role'] = user.role
            
            # Update last login
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            flash(f'Welcome back, {user.full_name}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password!', 'danger')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        full_name = request.form['full_name']
        role = request.form['role']
        department = request.form.get('department', '')
        phone = request.form.get('phone', '')
        
        # Check if user exists
        if User.query.filter_by(username=username).first():
            flash('Username already exists!', 'danger')
        elif User.query.filter_by(email=email).first():
            flash('Email already exists!', 'danger')
        else:
            user = User(
                username=username,
                password=password,
                email=email,
                full_name=full_name,
                role=role,
                department=department,
                phone=phone
            )
            db.session.add(user)
            db.session.commit()
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/dashboard')
@login_required
def dashboard():
    role = session['role']
    user_id = session['user_id']
    
    if role == 'admin':
        # Admin dashboard
        total_users = User.query.count()
        total_complaints = Complaint.query.count()
        pending_complaints = Complaint.query.filter_by(status='Pending').count()
        in_progress_complaints = Complaint.query.filter_by(status='In Progress').count()
        resolved_complaints = Complaint.query.filter_by(status='Resolved').count()
        
        recent_complaints = Complaint.query.order_by(Complaint.submitted_at.desc()).limit(5).all()
        recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()
        
        return render_template('admin/dashboard.html',
                             total_users=total_users,
                             total_complaints=total_complaints,
                             pending_complaints=pending_complaints,
                             in_progress_complaints=in_progress_complaints,
                             resolved_complaints=resolved_complaints,
                             recent_complaints=recent_complaints,
                             recent_users=recent_users)
    
    elif role == 'student':
        # Student dashboard
        complaints = Complaint.query.filter_by(user_id=user_id).order_by(Complaint.submitted_at.desc()).all()
        stats = {
            'total': len(complaints),
            'pending': sum(1 for c in complaints if c.status == 'Pending'),
            'in_progress': sum(1 for c in complaints if c.status == 'In Progress'),
            'resolved': sum(1 for c in complaints if c.status == 'Resolved')
        }
        return render_template('student/dashboard.html', complaints=complaints, stats=stats)
    
    elif role == 'faculty':
        # Faculty dashboard
        assigned_complaints = Complaint.query.filter_by(assigned_to=user_id).order_by(Complaint.submitted_at.desc()).all()
        return render_template('faculty/dashboard.html', complaints=assigned_complaints)

@app.route('/admin/users')
@login_required
@role_required('admin')
def admin_users():
    users = User.query.all()
    return render_template('admin/users.html', users=users)

@app.route('/admin/complaints')
@login_required
@role_required('admin')
def admin_complaints():
    complaints = Complaint.query.all()
    return render_template('admin/complaints.html', complaints=complaints)

@app.route('/admin/user/<int:user_id>')
@login_required
@role_required('admin')
def view_user(user_id):
    user = User.query.get_or_404(user_id)
    complaints = Complaint.query.filter_by(user_id=user_id).all()
    return render_template('admin/view_user.html', user=user, complaints=complaints)

@app.route('/admin/user/<int:user_id>/toggle-status')
@login_required
@role_required('admin')
def toggle_user_status(user_id):
    user = User.query.get_or_404(user_id)
    user.status = not user.status
    db.session.commit()
    flash(f'User status updated!', 'success')
    return redirect(url_for('admin_users'))

@app.route('/complaint/new', methods=['GET', 'POST'])
@login_required
def new_complaint():
    if request.method == 'POST':
        # Auto-categorize based on keywords
        title = request.form['title']
        description = request.form['description']
        
        # Simple auto-categorization
        text = (title + ' ' + description).lower()
        categories = {
            'academic': ['teacher', 'faculty', 'class', 'exam', 'study', 'course', 'subject'],
            'fee': ['fee', 'payment', 'money', 'scholarship', 'finance'],
            'infrastructure': ['building', 'room', 'lab', 'fan', 'light', 'ac', 'bench'],
            'hostel': ['hostel', 'mess', 'food', 'room', 'warden'],
            'library': ['library', 'book', 'journal', 'reading']
        }
        
        category = 'Other'
        for cat, keywords in categories.items():
            if any(keyword in text for keyword in keywords):
                category = cat.capitalize()
                break
        
        # Calculate priority
        priority = 'Medium'
        urgent_words = ['urgent', 'immediate', 'emergency', 'critical', 'serious']
        if any(word in text for word in urgent_words):
            priority = 'High'
        
        complaint = Complaint(
            user_id=session['user_id'],
            title=title,
            description=description,
            category=category,
            priority=priority,
            anonymous='anonymous' in request.form
        )
        
        # Handle file upload
        if 'attachment' in request.files:
            file = request.files['attachment']
            if file.filename:
                filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                complaint.attachment = filename
        
        db.session.add(complaint)
        db.session.commit()
        
        # Create notification for admins
        admins = User.query.filter_by(role='admin').all()
        for admin in admins:
            notification = Notification(
                user_id=admin.id,
                complaint_id=complaint.id,
                message=f'New complaint #{complaint.id} submitted by {session["full_name"]}'
            )
            db.session.add(notification)
        db.session.commit()
        
        flash('Complaint submitted successfully!', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('new_complaint.html')

@app.route('/complaint/<int:complaint_id>')
@login_required
def view_complaint(complaint_id):
    complaint = Complaint.query.get_or_404(complaint_id)
    
    # Check permission
    if session['role'] == 'student' and complaint.user_id != session['user_id']:
        flash('Access denied!', 'danger')
        return redirect(url_for('dashboard'))
    
    updates = ComplaintUpdate.query.filter_by(complaint_id=complaint_id).order_by(ComplaintUpdate.updated_at.desc()).all()
    return render_template('view_complaint.html', complaint=complaint, updates=updates)

@app.route('/complaint/<int:complaint_id>/update', methods=['POST'])
@login_required
@role_required('admin', 'faculty')
def update_complaint(complaint_id):
    complaint = Complaint.query.get_or_404(complaint_id)
    old_status = complaint.status
    new_status = request.form['status']
    remarks = request.form['remarks']
    
    complaint.status = new_status
    complaint.last_updated = datetime.utcnow()
    
    if new_status == 'Resolved':
        complaint.resolved_at = datetime.utcnow()
    
    db.session.commit()
    
    # Log update
    update = ComplaintUpdate(
        complaint_id=complaint_id,
        updated_by=session['user_id'],
        old_status=old_status,
        new_status=new_status,
        remarks=remarks
    )
    db.session.add(update)
    
    # Notify user
    notification = Notification(
        user_id=complaint.user_id,
        complaint_id=complaint_id,
        message=f'Your complaint #{complaint_id} status updated to: {new_status}'
    )
    db.session.add(notification)
    db.session.commit()
    
    flash('Complaint updated successfully!', 'success')
    return redirect(url_for('view_complaint', complaint_id=complaint_id))

@app.route('/complaint/<int:complaint_id>/feedback', methods=['POST'])
@login_required
def submit_feedback(complaint_id):
    complaint = Complaint.query.get_or_404(complaint_id)
    
    if complaint.user_id != session['user_id']:
        flash('Access denied!', 'danger')
        return redirect(url_for('dashboard'))
    
    complaint.feedback_rating = request.form['rating']
    complaint.feedback_comment = request.form['comment']
    db.session.commit()
    
    flash('Thank you for your feedback!', 'success')
    return redirect(url_for('view_complaint', complaint_id=complaint_id))

@app.route('/profile')
@login_required
def profile():
    user = User.query.get(session['user_id'])
    return render_template('profile.html', user=user)

@app.route('/profile/update', methods=['POST'])
@login_required
def update_profile():
    user = User.query.get(session['user_id'])
    user.full_name = request.form['full_name']
    user.email = request.form['email']
    user.phone = request.form['phone']
    user.department = request.form['department']
    
    if 'profile_pic' in request.files:
        file = request.files['profile_pic']
        if file.filename:
            filename = f"user_{user.id}_{file.filename}"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            user.profile_pic = filename
    
    db.session.commit()
    flash('Profile updated successfully!', 'success')
    return redirect(url_for('profile'))

@app.route('/notifications')
@login_required
def notifications():
    notifs = Notification.query.filter_by(user_id=session['user_id']).order_by(Notification.created_at.desc()).all()
    
    # Mark as read
    for notif in notifs:
        notif.is_read = True
    db.session.commit()
    
    return render_template('notifications.html', notifications=notifs)

@app.route('/api/notifications/count')
@login_required
def notification_count():
    count = Notification.query.filter_by(user_id=session['user_id'], is_read=False).count()
    return jsonify({'count': count})

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out!', 'info')
    return redirect(url_for('index'))

# Create upload folder
os.makedirs('static/uploads', exist_ok=True)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        
        # Create admin if not exists
        if not User.query.filter_by(username='admin').first():
            admin = User(
                username='admin',
                password='admin123',
                email='admin@college.edu',
                full_name='System Administrator',
                role='admin',
                status=True
            )
            db.session.add(admin)
            db.session.commit()
            print("Admin user created!")
        
        # Create departments
        departments = ['Academic', 'Administrative', 'Infrastructure', 'Hostel', 'Library', 'Examination', 'Finance', 'Student Affairs']
        for dept in departments:
            if not Department.query.filter_by(name=dept).first():
                department = Department(name=dept, description=f'{dept} Department')
                db.session.add(department)
        db.session.commit()
    
    app.run(debug=True, port=5000)