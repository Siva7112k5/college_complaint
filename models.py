from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

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
    complaints = db.relationship('Complaint', foreign_keys='Complaint.user_id', back_populates='user')
    assigned_complaints = db.relationship('Complaint', foreign_keys='Complaint.assigned_to', back_populates='assignee')

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
    complaints = db.relationship('Complaint', back_populates='department')

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
    escalation_level = db.Column(db.Integer, default=0)
    feedback_rating = db.Column(db.Integer)
    feedback_comment = db.Column(db.Text)
    
    # Relationships
    user = db.relationship('User', foreign_keys=[user_id], back_populates='complaints')
    assignee = db.relationship('User', foreign_keys=[assigned_to], back_populates='assigned_complaints')
    department = db.relationship('Department', back_populates='complaints')
    updates = db.relationship('ComplaintUpdate', back_populates='complaint', cascade='all, delete-orphan')

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
    complaint = db.relationship('Complaint', back_populates='updates')
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