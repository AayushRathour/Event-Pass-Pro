# Event Pass Generator - Full Stack Application

A complete event management and digital gate pass generation system built with Django backend and modern frontend.

## 🎯 Features

### ✅ Core Functionality
1. **Single-Use QR Code System**
   - QR codes are valid for only one scan
   - After first scan, code becomes invalid
   - All scan attempts are logged

2. **Admin Dashboard**
   - Interactive pie charts showing attendance statistics
   - Real-time data visualization
   - Tracks Present, Absent, and Registered members
   - Event-wise statistics

3. **Admin Authentication**
   - Secure login system for administrators
   - Role-based access control
   - Session management

4. **Professional Email Templates**
   - QR code sent to registered email
   - College logo included
   - Professional formatting

5. **Running Events Display**
   - Homepage shows active/ongoing events
   - Live event status indicators
   - Registration capacity tracking

6. **Event Management**
   - Create, edit, and delete events
   - Set event capacity and venue
   - Track event status (upcoming/ongoing/completed)

7. **QR Code Scanner**
   - Real-time QR code scanning
   - Shows attendee information
   - Tracks number of successful scans

8. **Complete UML Documentation**
   - ER Diagrams
   - Class Diagrams
   - Sequence Diagrams
   - Use Case Diagrams
   - Activity Diagrams
   - State Diagrams
   - Component Diagrams

## 🛠️ Technology Stack

### Backend
- **Framework**: Django 4.2.23
- **Database**: SQLite3
- **REST API**: Django REST Framework
- **QR Code**: Python qrcode library
- **Image Processing**: Pillow

### Frontend
- **HTML5**: Semantic markup
- **CSS3**: Custom styling with animations
- **JavaScript**: Vanilla JS for API interactions
- **Chart.js**: Interactive pie charts
- **Html5-qrcode**: QR code scanning
- **Font Awesome**: Icons
- **Google Fonts**: Poppins font family

## 📁 Project Structure

```
Event Pass Generator/
├── eventpass_backend/          # Django project settings
│   ├── settings.py            # Main configuration
│   ├── urls.py                # Root URL configuration
│   └── wsgi.py                # WSGI configuration
├── events/                    # Main Django app
│   ├── models.py              # Database models
│   ├── views.py               # API views and endpoints
│   ├── serializers.py         # REST serializers
│   ├── admin.py               # Admin panel configuration
│   └── urls.py                # App URL patterns
├── templates/                 # HTML templates
│   ├── index.html             # Homepage with event listing
│   ├── scan.html              # QR scanner page
│   ├── dashboard.html         # Admin dashboard
│   └── admin_login.html       # Admin login page
├── static/                    # Static files
│   ├── css/
│   │   └── style.css          # Main stylesheet
│   ├── js/
│   │   ├── script.js          # Homepage logic
│   │   ├── scanner.js         # QR scanning logic
│   │   └── dashboard.js       # Dashboard charts
│   └── images/
│       └── cmrtc.png          # College logo
├── db.sqlite3                 # SQLite database
├── manage.py                  # Django management script
├── UML_DIAGRAMS.md           # Complete UML documentation
└── README.md                  # This file
```

## 🚀 Installation & Setup

### Prerequisites
- Python 3.8 or higher
- pip package manager

### Step 1: Install Dependencies
```bash
pip install django qrcode pillow djangorestframework django-cors-headers
```

### Step 2: Run Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

### Step 3: Create Superuser (Admin)
```bash
python manage.py createsuperuser
```
Follow the prompts to create admin credentials:
- Username: admin
- Email: admin@eventpass.com
- Password: (choose a secure password)

### Step 4: Run Development Server
```bash
python manage.py runserver
```

The application will be available at:
- **Homepage**: http://127.0.0.1:8000/
- **Admin Panel**: http://127.0.0.1:8000/admin/
- **Dashboard**: http://127.0.0.1:8000/dashboard/
- **QR Scanner**: http://127.0.0.1:8000/scan/

## 📋 Usage Guide

### For Students/Participants

1. **Register for Event**
   - Visit homepage
   - View running events
   - Select an event
   - Fill registration form (Name, Student ID, Email)
   - Submit to generate QR code
   - QR code is displayed and sent to email

