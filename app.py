from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, Class, Timetable, Event, Notification, ChatMessage, StudentClass, TeacherClass, UserType, TeacherAbsence, Hall, HallBooking
from datetime import datetime, date, time
from sqlalchemy import inspect, text
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///education_system.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Initialize database
with app.app_context():
    db.create_all()

    # Lightweight migration for hall_booking table: ensure start_time and end_time columns exist
    inspector = inspect(db.engine)
    tables = inspector.get_table_names()
    if 'hall_booking' in tables:
        columns = [col['name'] for col in inspector.get_columns('hall_booking')]
        if 'start_time' not in columns:
            db.session.execute(text('ALTER TABLE hall_booking ADD COLUMN start_time TIME'))
        if 'end_time' not in columns:
            db.session.execute(text('ALTER TABLE hall_booking ADD COLUMN end_time TIME'))
        db.session.commit()

    # Create default admin if not exists
    if not User.query.filter_by(username='admin').first():
        admin = User(
            username='admin',
            email='admin@college.edu',
            user_type=UserType.ADMIN,
            full_name='System Administrator'
        )
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()

    # Create default halls if they don't exist
    default_halls = [
        'Kailash Hall',
        'RD Hall',
        'AV Hall',
        'Charles Babbage Hall'
    ]
    for hall_name in default_halls:
        if not Hall.query.filter_by(name=hall_name).first():
            hall = Hall(name=hall_name)
            db.session.add(hall)
    db.session.commit()

