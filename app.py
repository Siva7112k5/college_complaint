from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
from functools import wraps
import tempfile
# For Vercel serverless environment
import sys
import logging

# Configure logging for Vercel
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-change-this')

# Use /tmp for database on Vercel (writable location)
tmp = tempfile.mkdtemp()
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{tmp}/complaint_system.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# For Vercel - disable file uploads since we can't write to filesystem
# app.config['UPLOAD_FOLDER'] = '/tmp/uploads'  # Uncomment if you need uploads
# os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)

# Database Models
class User(db.Model):
    __tablename__ = 'user'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='student')
    department = db.Column(db.String(50))
    phone = db.Column(db.String(15))
    profile_pic = db.Column(db.String(200), default='default.jpg')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    status = db.Column(db.Boolean, default=True)
    
    # Relationships
    complaints = db.relationship('Complaint', foreign_keys='Complaint.user_id', backref='user', lazy=True)
    assigned_complaints = db.relationship('Complaint', foreign_keys='Complaint.assigned_to', backref='assignee', lazy=True)

class Department(db.Model):
    __tablename__ = 'department'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    hod_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.Boolean, default=True)
    
    # Relationships
    hod = db.relationship('User', foreign_keys=[hod_id])
    complaints = db.relationship('Complaint', backref='department')

class Complaint(db.Model):
    __tablename__ = 'complaint'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    priority = db.Column(db.String(20), default='Medium')
    status = db.Column(db.String(20), default='Pending')
    assigned_to = db.Column(db.Integer, db.ForeignKey('user.id'))
    department_id = db.Column(db.Integer, db.ForeignKey('department.id'))
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    resolved_at = db.Column(db.DateTime)
    attachment = db.Column(db.String(200))
    anonymous = db.Column(db.Boolean, default=False)
    feedback_rating = db.Column(db.Integer)
    feedback_comment = db.Column(db.Text)
    
    # Relationships
    updates = db.relationship('ComplaintUpdate', backref='complaint', cascade='all, delete-orphan')

class ComplaintUpdate(db.Model):
    __tablename__ = 'complaint_update'
    
    id = db.Column(db.Integer, primary_key=True)
    complaint_id = db.Column(db.Integer, db.ForeignKey('complaint.id'), nullable=False)
    updated_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    old_status = db.Column(db.String(20))
    new_status = db.Column(db.String(20))
    remarks = db.Column(db.Text)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    updater = db.relationship('User', foreign_keys=[updated_by])

class Notification(db.Model):
    __tablename__ = 'notification'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    complaint_id = db.Column(db.Integer, db.ForeignKey('complaint.id'))
    message = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(50), default='in-app')
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', foreign_keys=[user_id])
    complaint = db.relationship('Complaint', foreign_keys=[complaint_id])

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
        
        user = User.query.filter(
            (User.username == username) | (User.email == username)
        ).first()
        
        if user and user.password == password and user.status:
            session['user_id'] = user.id
            session['username'] = user.username
            session['full_name'] = user.full_name
            session['role'] = user.role
            
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
        complaints = Complaint.query.filter_by(user_id=user_id).order_by(Complaint.submitted_at.desc()).all()
        stats = {
            'total': len(complaints),
            'pending': sum(1 for c in complaints if c.status == 'Pending'),
            'in_progress': sum(1 for c in complaints if c.status == 'In Progress'),
            'resolved': sum(1 for c in complaints if c.status == 'Resolved')
        }
        return render_template('student/dashboard.html', complaints=complaints, stats=stats)
    
    elif role == 'faculty':
        assigned_complaints = Complaint.query.filter_by(assigned_to=user_id).order_by(Complaint.submitted_at.desc()).all()
        return render_template('faculty/dashboard.html', complaints=assigned_complaints)
    
    return redirect(url_for('login'))

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
    status = "activated" if user.status else "deactivated"
    flash(f'User {user.full_name} has been {status}!', 'success')
    return redirect(url_for('view_user', user_id=user.id))

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
    db.session.commit()
    flash('Profile updated successfully!', 'success')
    return redirect(url_for('profile'))

@app.route('/change-password', methods=['POST'])
@login_required
def change_password():
    current = request.form['current_password']
    new = request.form['new_password']
    confirm = request.form['confirm_password']
    user = User.query.get(session['user_id'])
    
    if user.password != current:
        flash('Current password is incorrect!', 'danger')
    elif new != confirm:
        flash('New passwords do not match!', 'danger')
    elif len(new) < 6:
        flash('Password must be at least 6 characters!', 'danger')
    else:
        user.password = new
        db.session.commit()
        flash('Password changed successfully!', 'success')
    
    return redirect(url_for('profile'))

@app.route('/complaint/new', methods=['GET', 'POST'])
@login_required
def new_complaint():
    if request.method == 'POST':
        complaint = Complaint(
            user_id=session['user_id'],
            title=request.form['title'],
            description=request.form['description'],
            category=request.form['category'],
            priority=request.form.get('priority', 'Medium'),
            anonymous='anonymous' in request.form
        )
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
    
    if session['role'] == 'student' and complaint.user_id != session['user_id']:
        flash('Access denied!', 'danger')
        return redirect(url_for('dashboard'))
    
    updates = ComplaintUpdate.query.filter_by(complaint_id=complaint_id).order_by(ComplaintUpdate.updated_at.desc()).all()
    return render_template('view_complaint.html', complaint=complaint, updates=updates)

@app.route('/my-complaints')
@login_required
def my_complaints():
    complaints = Complaint.query.filter_by(user_id=session['user_id']).order_by(Complaint.submitted_at.desc()).all()
    stats = {
        'total': len(complaints),
        'pending': sum(1 for c in complaints if c.status == 'Pending'),
        'in_progress': sum(1 for c in complaints if c.status == 'In Progress'),
        'resolved': sum(1 for c in complaints if c.status == 'Resolved')
    }
    return render_template('my_complaints.html', complaints=complaints, stats=stats)

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
    
    update = ComplaintUpdate(
        complaint_id=complaint_id,
        updated_by=session['user_id'],
        old_status=old_status,
        new_status=new_status,
        remarks=remarks
    )
    
    db.session.add(update)
    
    notification = Notification(
        user_id=complaint.user_id,
        complaint_id=complaint_id,
        message=f'Your complaint #{complaint_id} status updated to: {new_status}'
    )
    db.session.add(notification)
    db.session.commit()
    
    flash('Complaint updated successfully!', 'success')
    return redirect(url_for('view_complaint', complaint_id=complaint_id))

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out!', 'info')
    return redirect(url_for('index'))

# Initialize database
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
        print("✓ Admin user created!")
    
    # Create departments
    departments = ['Academic', 'Administrative', 'Infrastructure', 'Hostel', 'Library', 'Examination', 'Finance', 'Student Affairs']
    for dept in departments:
        if not Department.query.filter_by(name=dept).first():
            department = Department(name=dept, description=f'{dept} Department')
            db.session.add(department)
    db.session.commit()
    print("✓ Departments created!")

if __name__ == '__main__':
    app.run(debug=True, port=5000)