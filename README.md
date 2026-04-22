# Educational Management System with AI Automation

A comprehensive educational management system for managing multiple classes, timetables, events, notifications, and an AI-powered chatbot.

## Features

- **Multi-Class Support**: BCA, BSc Computer Science, BSc IT, PG MCA, MSc IT (all years)
- **User Management**: Separate portals for Students, Teachers, and Admin
- **Timetable Management**: Class-specific timetables
- **Event Scheduling**: Schedule and manage events
- **Notifications**: Real-time notifications system
- **AI Chatbot**: Intelligent chatbot for student queries
- **Modern UI**: Attractive and professional design

## Technologies

- Frontend: HTML, CSS, JavaScript
- Backend: Python (Flask)
- Database: SQLite (can be upgraded to PostgreSQL/MySQL)

## Installation & Setup

### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Initialize Sample Data (Optional but Recommended)
This will create sample students, teachers, timetables, events, and notifications:
```bash
python init_sample_data.py
```

### Step 3: Run the Application
```bash
python app.py
```

### Step 4: Access the Application
Open your browser and navigate to:
```
http://localhost:5000
```

## Default Login Credentials

After running `init_sample_data.py`, you can use these credentials:

- **Admin**: 
  - Username: `admin`
  - Password: `admin123`

- **Student**: 
  - Register Number: `BCA001` (or BCA002, BCA003, BSC001, etc.)
  - Password: `student123`

- **Teacher**: 
  - Username: `teacher1` (or teacher2, teacher3, teacher4)
  - Password: `teacher123`

## Features Overview

### Student Portal
- View personalized dashboard
- Check class timetable
- View upcoming events
- Read notifications
- Interact with AI chatbot for queries

### Teacher Portal
- View assigned classes
- Check class schedules
- View upcoming events

### Admin Portal
- Manage all classes
- Create and manage timetables
- Schedule events
- Send notifications
- Add students and teachers
- View system statistics

## Project Structure

```
THRISH/
├── app.py                 # Main Flask application
├── models.py              # Database models
├── requirements.txt       # Python dependencies
├── static/               # Static files (CSS, JS, images)
│   ├── css/
│   ├── js/
│   └── images/
└── templates/            # HTML templates
    ├── auth/
    ├── student/
    ├── teacher/
    └── admin/
```