# Routes
@app.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.user_type == UserType.STUDENT:
            return redirect(url_for('student_dashboard'))
        elif current_user.user_type == UserType.TEACHER:
            return redirect(url_for('teacher_dashboard'))
        elif current_user.user_type == UserType.ADMIN:
            return redirect(url_for('admin_dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user_type = request.form.get('user_type', 'student')
        
        if user_type == 'student':
            # For students, username is register number
            user = User.query.filter_by(register_number=username, user_type=UserType.STUDENT).first()
        else:
            user = User.query.filter_by(username=username, user_type=user_type).first()
        
        if user and user.check_password(password):
            login_user(user)
            flash('Login successful!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid credentials. Please try again.', 'error')
    
    return render_template('auth/login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

# Student Routes
@app.route('/student/dashboard')
@login_required
def student_dashboard():
    if current_user.user_type != UserType.STUDENT:
        flash('Access denied.', 'error')
        return redirect(url_for('index'))
    
    # Get student's class
    student_class = StudentClass.query.filter_by(student_id=current_user.id).first()
    class_info = student_class.class_info if student_class else None
    
    # Get timetable
    timetable = []
    if class_info:
        timetable = Timetable.query.filter_by(class_id=class_info.id).order_by(
            Timetable.day, Timetable.time_slot
        ).all()
    
    # Get events
    events = Event.query.filter(
        (Event.class_id == class_info.id) if class_info else (Event.class_id.is_(None))
    ).order_by(Event.event_date.desc()).limit(10).all()
    
    # Get notifications for students (all, students, or class-specific)
    if class_info:
        notifications = Notification.query.filter(
            (Notification.target_audience.in_(['all', 'students'])) &
            ((Notification.class_id == class_info.id) | (Notification.class_id.is_(None)))
        ).order_by(Notification.created_at.desc()).limit(10).all()
    else:
        notifications = Notification.query.filter(
            Notification.target_audience.in_(['all', 'students'])
        ).order_by(Notification.created_at.desc()).limit(10).all()
    
    # Get today's day name
    today_day = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'][datetime.now().weekday()]
    
    return render_template('student/dashboard.html', 
                         class_info=class_info, 
                         timetable=timetable,
                         events=events,
                         notifications=notifications,
                         today_day=today_day)

@app.route('/student/timetable')
@login_required
def student_timetable():
    if current_user.user_type != UserType.STUDENT:
        return redirect(url_for('index'))
    
    student_class = StudentClass.query.filter_by(student_id=current_user.id).first()
    if not student_class:
        flash('No class assigned.', 'error')
        return redirect(url_for('student_dashboard'))
    
    timetable = Timetable.query.filter_by(class_id=student_class.class_id).order_by(
        Timetable.day, Timetable.time_slot
    ).all()
    
    # Get recent timetable-related notifications
    # Handle case where notification_type column might not exist yet
    try:
        timetable_notifications = Notification.query.filter(
            (Notification.class_id == student_class.class_id) | (Notification.class_id.is_(None)),
            Notification.notification_type.in_(['substitute', 'rescheduled', 'cancelled', 'timetable_change'])
        ).order_by(Notification.created_at.desc()).limit(5).all()
    except Exception:
        # Fallback if notification_type column doesn't exist
        timetable_notifications = []
    
    # Organize by day
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
    timetable_by_day = {day: [] for day in days}
    
    for entry in timetable:
        if entry.day in timetable_by_day:
            timetable_by_day[entry.day].append(entry)
    
    return render_template('student/timetable.html', 
                         timetable_by_day=timetable_by_day, 
                         class_info=student_class.class_info,
                         timetable_notifications=timetable_notifications)

@app.route('/student/events')
@login_required
def student_events():
    if current_user.user_type != UserType.STUDENT:
        return redirect(url_for('index'))
    
    student_class = StudentClass.query.filter_by(student_id=current_user.id).first()
    class_id = student_class.class_id if student_class else None
    
    events = Event.query.filter(
        (Event.class_id == class_id) | (Event.class_id.is_(None))
    ).order_by(Event.event_date.desc()).all()
    
    return render_template('student/events.html', events=events)

@app.route('/student/notifications')
@login_required
def student_notifications():
    if current_user.user_type != UserType.STUDENT:
        return redirect(url_for('index'))
    
    student_class = StudentClass.query.filter_by(student_id=current_user.id).first()
    class_id = student_class.class_id if student_class else None
    
    # Get notifications for students (all, students, or class-specific)
    if class_id:
        notifications = Notification.query.filter(
            (Notification.target_audience.in_(['all', 'students'])) &
            ((Notification.class_id == class_id) | (Notification.class_id.is_(None)))
        ).order_by(Notification.created_at.desc()).all()
    else:
        notifications = Notification.query.filter(
            Notification.target_audience.in_(['all', 'students'])
        ).order_by(Notification.created_at.desc()).all()
    
    return render_template('student/notifications.html', notifications=notifications)

@app.route('/student/chatbot')
@login_required
def student_chatbot():
    if current_user.user_type != UserType.STUDENT:
        return redirect(url_for('index'))
    
    # Get chat history
    chat_history = ChatMessage.query.filter_by(user_id=current_user.id).order_by(
        ChatMessage.created_at.desc()
    ).limit(50).all()
    
    return render_template('student/chatbot.html', chat_history=reversed(chat_history))

@app.route('/api/chatbot', methods=['POST'])
@login_required
def chatbot_api():
    if current_user.user_type != UserType.STUDENT:
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.json
    user_message = data.get('message', '')
    
    # Simple AI chatbot logic (can be enhanced with actual AI)
    response = generate_chatbot_response(user_message)
    
    # Save to database
    chat_message = ChatMessage(
        user_id=current_user.id,
        message=user_message,
        response=response
    )
    db.session.add(chat_message)
    db.session.commit()
    
    return jsonify({'response': response})

def generate_chatbot_response(message):
    """Simple rule-based chatbot (can be replaced with actual AI)"""
    message_lower = message.lower()
    
    if any(word in message_lower for word in ['timetable', 'schedule', 'class time']):
        return "You can view your timetable in the Timetable section. It shows all your classes for the week."
    elif any(word in message_lower for word in ['event', 'upcoming']):
        return "Check the Events section to see all upcoming events and important dates."
    elif any(word in message_lower for word in ['notification', 'announcement']):
        return "All notifications are displayed in the Notifications section. Make sure to check regularly!"
    elif any(word in message_lower for word in ['hello', 'hi', 'hey']):
        return "Hello! How can I help you today? I can assist with timetable, events, notifications, and general queries."
    elif any(word in message_lower for word in ['exam', 'test', 'assignment']):
        return "For exam and assignment details, please check the Notifications section or contact your teachers."
    elif any(word in message_lower for word in ['help']):
        return "I'm here to help! You can ask me about: timetable, events, notifications, exams, assignments, or any general questions about your classes."
    else:
        return "I understand your query. For specific information, please check the relevant sections: Timetable, Events, or Notifications. If you need more help, contact your class coordinator."

# Teacher Routes
@app.route('/teacher/dashboard')
@login_required
def teacher_dashboard():
    if current_user.user_type != UserType.TEACHER:
        flash('Access denied.', 'error')
        return redirect(url_for('index'))
    
    # Get teacher's classes
    teacher_classes = TeacherClass.query.filter_by(teacher_id=current_user.id).all()
    classes = [tc.class_info for tc in teacher_classes]
    
    # Get upcoming events
    events = Event.query.order_by(Event.event_date.desc()).limit(5).all()
    
    # Get notifications for teachers (all or teachers only)
    notifications = Notification.query.filter(
        Notification.target_audience.in_(['all', 'teachers'])
    ).order_by(Notification.created_at.desc()).limit(5).all()
    
    # Get assignments created by this teacher
    teacher_assignments = Notification.query.filter_by(
        created_by=current_user.id,
        notification_type='assignment'
    ).order_by(Notification.created_at.desc()).limit(5).all()
    
    return render_template('teacher/dashboard.html', 
                         classes=classes, 
                         events=events, 
                         notifications=notifications,
                         teacher_assignments=teacher_assignments)

@app.route('/teacher/classes')
@login_required
def teacher_classes():
    if current_user.user_type != UserType.TEACHER:
        return redirect(url_for('index'))
    
    teacher_classes = TeacherClass.query.filter_by(teacher_id=current_user.id).all()
    
    return render_template('teacher/classes.html', teacher_classes=teacher_classes)

@app.route('/teacher/assignments/add', methods=['POST'])
@login_required
def teacher_add_assignment():
    """Allow teachers to create assignment notifications for their classes"""
    if current_user.user_type != UserType.TEACHER:
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.json
    class_id = data.get('class_id')
    title = data.get('title', '').strip()
    message = data.get('message', '').strip()
    
    if not title or not message:
        return jsonify({'error': 'Title and message are required'}), 400
    
    if not class_id:
        return jsonify({'error': 'Class selection is required'}), 400
    
    # Verify teacher is assigned to this class
    teacher_class = TeacherClass.query.filter_by(
        teacher_id=current_user.id,
        class_id=class_id
    ).first()
    
    if not teacher_class:
        return jsonify({'error': 'You are not assigned to this class'}), 403
    
    # Create notification as assignment for students
    notification = Notification(
        title=title,
        message=message,
        class_id=class_id,
        created_by=current_user.id,
        notification_type='assignment',  # New notification type for assignments
        target_audience='students'  # Only students see assignments
    )
    db.session.add(notification)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Assignment created successfully! Students in the class will be notified.'
    })

# Admin Routes
@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if current_user.user_type != UserType.ADMIN:
        flash('Access denied.', 'error')
        return redirect(url_for('index'))
    
    stats = {
        'total_students': User.query.filter_by(user_type=UserType.STUDENT).count(),
        'total_teachers': User.query.filter_by(user_type=UserType.TEACHER).count(),
        'total_classes': Class.query.count(),
        'total_events': Event.query.count()
    }
    
    recent_events = Event.query.order_by(Event.created_at.desc()).limit(5).all()
    recent_notifications = Notification.query.order_by(Notification.created_at.desc()).limit(5).all()
    
    return render_template('admin/dashboard.html', stats=stats, recent_events=recent_events, recent_notifications=recent_notifications)

@app.route('/admin/classes')
@login_required
def admin_classes():
    if current_user.user_type != UserType.ADMIN:
        return redirect(url_for('index'))
    
    classes = Class.query.all()
    return render_template('admin/classes.html', classes=classes)

@app.route('/admin/timetable/<int:class_id>')
@login_required
def admin_timetable(class_id):
    if current_user.user_type != UserType.ADMIN:
        return redirect(url_for('index'))
    
    class_info = Class.query.get_or_404(class_id)
    timetable = Timetable.query.filter_by(class_id=class_id).order_by(
        Timetable.day, Timetable.time_slot
    ).all()
    
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
    timetable_by_day = {day: [] for day in days}
    
    for entry in timetable:
        if entry.day in timetable_by_day:
            timetable_by_day[entry.day].append(entry)
    
    teachers = User.query.filter_by(user_type=UserType.TEACHER).all()
    
    return render_template('admin/timetable.html', 
                         class_info=class_info, 
                         timetable_by_day=timetable_by_day,
                         teachers=teachers)

@app.route('/admin/timetable/add', methods=['POST'])
@login_required
def add_timetable_entry():
    if current_user.user_type != UserType.ADMIN:
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.json
    timetable = Timetable(
        class_id=data['class_id'],
        day=data['day'],
        time_slot=data['time_slot'],
        subject=data['subject'],
        teacher_id=data.get('teacher_id'),
        room=data.get('room')
    )
    db.session.add(timetable)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Timetable entry added successfully'})

@app.route('/admin/timetable/delete/<int:timetable_id>', methods=['POST'])
@login_required
def delete_timetable_entry(timetable_id):
    if current_user.user_type != UserType.ADMIN:
        return jsonify({'error': 'Unauthorized'}), 403
    
    timetable = Timetable.query.get_or_404(timetable_id)
    db.session.delete(timetable)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Timetable entry deleted successfully'})

@app.route('/admin/timetable/generate', methods=['POST'])
@login_required
def generate_timetable():
    """AI-powered automatic timetable generator"""
    if current_user.user_type != UserType.ADMIN:
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.json
    class_id = data.get('class_id')
    start_time = data.get('start_time', '09:00')  # Default 9:00 AM
    end_time = data.get('end_time', '15:30')  # Default 3:30 PM
    subjects_input = data.get('subjects', '')  # Comma-separated subjects
    class_duration = int(data.get('class_duration', 60))  # Default 60 minutes
    
    if not class_id:
        return jsonify({'error': 'Class ID is required'}), 400
    
    class_info = Class.query.get_or_404(class_id)
    
    # Parse subjects
    if subjects_input:
        subjects_list = [s.strip() for s in subjects_input.split(',') if s.strip()]
    else:
        # Default subjects based on course
        default_subjects = {
            'BCA': ['Mathematics', 'Programming', 'Database Systems', 'Web Development', 'Data Structures', 'Computer Networks'],
            'BSc Computer Science': ['Mathematics', 'Programming', 'Database Systems', 'Web Development', 'Data Structures', 'Operating Systems'],
            'BSc IT': ['Mathematics', 'Programming', 'Database Systems', 'Web Development', 'Information Systems', 'Networking'],
            'MCA': ['Advanced Programming', 'Software Engineering', 'Machine Learning', 'Cloud Computing', 'Project Management'],
            'MSc IT': ['Advanced Database', 'Web Technologies', 'Data Analytics', 'Information Security', 'Research Methodology']
        }
        course_key = class_info.course.split()[0] if class_info.course else 'BCA'
        subjects_list = default_subjects.get(course_key, ['Mathematics', 'Programming', 'Database Systems', 'Web Development'])
    
    # Get available teachers for this class
    teacher_classes = TeacherClass.query.filter_by(class_id=class_id).all()
    teachers = [tc.teacher for tc in teacher_classes] if teacher_classes else []
    
    # Parse time
    def time_to_minutes(time_str):
        h, m = map(int, time_str.split(':'))
        return h * 60 + m
    
    def minutes_to_time(minutes):
        h = minutes // 60
        m = minutes % 60
        return f"{h:02d}:{m:02d}"
    
    start_minutes = time_to_minutes(start_time)
    end_minutes = time_to_minutes(end_time)
    
    # Calculate number of slots per day
    total_minutes = end_minutes - start_minutes
    slots_per_day = total_minutes // class_duration
    
    # Days of the week
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
    
    # Delete existing timetable for this class
    Timetable.query.filter_by(class_id=class_id).delete()
    db.session.commit()
    
    # Generate timetable intelligently
    generated_entries = []
    subject_index = 0
    room_counter = 1
    
    for day in days:
        current_time = start_minutes
        day_subjects = []
        
        # Distribute subjects across the day
        for slot in range(slots_per_day):
            if current_time + class_duration > end_minutes:
                break
            
            # Select subject (round-robin)
            subject = subjects_list[subject_index % len(subjects_list)]
            subject_index += 1
            
            # Avoid same subject twice in a row on same day
            if day_subjects and day_subjects[-1] == subject and len(subjects_list) > 1:
                subject_index += 1
                subject = subjects_list[subject_index % len(subjects_list)]
            
            day_subjects.append(subject)
            
            # Assign teacher if available
            teacher_id = None
            if teachers:
                # Try to match teacher with subject
                for tc in teacher_classes:
                    if tc.subject and tc.subject.lower() in subject.lower():
                        teacher_id = tc.teacher_id
                        break
                # If no match, assign any teacher
                if not teacher_id:
                    teacher_id = teachers[slot % len(teachers)].id
            
            # Generate time slot
            slot_start = minutes_to_time(current_time)
            slot_end = minutes_to_time(current_time + class_duration)
            time_slot = f"{slot_start}-{slot_end}"
            
            # Generate room
            room = f"Room-{101 + (room_counter % 10)}"
            if 'Lab' in subject or 'Programming' in subject or 'Web' in subject:
                room = f"Lab-{201 + (room_counter % 5)}"
            
            # Create timetable entry
            timetable_entry = Timetable(
                class_id=class_id,
                day=day,
                time_slot=time_slot,
                subject=subject,
                teacher_id=teacher_id,
                room=room
            )
            db.session.add(timetable_entry)
            generated_entries.append({
                'day': day,
                'time_slot': time_slot,
                'subject': subject,
                'room': room
            })
            
            current_time += class_duration
            room_counter += 1
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f'Timetable generated successfully! Created {len(generated_entries)} entries.',
        'entries_count': len(generated_entries),
        'entries': generated_entries
    })