2. **Receive Pass**
   - Check your email for the gate pass
   - QR code is valid for single entry only
   - Save or print for event entry

### For Event Organizers (Admin)

1. **Login to Admin Panel**
   - Visit `/admin/` or `/admin-login/`
   - Enter admin credentials
   - Access full admin interface

2. **Create Event**
   - Go to Events section
   - Click "Add Event"
   - Fill in event details:
     - Name, Description
     - Start and end date/time
     - Venue, Capacity
     - Status (upcoming/ongoing/completed)
   - Save event

3. **View Dashboard**
   - Visit `/dashboard/`
   - See overall statistics
   - View pie chart of attendance
   - Check event-wise breakdown

4. **Scan QR Codes**
   - Visit `/scan/`
   - Allow camera access
   - Scan participant QR codes
   - System validates and marks attendance
   - Invalid/already-used codes are rejected

## 🔒 Security Features

1. **Single-Use QR Codes**
   - Each QR code can only be scanned once
   - Prevents duplicate entries
   - All attempts logged with timestamps

2. **Admin Authentication**
   - Password-protected admin access
   - Session-based authentication
   - CSRF protection enabled

3. **Attendance Logging**
   - All scan attempts recorded
   - IP address tracking
   - Audit trail for security

## 📊 Database Schema

### Models

1. **Event**
   - Stores event information
   - Tracks capacity and registrations
   - Manages event lifecycle

2. **Registration**
   - Links participants to events
   - Stores QR code data
   - Tracks attendance status
   - Validates single-use constraint

3. **AttendanceLog**
   - Logs all scan attempts
   - Records success/failure reasons
   - Maintains audit trail

## 🎨 Features in Detail

### 1. Single-Use QR Code System
- Each registration generates a unique UUID
- QR code contains encrypted registration data
- `is_valid` flag prevents reuse
- `mark_as_scanned()` method ensures atomicity
- All scan attempts logged for security

### 2. Dashboard Analytics
- **Pie Chart**: Visual representation of attendance
  - Present (Blue)
  - Absent (Red/Pink)
  - Registered but not yet attended (Gray)
- **Statistics Cards**: Quick metrics
  - Total events
  - Total registrations
  - Present count
  - Absent count
- **Event List**: Detailed per-event statistics

### 3. Real-Time Event Display
- Shows only active/ongoing events
- Live status indicators
- Registration progress tracking
- Quick registration buttons

### 4. QR Scanner Interface
- Camera-based scanning
- File upload fallback
- Real-time validation feedback
- Success/failure indicators
- Scan counter

## 🔧 Configuration

### Email Setup (Optional)
To enable email functionality, update `settings.py`:

```python
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'your-email@gmail.com'
EMAIL_HOST_PASSWORD = 'your-app-password'
```

### Customize College Logo
Replace `static/images/cmrtc.png` with your college logo.

## 📱 Responsive Design
- Mobile-friendly interface
- Responsive grid layouts
- Touch-optimized controls
- Works on all modern browsers

## 🐛 Troubleshooting

### Common Issues

1. **Camera not working in scanner**
   - Ensure HTTPS or localhost
   - Grant camera permissions
   - Use file upload as fallback

2. **QR code not generating**
   - Check database connection
   - Verify qrcode library installed
   - Check browser console for errors

3. **Admin login failing**
   - Verify superuser created
   - Check credentials
   - Ensure user has `is_staff` permission

## 📈 Future Enhancements

- [ ] Export attendance reports (CSV/PDF)
- [ ] SMS notifications
- [ ] Multi-language support
- [ ] Advanced analytics
- [ ] Bulk event creation
- [ ] Participant check-in history
- [ ] Integration with calendar apps

## 👥 Contributing

This is an academic project. For improvements:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📄 License

This project is created for educational purposes.

## 🙏 Acknowledgments

- College: CMRTC
- Framework: Django
- Frontend Libraries: Chart.js, Html5-qrcode
- Icons: Font Awesome
- Fonts: Google Fonts (Poppins)

## 📞 Support

For questions or issues:
- Check UML_DIAGRAMS.md for system architecture
- Review Django admin documentation
- Check browser console for errors

---

**Built with ❤️ for Event Management**
