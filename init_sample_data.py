"""
Script to initialize sample data for the Educational Management System
Run this script once to populate the database with sample students, teachers, and data
"""

from app import app, db
from models import User, Class, Timetable, Event, Notification, StudentClass, TeacherClass, UserType
from datetime import datetime, date, time, timedelta

def init_sample_data():
    with app.app_context():
        print("Initializing sample data...")
        
        # Get or create classes
        classes = {}
        class_data = [
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
        
        for class_name, course, year in class_data:
            class_obj = Class.query.filter_by(class_name=class_name).first()
            if not class_obj:
                class_obj = Class(class_name=class_name, course=course, year=year)
                db.session.add(class_obj)
            classes[class_name] = class_obj
        
        db.session.commit()
        print("[OK] Classes created")
        
        # Create sample students
        sample_students = [
            ('BCA001', 'John Doe', 'BCA-1st'),
            ('BCA002', 'Jane Smith', 'BCA-1st'),
            ('BCA003', 'Mike Johnson', 'BCA-2nd'),
            ('BSC001', 'Sarah Williams', 'BSc CS-1st'),
            ('BSC002', 'David Brown', 'BSc CS-2nd'),
            ('BSI001', 'Emily Davis', 'BSc IT-1st'),
            ('MCA001', 'Robert Wilson', 'MCA-1st'),
            ('MSI001', 'Lisa Anderson', 'MSc IT-1st'),
        ]
        
        for reg_num, name, class_name in sample_students:
            if not User.query.filter_by(register_number=reg_num).first():
                student = User(
                    username=reg_num,
                    register_number=reg_num,
                    full_name=name,
                    email=f'{reg_num.lower()}@college.edu',
                    user_type=UserType.STUDENT
                )
                student.set_password('student123')
                db.session.add(student)
                db.session.flush()
                
                # Assign to class
                student_class = StudentClass(
                    student_id=student.id,
                    class_id=classes[class_name].id
                )
                db.session.add(student_class)
        
        db.session.commit()
        print("[OK] Sample students created")
        
        # Create sample teachers
        sample_teachers = [
            ('teacher1', 'Dr. Smith', ['BCA-1st', 'BCA-2nd'], 'Mathematics'),
            ('teacher2', 'Prof. Johnson', ['BSc CS-1st', 'BSc CS-2nd'], 'Programming'),
            ('teacher3', 'Dr. Williams', ['BSc IT-1st', 'BSc IT-2nd'], 'Database Systems'),
            ('teacher4', 'Prof. Brown', ['MCA-1st', 'MSc IT-1st'], 'Web Development'),
        ]
        
        for username, name, class_names, subject in sample_teachers:
            if not User.query.filter_by(username=username).first():
                teacher = User(
                    username=username,
                    full_name=name,
                    email=f'{username}@college.edu',
                    user_type=UserType.TEACHER
                )
                teacher.set_password('teacher123')
                db.session.add(teacher)
                db.session.flush()
                
                # Assign classes
                for class_name in class_names:
                    teacher_class = TeacherClass(
                        teacher_id=teacher.id,
                        class_id=classes[class_name].id,
                        subject=subject
                    )
                    db.session.add(teacher_class)
        
        db.session.commit()
        print("[OK] Sample teachers created")
        
        # Create sample timetable entries
        bca1 = classes['BCA-1st']
        teacher1 = User.query.filter_by(username='teacher1').first()
        
        sample_timetable = [
            ('Monday', '09:00-10:00', 'Mathematics', teacher1.id if teacher1 else None, 'Room-101'),
            ('Monday', '10:00-11:00', 'Programming', None, 'Lab-201'),
            ('Tuesday', '09:00-10:00', 'Database Systems', None, 'Room-102'),
            ('Wednesday', '09:00-10:00', 'Web Development', None, 'Lab-202'),
            ('Thursday', '09:00-10:00', 'Mathematics', teacher1.id if teacher1 else None, 'Room-101'),
            ('Friday', '09:00-10:00', 'Programming', None, 'Lab-201'),
        ]
        
        for day, time_slot, subject, teacher_id, room in sample_timetable:
            # Add to BCA-1st
            if not Timetable.query.filter_by(class_id=bca1.id, day=day, time_slot=time_slot).first():
                timetable = Timetable(
                    class_id=bca1.id,
                    day=day,
                    time_slot=time_slot,
                    subject=subject,
                    teacher_id=teacher_id,
                    room=room
                )
                db.session.add(timetable)
        
        db.session.commit()
        print("[OK] Sample timetable entries created")
        
        # Create sample events
        sample_events = [
            ('Annual Sports Day', 'Join us for the annual sports day celebration', date.today() + timedelta(days=7), time(9, 0), None),
            ('Tech Fest 2024', 'Annual technical festival with competitions and workshops', date.today() + timedelta(days=14), time(10, 0), None),
            ('BCA Class Test', 'Mathematics class test for BCA 1st year', date.today() + timedelta(days=3), time(11, 0), bca1.id),
        ]
        
        admin = User.query.filter_by(username='admin').first()
        if admin:
            for title, desc, event_date, event_time, class_id in sample_events:
                if not Event.query.filter_by(title=title, event_date=event_date).first():
                    event = Event(
                        title=title,
                        description=desc,
                        event_date=event_date,
                        event_time=event_time,
                        class_id=class_id,
                        created_by=admin.id
                    )
                    db.session.add(event)
        
        db.session.commit()
        print("[OK] Sample events created")
        
        # Create sample notifications
        sample_notifications = [
            ('Welcome to New Academic Year', 'Welcome all students to the new academic year. Please check your timetables regularly.', None),
            ('Library Hours Extended', 'Library will remain open until 8 PM from Monday to Friday.', None),
            ('BCA Assignment Submission', 'Submit your programming assignment by next Friday.', bca1.id),
        ]
        
        if admin:
            for title, message, class_id in sample_notifications:
                if not Notification.query.filter_by(title=title).first():
                    notification = Notification(
                        title=title,
                        message=message,
                        class_id=class_id,
                        created_by=admin.id
                    )
                    db.session.add(notification)
        
        db.session.commit()
        print("[OK] Sample notifications created")
        
        print("\n[SUCCESS] Sample data initialization complete!")
        print("\nDefault Login Credentials:")
        print("Student: BCA001 / student123")
        print("Teacher: teacher1 / teacher123")
        print("Admin: admin / admin123")

if __name__ == '__main__':
    init_sample_data()