@app.route('/admin/timetable/clear/<int:class_id>', methods=['POST'])
@login_required
def clear_timetable(class_id):
    """Clear all timetable entries for a class"""
    if current_user.user_type != UserType.ADMIN:
        return jsonify({'error': 'Unauthorized'}), 403
    
    count = Timetable.query.filter_by(class_id=class_id).delete()
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f'Cleared {count} timetable entries successfully.'
    })

@app.route('/admin/events')
@login_required
def admin_events():
    if current_user.user_type != UserType.ADMIN:
        return redirect(url_for('index'))
    
    events = Event.query.order_by(Event.event_date.desc()).all()
    classes = Class.query.all()
    halls = Hall.query.order_by(Hall.name).all()
    
    return render_template('admin/events.html', events=events, classes=classes, halls=halls)


def is_hall_available(hall_id, event_date, start_time, end_time):
    """
    Check if a hall is free for the given date and time range.
    We consider the interval [start_time, end_time).
    Any overlap with existing bookings on that date makes it unavailable.
    """
    if not hall_id or not event_date or not start_time or not end_time:
        # If any of these are missing, treat as not using hall-based allocation
        return True

    # Fetch all bookings for this hall and date and check for time overlap
    existing_bookings = HallBooking.query.filter_by(
        hall_id=hall_id,
        booking_date=event_date
    ).all()

    for b in existing_bookings:
        # Support legacy rows that may only have booking_time
        existing_start = b.start_time or b.booking_time
        existing_end = b.end_time or b.booking_time

        if not existing_start or not existing_end:
            continue

        # Overlap check for [start_time, end_time) vs [existing_start, existing_end)
        if start_time < existing_end and end_time > existing_start:
            return False

    return True


