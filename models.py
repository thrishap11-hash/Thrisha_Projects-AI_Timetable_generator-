from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

# User Types
class UserType:
    STUDENT = 'student'
    TEACHER = 'teacher'
    ADMIN = 'admin'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=True)
    password_hash = db.Column(db.String(255), nullable=False)
    user_type = db.Column(db.String(20), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    register_number = db.Column(db.String(50), unique=True, nullable=True)  # For students
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    student_class = db.relationship('StudentClass', backref='student', lazy=True, uselist=False)
    teacher_classes = db.relationship('TeacherClass', backref='teacher', lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Class(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    class_name = db.Column(db.String(100), unique=True, nullable=False)  # e.g., "BCA-1st"
    course = db.Column(db.String(50), nullable=False)  # BCA, BSc CS, BSc IT, MCA, MSc IT
    year = db.Column(db.String(20), nullable=False)  # 1st, 2nd, 3rd
    description = db.Column(db.Text, nullable=True)
    
    # Relationships
    students = db.relationship('StudentClass', backref='class_info', lazy=True)
    teachers = db.relationship('TeacherClass', backref='class_info', lazy=True)
    timetables = db.relationship('Timetable', backref='class_info', lazy=True)

class StudentClass(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey('class.id'), nullable=False)

class TeacherClass(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey('class.id'), nullable=False)
    subject = db.Column(db.String(100), nullable=True)

class Timetable(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    class_id = db.Column(db.Integer, db.ForeignKey('class.id'), nullable=False)
    day = db.Column(db.String(20), nullable=False)  # Monday, Tuesday, etc.
    time_slot = db.Column(db.String(50), nullable=False)  # e.g., "09:00-10:00"
    subject = db.Column(db.String(100), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    room = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    event_date = db.Column(db.Date, nullable=False)
    event_time = db.Column(db.Time, nullable=True)
    class_id = db.Column(db.Integer, db.ForeignKey('class.id'), nullable=True)  # None for all classes
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    creator = db.relationship('User', backref='created_events')
    hall_bookings = db.relationship('HallBooking', backref='event', lazy=True)

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey('class.id'), nullable=True)  # None for all classes
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)
    notification_type = db.Column(db.String(50), default='general')  # general, assignment, timetable_change, substitute, rescheduled, cancelled, department_meeting, college_program
    target_audience = db.Column(db.String(20), default='all')  # all, students, teachers
    
    # Relationships
    creator = db.relationship('User', foreign_keys=[created_by], backref='created_notifications')
    class_info = db.relationship('Class', foreign_keys=[class_id], backref='notifications')

class ChatMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    response = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    user = db.relationship('User', backref='chat_messages')

class TeacherAbsence(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    absence_date = db.Column(db.Date, nullable=False)
    reason = db.Column(db.String(200), nullable=True)
    status = db.Column(db.String(20), default='pending')  # pending, resolved, cancelled
    resolution_type = db.Column(db.String(50), nullable=True)  # substitute, rescheduled, cancelled
    substitute_teacher_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    resolved_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    teacher = db.relationship('User', foreign_keys=[teacher_id], backref='absences')
    substitute_teacher = db.relationship('User', foreign_keys=[substitute_teacher_id])
    creator = db.relationship('User', foreign_keys=[created_by], backref='reported_absences')


class Hall(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)

    # Relationships
    bookings = db.relationship('HallBooking', backref='hall', lazy=True)


class HallBooking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    hall_id = db.Column(db.Integer, db.ForeignKey('hall.id'), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    booking_date = db.Column(db.Date, nullable=False)
    # Legacy single time field (kept for compatibility)
    booking_time = db.Column(db.Time, nullable=True)
    # New start and end times for proper slot management
    start_time = db.Column(db.Time, nullable=True)
    end_time = db.Column(db.Time, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Prevent double booking: one hall, date, time can have only one booking
    __table_args__ = (
        db.UniqueConstraint('hall_id', 'booking_date', 'booking_time', name='uq_hall_booking_slot'),
    )