def find_available_hall(event_date, start_time, end_time):
    """Return the first free hall for the given date and time range, or None."""
    if not event_date or not start_time or not end_time:
        return None

    halls = Hall.query.order_by(Hall.name).all()
    for hall in halls:
        if is_hall_available(hall.id, event_date, start_time, end_time):
            return hall
    return None

@app.route('/admin/events/add', methods=['POST'])
@login_required
def add_event():
    if current_user.user_type != UserType.ADMIN:
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.json

    event_date = datetime.strptime(data['event_date'], '%Y-%m-%d').date()
    # Start and end times for the event
    event_start_time = datetime.strptime(data['event_time'], '%H:%M').time() if data.get('event_time') else None
    event_end_time = datetime.strptime(data['event_end_time'], '%H:%M').time() if data.get('event_end_time') else None
    hall_id_raw = data.get('hall_id')
    hall_id = int(hall_id_raw) if hall_id_raw else None

    # If a hall is selected but start or end time is missing, do not allow booking
    if hall_id and (not event_start_time or not event_end_time):
        return jsonify({
            'success': False,
            'message': 'Please select both start time and end time to book the hall.'
        }), 400

    # If both times provided, ensure end is after start
    if event_start_time and event_end_time and event_end_time <= event_start_time:
        return jsonify({
            'success': False,
            'message': 'End time must be after start time.'
        }), 400

    # If admin selected a specific hall and time, enforce no double booking for that hall
    if hall_id and event_start_time and event_end_time:
        # Check for overlapping bookings
        existing_bookings = HallBooking.query.filter_by(
            hall_id=hall_id,
            booking_date=event_date
        ).all()
        for existing in existing_bookings:
            existing_start = existing.start_time or existing.booking_time
            existing_end = existing.end_time or existing.booking_time
            if not existing_start or not existing_end:
                continue

            if event_start_time < existing_end and event_end_time > existing_start:
                # Build detailed message with previous booking info
                existing_event = existing.event
                existing_hall = existing.hall
                msg_lines = [
                    'Hall Already Booked!',
                    f'Hall: {existing_hall.name}',
                    f'Booked For: {existing_event.title}',
                    f'Date: {existing.booking_date.strftime("%d-%m-%Y")}',
                    f'Time: {existing_start.strftime("%I:%M %p")} - {existing_end.strftime("%I:%M %p")}',
                    '',
                    'You have not registered this hall because it is already booked in this time range.'
                ]
                return jsonify({
                    'success': False,
                    'message': '\n'.join(msg_lines)
                }), 400

    # If no hall selected but times are given, try to auto-allocate any free hall
    if not hall_id and event_start_time and event_end_time:
        free_hall = find_available_hall(event_date, event_start_time, event_end_time)
        if free_hall is None:
            return jsonify({
                'success': False,
                'message': 'No Halls Available!\nAll halls are already booked for the selected date and time.\nPlease choose a different time.'
            }), 400
        hall_id = free_hall.id

    event = Event(
        title=data['title'],
        description=data.get('description', ''),
        event_date=event_date,
        event_time=event_start_time,
        class_id=data.get('class_id') if data.get('class_id') else None,
        created_by=current_user.id
    )
    db.session.add(event)
    db.session.flush()  # Get event.id before creating booking

    # Create hall booking record if hall and times are provided
    if hall_id and event_start_time and event_end_time:
        booking = HallBooking(
            hall_id=hall_id,
            event_id=event.id,
            booking_date=event_date,
            booking_time=event_start_time,  # keep legacy field as start time
            start_time=event_start_time,
            end_time=event_end_time
        )
        db.session.add(booking)

    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Booking Successful!\nThe hall has been successfully reserved for your event.'
    })


@app.route('/admin/halls/<int:hall_id>/bookings')
@login_required
def get_hall_bookings(hall_id):
    """Return all bookings for a specific hall (for admin view)."""
    if current_user.user_type != UserType.ADMIN:
        return jsonify({'error': 'Unauthorized'}), 403

    hall = Hall.query.get_or_404(hall_id)
    bookings = HallBooking.query.filter_by(hall_id=hall_id).order_by(
        HallBooking.booking_date, HallBooking.start_time
    ).all()

    result = []
    for b in bookings:
        start_t = b.start_time or b.booking_time
        end_t = b.end_time or b.booking_time
        result.append({
            'event_title': b.event.title if b.event else '',
            'date': b.booking_date.strftime('%d-%m-%Y'),
            'start_time': start_t.strftime('%I:%M %p') if start_t else '',
            'end_time': end_t.strftime('%I:%M %p') if end_t else ''
        })

    return jsonify({
        'hall_id': hall.id,
        'hall_name': hall.name,
        'bookings': result
    })

@app.route('/admin/notifications')
@login_required
def admin_notifications():
    if current_user.user_type != UserType.ADMIN:
        return redirect(url_for('index'))
    
    notifications = Notification.query.order_by(Notification.created_at.desc()).all()
    classes = Class.query.all()
    
    return render_template('admin/notifications.html', notifications=notifications, classes=classes)

@app.route('/admin/notifications/add', methods=['POST'])
@login_required
def add_notification():
    if current_user.user_type != UserType.ADMIN:
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.json
    notification = Notification(
        title=data['title'],
        message=data['message'],
        class_id=data.get('class_id') if data.get('class_id') else None,
        created_by=current_user.id,
        notification_type=data.get('notification_type', 'general'),
        target_audience=data.get('target_audience', 'all')
    )
    db.session.add(notification)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Notification added successfully'})

@app.route('/admin/users')
@login_required
def admin_users():
    if current_user.user_type != UserType.ADMIN:
        return redirect(url_for('index'))
    
    students = User.query.filter_by(user_type=UserType.STUDENT).all()
    teachers = User.query.filter_by(user_type=UserType.TEACHER).all()
    classes = Class.query.all()
    
    return render_template('admin/users.html', students=students, teachers=teachers, classes=classes)

@app.route('/admin/users/generate-register-number/<int:class_id>', methods=['GET'])
@login_required
def get_next_register_number(class_id):
    """Get the next available register number for a class"""
    if current_user.user_type != UserType.ADMIN:
        return jsonify({'error': 'Unauthorized'}), 403
    
    register_number = generate_student_register_number(class_id)
    if register_number:
        return jsonify({'success': True, 'register_number': register_number})
    else:
        return jsonify({'error': 'Invalid class'}), 400

def generate_student_register_number(class_id):
    """Generate a unique student register number based on class and year
    
    Format: {course_code}{year_code}{student_number}
    Examples:
    - BCA 1st year: bca25001, bca25002, ..., bca25010
    - BCA 2nd year: bca24001, bca24002, ..., bca24010
    - BCA 3rd year: bca23001, bca23002, ..., bca23010
    """
    class_info = Class.query.get(class_id)
    if not class_info:
        return None
    
    # Map year to year code (batch year)
    # 1st year = 25, 2nd year = 24, 3rd year = 23
    year_code_map = {
        '1st': '25',
        '2nd': '24',
        '3rd': '23'
    }
    
    # Get course code based on course name
    course_name = class_info.course.lower().strip()
    course_code_map = {
        'bca': 'bca',
        'bsc computer science': 'bsc',
        'bsc cs': 'bsc',
        'bsc it': 'bsit',
        'mca': 'mca',
        'msc it': 'msit',
        'ms it': 'msit'
    }
    
    # Find matching course code
    course_code = None
    for key, code in course_code_map.items():
        if key in course_name:
            course_code = code
            break
    
    # Fallback: use first 3-4 letters of course name
    if not course_code:
        course_code = ''.join(c for c in course_name if c.isalnum())[:4]
    
    # Get year code
    year_code = year_code_map.get(class_info.year, '25')
    
    # Find existing students in this class to determine next number
    existing_students = db.session.query(User).join(StudentClass).filter(
        StudentClass.class_id == class_id
    ).all()
    
    # Get all register numbers for this class pattern
    existing_numbers = []
    pattern_prefix = f"{course_code}{year_code}"
    
    for student in existing_students:
        if student.register_number and student.register_number.startswith(pattern_prefix):
            # Extract number part (last 3 digits)
            try:
                num_part = int(student.register_number[-3:])
                existing_numbers.append(num_part)
            except:
                pass
    
    # Find next available number (001-010 for each class, but can extend if needed)
    next_number = 1
    for i in range(1, 11):  # 10 students per class
        if i not in existing_numbers:
            next_number = i
            break
    else:
        # If all 10 slots are taken, use next available
        next_number = max(existing_numbers) + 1 if existing_numbers else 1
    
    # Format: course_code + year_code + 3-digit number
    register_number = f"{course_code}{year_code}{next_number:03d}"
    
    # Ensure uniqueness (in case of conflicts)
    counter = 0
    while User.query.filter_by(register_number=register_number).first():
        next_number = (next_number % 10) + 1
        if next_number == 0:
            next_number = 1
        register_number = f"{course_code}{year_code}{next_number:03d}"
        counter += 1
        if counter > 20:  # Safety check
            register_number = f"{course_code}{year_code}{next_number:03d}_{counter}"
            break
    
    return register_number

@app.route('/admin/users/add', methods=['POST'])
@login_required
def add_user():
    if current_user.user_type != UserType.ADMIN:
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.json
    user_type = data['user_type']
    
    if user_type == UserType.STUDENT:
        # Auto-generate register number if class is provided and register_number is not manually entered
        register_number = data.get('register_number', '').strip()
        class_id = data.get('class_id')
        
        if not register_number and class_id:
            # Auto-generate based on class
            register_number = generate_student_register_number(class_id)
            if not register_number:
                return jsonify({'error': 'Invalid class selected'}), 400
        elif not register_number:
            return jsonify({'error': 'Register number is required or select a class to auto-generate'}), 400
        
        # Check if register number already exists
        if User.query.filter_by(register_number=register_number).first():
            return jsonify({'error': f'Register number {register_number} already exists'}), 400
        
        user = User(
            username=register_number,
            register_number=register_number,
            full_name=data['full_name'],
            email=data.get('email', ''),
            user_type=UserType.STUDENT
        )
        user.set_password('student123')  # Default password
        db.session.add(user)
        db.session.flush()
        
        # Assign to class
        if class_id:
            student_class = StudentClass(
                student_id=user.id,
                class_id=class_id
            )
            db.session.add(student_class)
    else:
        user = User(
            username=data['username'],
            full_name=data['full_name'],
            email=data.get('email', ''),
            user_type=UserType.TEACHER
        )
        user.set_password('teacher123')  # Default password
        db.session.add(user)
        db.session.flush()
        
        # Assign classes
        if data.get('class_ids'):
            for class_id in data['class_ids']:
                teacher_class = TeacherClass(
                    teacher_id=user.id,
                    class_id=class_id,
                    subject=data.get('subject', '')
                )
                db.session.add(teacher_class)
    
    db.session.commit()
    return jsonify({'success': True, 'message': 'User added successfully'})

# Teacher Absence Management Routes
@app.route('/admin/absences')
@login_required
def admin_absences():
    if current_user.user_type != UserType.ADMIN:
        return redirect(url_for('index'))
    
    absences = TeacherAbsence.query.order_by(TeacherAbsence.absence_date.desc(), TeacherAbsence.created_at.desc()).all()
    teachers = User.query.filter_by(user_type=UserType.TEACHER).all()
    
    return render_template('admin/absences.html', absences=absences, teachers=teachers)

@app.route('/admin/absences/report', methods=['POST'])
@login_required
def report_absence():
    """Report teacher absence and automatically resolve it"""
    if current_user.user_type != UserType.ADMIN:
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.json
    teacher_id = data.get('teacher_id')
    absence_date_str = data.get('absence_date')
    reason = data.get('reason', '')
    
    if not teacher_id or not absence_date_str:
        return jsonify({'error': 'Teacher ID and absence date are required'}), 400
    
    absence_date = datetime.strptime(absence_date_str, '%Y-%m-%d').date()
    
    # Get day name from date
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    day_name = days[absence_date.weekday()]
    
    # Find all classes affected by this absence
    affected_classes = Timetable.query.filter_by(
        teacher_id=teacher_id,
        day=day_name
    ).all()
    
    if not affected_classes:
        return jsonify({'error': 'No classes found for this teacher on the selected date'}), 400
    
    # Create absence record
    absence = TeacherAbsence(
        teacher_id=teacher_id,
        absence_date=absence_date,
        reason=reason,
        status='pending',
        created_by=current_user.id
    )
    db.session.add(absence)
    db.session.flush()
    
    # Automatically resolve each affected class
    resolution_summary = []
    notifications_created = 0
    
    for timetable_entry in affected_classes:
        resolution = auto_resolve_absence(timetable_entry, teacher_id, absence_date, day_name)
        resolution_summary.append(resolution)
        
        # Create notification for students
        class_info = Class.query.get(timetable_entry.class_id)
        if class_info:
            # Determine notification type and title based on resolution
            if resolution['type'] == 'substitute':
                notif_type = 'substitute'
                notif_title = f"🔄 Substitute Teacher: {timetable_entry.subject}"
            elif resolution['type'] == 'rescheduled':
                notif_type = 'rescheduled'
                notif_title = f"📅 Class Rescheduled: {timetable_entry.subject}"
            else:
                notif_type = 'cancelled'
                notif_title = f"❌ Class Cancelled: {timetable_entry.subject}"
            
            notification = Notification(
                title=notif_title,
                message=resolution['notification_message'],
                class_id=timetable_entry.class_id,
                created_by=current_user.id,
                notification_type=notif_type
            )
            db.session.add(notification)
            notifications_created += 1
    
    # Update absence status
    if resolution_summary:
        absence.status = 'resolved'
        absence.resolved_at = datetime.utcnow()
        if any(r['type'] == 'substitute' for r in resolution_summary):
            absence.resolution_type = 'substitute'
            absence.substitute_teacher_id = next((r.get('substitute_id') for r in resolution_summary if r.get('substitute_id')), None)
        elif any(r['type'] == 'rescheduled' for r in resolution_summary):
            absence.resolution_type = 'rescheduled'
        else:
            absence.resolution_type = 'cancelled'
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f'Absence reported and resolved automatically! {len(affected_classes)} classes updated, {notifications_created} notifications sent.',
        'resolutions': resolution_summary
    })

def auto_resolve_absence(timetable_entry, absent_teacher_id, absence_date, day_name):
    """Automatically resolve teacher absence by finding substitute or rescheduling"""
    class_id = timetable_entry.class_id
    subject = timetable_entry.subject
    time_slot = timetable_entry.time_slot
    
    # Strategy 1: Find substitute teacher
    substitute_teacher = find_substitute_teacher(class_id, subject, day_name, time_slot, absent_teacher_id)
    
    if substitute_teacher:
        # Assign substitute teacher
        timetable_entry.teacher_id = substitute_teacher.id
        timetable_entry.updated_at = datetime.utcnow()
        db.session.commit()
        
        return {
            'type': 'substitute',
            'class': Class.query.get(class_id).class_name,
            'subject': subject,
            'time': time_slot,
            'substitute_teacher': substitute_teacher.full_name,
            'substitute_id': substitute_teacher.id,
            'notification_message': f"Teacher absence for {subject} on {absence_date.strftime('%B %d, %Y')}. Substitute teacher: {substitute_teacher.full_name}. Class will be held as scheduled at {time_slot}."
        }
    
    # Strategy 2: Find free slot to reschedule
    free_slot = find_free_slot(class_id, day_name, time_slot)
    
    if free_slot:
        # Reschedule to free slot
        old_time = timetable_entry.time_slot
        timetable_entry.time_slot = free_slot['time_slot']
        timetable_entry.room = free_slot.get('room', timetable_entry.room)
        timetable_entry.updated_at = datetime.utcnow()
        db.session.commit()
        
        return {
            'type': 'rescheduled',
            'class': Class.query.get(class_id).class_name,
            'subject': subject,
            'old_time': old_time,
            'new_time': free_slot['time_slot'],
            'new_day': free_slot.get('day', day_name),
            'notification_message': f"Class {subject} on {absence_date.strftime('%B %d, %Y')} has been rescheduled from {old_time} to {free_slot['time_slot']} ({free_slot.get('day', day_name)}). Please note the new timing."
        }
    
    # Strategy 3: Cancel class (last resort)
    return {
        'type': 'cancelled',
        'class': Class.query.get(class_id).class_name,
        'subject': subject,
        'time': time_slot,
        'notification_message': f"Class {subject} on {absence_date.strftime('%B %d, %Y')} at {time_slot} has been cancelled due to teacher absence. Please check for any assignments or updates."
    }

def find_substitute_teacher(class_id, subject, day_name, time_slot, absent_teacher_id):
    """Find a suitable substitute teacher"""
    # Get all teachers assigned to this class
    teacher_classes = TeacherClass.query.filter_by(class_id=class_id).all()
    available_teachers = [tc.teacher for tc in teacher_classes if tc.teacher_id != absent_teacher_id]
    
    if not available_teachers:
        # Try to find any teacher who teaches similar subject
        all_teachers = User.query.filter_by(user_type=UserType.TEACHER).filter(User.id != absent_teacher_id).all()
        for teacher in all_teachers:
            teacher_classes = TeacherClass.query.filter_by(teacher_id=teacher.id).all()
            for tc in teacher_classes:
                if tc.subject and (subject.lower() in tc.subject.lower() or tc.subject.lower() in subject.lower()):
                    # Check if teacher is free at this time
                    if is_teacher_free(teacher.id, day_name, time_slot):
                        return teacher
        return None
    
    # Check which available teachers are free at this time
    for teacher in available_teachers:
        if is_teacher_free(teacher.id, day_name, time_slot):
            # Prefer teacher who teaches same or similar subject
            teacher_classes = TeacherClass.query.filter_by(teacher_id=teacher.id, class_id=class_id).first()
            if teacher_classes and teacher_classes.subject:
                if subject.lower() in teacher_classes.subject.lower() or teacher_classes.subject.lower() in subject.lower():
                    return teacher
            return teacher
    
    # If no teacher from same class is free, try any free teacher
    all_teachers = User.query.filter_by(user_type=UserType.TEACHER).filter(User.id != absent_teacher_id).all()
    for teacher in all_teachers:
        if is_teacher_free(teacher.id, day_name, time_slot):
            return teacher
    
    return None

def is_teacher_free(teacher_id, day_name, time_slot):
    """Check if teacher has no class at given day and time"""
    conflicting = Timetable.query.filter_by(
        teacher_id=teacher_id,
        day=day_name,
        time_slot=time_slot
    ).first()
    return conflicting is None

def find_free_slot(class_id, day_name, time_slot):
    """Find a free time slot for rescheduling"""
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
    
    # Get all timetable entries for this class (excluding the one being rescheduled)
    current_entry = Timetable.query.filter_by(class_id=class_id, day=day_name, time_slot=time_slot).first()
    all_entries = Timetable.query.filter_by(class_id=class_id).all()
    
    # Common time slots
    common_slots = ['09:00-10:00', '10:00-11:00', '11:00-12:00', '12:00-13:00', '13:00-14:00', '14:00-15:00', '15:00-16:00']
    
    # Try to find free slot on same day first (adjacent slots)
    if time_slot in common_slots:
        current_index = common_slots.index(time_slot)
        day_entries = [e for e in all_entries if e.day == day_name and e.id != (current_entry.id if current_entry else -1)]
        used_times = {e.time_slot for e in day_entries}
        
        # Try next slot
        if current_index + 1 < len(common_slots):
            next_slot = common_slots[current_index + 1]
            if next_slot not in used_times:
                room = current_entry.room if current_entry else 'Room-101'
                return {'day': day_name, 'time_slot': next_slot, 'room': room}
        
        # Try previous slot
        if current_index - 1 >= 0:
            prev_slot = common_slots[current_index - 1]
            if prev_slot not in used_times:
                room = current_entry.room if current_entry else 'Room-101'
                return {'day': day_name, 'time_slot': prev_slot, 'room': room}
    
    # Try other days
    for day in days:
        if day != day_name:
            day_entries = [e for e in all_entries if e.day == day]
            used_times = {e.time_slot for e in day_entries}
            
            # Find first free slot on this day
            for slot in common_slots:
                if slot not in used_times:
                    # Get a room from existing entries or use default
                    room = day_entries[0].room if day_entries else (current_entry.room if current_entry else 'Room-101')
                    return {'day': day, 'time_slot': slot, 'room': room}
    
    return None

if __name__ == '__main__':
    # Initialize sample data
    with app.app_context():
        # Create classes if they don't exist
        classes_data = [
            ('BCA-1st', 'BCA', '1st'),
            ('BCA-2nd', 'BCA', '2nd'),
            ('BCA-3rd', 'BCA', '3rd'),
            ('BSc CS-1st', 'BSc Computer Science', '1st'),
            ('BSc CS-2nd', 'BSc Computer Science', '2nd'),
            ('BSc CS-3rd', 'BSc Computer Science', '3rd'),
            ('BSc IT-1st', 'BSc IT', '1st'),
            ('BSc IT-2nd', 'BSc IT', '2nd'),
            ('BSc IT-3rd', 'BSc IT', '3rd'),
            ('MCA-1st', 'MCA', '1st'),
            ('MCA-2nd', 'MCA', '2nd'),
            ('MSc IT-1st', 'MSc IT', '1st'),
            ('MSc IT-2nd', 'MSc IT', '2nd'),
        ]
        
        for class_name, course, year in classes_data:
            if not Class.query.filter_by(class_name=class_name).first():
                new_class = Class(class_name=class_name, course=course, year=year)
                db.session.add(new_class)
        
        db.session.commit()
    
    app.run(debug=True, host='0.0.0.0', port=5000)


