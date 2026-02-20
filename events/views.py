from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, FileResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.db.models import Count, Q
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from email.mime.image import MIMEImage
import os
from datetime import datetime
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
import qrcode
import io
import base64
import json
import uuid
from reportlab.lib.pagesizes import A7, A4, letter
from reportlab.lib.units import mm, inch
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image as RLImage, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from PIL import Image
from .models import Event, Registration, AttendanceLog
from .serializers import (
    EventSerializer, RegistrationSerializer, RegistrationCreateSerializer,
    AttendanceLogSerializer, EventStatisticsSerializer
)


def send_registration_email(registration, qr_code_image_base64):
    """Send registration confirmation email with QR code"""
    try:
        event = registration.event
        
        # Prepare email context
        context = {
            'name': registration.name,
            'event_name': event.name,
            'event_venue': event.venue,
            'event_date': event.start_date.strftime('%B %d, %Y at %I:%M %p'),
            'student_id': registration.student_id,
            'registration_id': str(registration.id)[:8].upper(),
        }
        
        # Render HTML email
        html_content = render_to_string('emails/registration_email.html', context)
        
        # Create email message
        subject = f'Event Registration Confirmation - {event.name}'
        from_email = settings.DEFAULT_FROM_EMAIL
        to_email = [registration.email]
        
        # Create message
        msg = EmailMultiAlternatives(subject, '', from_email, to_email)
        msg.attach_alternative(html_content, "text/html")
        
        # Attach college logo
        logo_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'cmrtc.png')
        if os.path.exists(logo_path):
            with open(logo_path, 'rb') as f:
                logo_img = MIMEImage(f.read())
                logo_img.add_header('Content-ID', '<college_logo>')
                logo_img.add_header('Content-Disposition', 'inline', filename='logo.png')
                msg.attach(logo_img)
        
        # Attach QR code
        # Convert base64 to bytes
        qr_code_data = qr_code_image_base64.split(',')[1]  # Remove data:image/png;base64, prefix
        qr_code_bytes = base64.b64decode(qr_code_data)
        qr_img = MIMEImage(qr_code_bytes)
        qr_img.add_header('Content-ID', '<qr_code>')
        qr_img.add_header('Content-Disposition', 'inline', filename='qr_code.png')
        msg.attach(qr_img)
        
        # Send email
        msg.send()
        return True
        
    except Exception as e:
        print(f"Error sending email: {str(e)}")
        return False


class EventViewSet(viewsets.ModelViewSet):
    """ViewSet for managing events"""
    queryset = Event.objects.all()
    serializer_class = EventSerializer
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [IsAuthenticated()]
    
    @action(detail=False, methods=['get'])
    def active_events(self, request):
        """Get all currently active/ongoing events"""
        now = timezone.now()
        active = Event.objects.filter(
            start_date__lte=now,
            end_date__gte=now,
            status='ongoing'
        )
        serializer = self.get_serializer(active, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def statistics(self, request, pk=None):
        """Get statistics for a specific event"""
        event = self.get_object()
        data = {
            'event_name': event.name,
            'registered': event.registered_count,
            'present': event.present_count,
            'absent': event.absent_count,
            'attendance_rate': (event.present_count / event.registered_count * 100) if event.registered_count > 0 else 0
        }
        return Response(data)


class RegistrationViewSet(viewsets.ModelViewSet):
    """ViewSet for managing registrations"""
    queryset = Registration.objects.all()
    serializer_class = RegistrationSerializer
    
    def get_serializer_class(self):
        if self.action == 'create':
            return RegistrationCreateSerializer
        return RegistrationSerializer
    
    def get_permissions(self):
        if self.action == 'create':
            return [AllowAny()]
        return [IsAuthenticated()]
    
    def create(self, request, *args, **kwargs):
        """Create a new registration and generate QR code"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Generate unique QR code data
        qr_uuid = str(uuid.uuid4())
        qr_data_dict = {
            'registration_id': qr_uuid,
            'event_id': str(serializer.validated_data['event'].id),
            'name': serializer.validated_data['name'],
            'student_id': serializer.validated_data['student_id'],
            'email': serializer.validated_data['email'],
            'timestamp': timezone.now().isoformat()
        }
        qr_data = json.dumps(qr_data_dict)
        
        # Generate QR code image
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(qr_data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to base64
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        img_str = base64.b64encode(buffer.getvalue()).decode()
        qr_code_image = f"data:image/png;base64,{img_str}"
        
        # Save registration
        registration = serializer.save(
            qr_code_data=qr_data,
            qr_code_image=qr_code_image
        )
        
        # Send confirmation email
        email_sent = send_registration_email(registration, qr_code_image)
        
        # Return registration data with QR code
        response_serializer = RegistrationSerializer(registration)
        return Response({
            **response_serializer.data,
            'qr_code_image': qr_code_image,
            'email_sent': email_sent
        }, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['post'])
    def verify_qr(self, request):
        """Verify and mark QR code as scanned"""
        qr_data = request.data.get('qr_data')
        if not qr_data:
            return Response({'error': 'QR data is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Parse QR data
            qr_dict = json.loads(qr_data)
            
            # Find registration by QR code data
            registration = Registration.objects.filter(qr_code_data=qr_data).first()
            
            if not registration:
                return Response({
                    'valid': False,
                    'message': 'Invalid QR code',
                    'scan_result': 'invalid'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Get client IP
            ip_address = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0] or \
                        request.META.get('REMOTE_ADDR')
            
            # Check if already scanned
            if not registration.is_valid:
                # Log failed attempt
                AttendanceLog.objects.create(
                    registration=registration,
                    scan_result='already_used',
                    ip_address=ip_address
                )
                return Response({
                    'valid': False,
                    'message': 'QR code already used',
                    'scan_result': 'already_used',
                    'registration': RegistrationSerializer(registration).data
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Mark as scanned
            registration.mark_as_scanned()
            
            # Log successful scan
            AttendanceLog.objects.create(
                registration=registration,
                scan_result='success',
                ip_address=ip_address
            )
            
            return Response({
                'valid': True,
                'message': 'Attendance marked successfully',
                'scan_result': 'success',
                'registration': RegistrationSerializer(registration).data
            }, status=status.HTTP_200_OK)
            
        except json.JSONDecodeError:
            return Response({
                'valid': False,
                'message': 'Invalid QR code format',
                'scan_result': 'invalid'
            }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@login_required
def dashboard_statistics(request):
    """Get overall dashboard statistics"""
    total_events = Event.objects.count()
    now = timezone.now()
    active_events = Event.objects.filter(
        start_date__lte=now,
        end_date__gte=now,
        status='ongoing'
    ).count()
    
    total_registrations = Registration.objects.count()
    total_present = Registration.objects.filter(has_attended=True).count()
    total_absent = total_registrations - total_present
    attendance_rate = (total_present / total_registrations * 100) if total_registrations > 0 else 0
    
    data = {
        'total_events': total_events,
        'active_events': active_events,
        'total_registrations': total_registrations,
        'total_present': total_present,
        'total_absent': total_absent,
        'attendance_rate': round(attendance_rate, 2)
    }
    
    serializer = EventStatisticsSerializer(data)
    return Response(serializer.data)


@api_view(['POST'])
def admin_login_view(request):
    """Admin login endpoint"""
    username = request.data.get('username')
    password = request.data.get('password')
    
    user = authenticate(request, username=username, password=password)
    if user is not None and user.is_staff:
        login(request, user)
        return Response({
            'success': True,
            'message': 'Login successful',
            'user': {
                'username': user.username,
                'email': user.email,
                'is_staff': user.is_staff
            }
        })
    else:
        return Response({
            'success': False,
            'message': 'Invalid credentials or insufficient permissions'
        }, status=status.HTTP_401_UNAUTHORIZED)


@api_view(['POST'])
@login_required
def admin_logout_view(request):
    """Admin logout endpoint"""
    logout(request)
    return Response({
        'success': True,
        'message': 'Logout successful'
    })


# Template views
def index_view(request):
    """Home page view"""
    return render(request, 'index.html')


def events_view(request):
    """All events page view"""
    return render(request, 'events.html')


def scan_view(request):
    """QR scan page view"""
    return render(request, 'scan.html')


@login_required
def dashboard_view(request):
    """Admin dashboard view"""
    return render(request, 'dashboard.html')


def admin_login_page(request):
    """Admin login page"""
    # Handle POST request for login
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        if user is not None and user.is_staff:
            login(request, user)
            return redirect('admin-panel')
        else:
            context = {'error': 'Invalid credentials or you do not have admin permissions'}
            return render(request, 'admin_login.html', context)
    
    # If already logged in, redirect to admin panel
    if request.user.is_authenticated and request.user.is_staff:
        return redirect('admin-panel')
    
    return render(request, 'admin_login.html')


def admin_register_page(request):
    """Admin registration page"""
    # Handle POST request for registration
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        
        # Validation
        if password1 != password2:
            context = {'error': 'Passwords do not match'}
            return render(request, 'admin_register.html', context)
        
        # Check if username already exists
        from django.contrib.auth.models import User
        if User.objects.filter(username=username).exists():
            context = {'error': 'Username already exists'}
            return render(request, 'admin_register.html', context)
        
        # Check if email already exists
        if User.objects.filter(email=email).exists():
            context = {'error': 'Email already exists'}
            return render(request, 'admin_register.html', context)
        
        # Create user with staff permissions
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password1
        )
        user.is_staff = True
        user.save()
        
        context = {'success': 'Admin account created successfully! You can now login.'}
        return render(request, 'admin_register.html', context)
    
    # If already logged in, redirect to admin panel
    if request.user.is_authenticated and request.user.is_staff:
        return redirect('admin-panel')
    
    return render(request, 'admin_register.html')


@login_required
def admin_panel_view(request):
    """Custom admin panel home"""
    if not request.user.is_staff:
        return redirect('admin-login-page')
    
    # Get summary statistics
    total_events = Event.objects.count()
    total_registrations = Registration.objects.count()
    total_present = Registration.objects.filter(has_attended=True).count()
    recent_events = Event.objects.all()[:5]
    all_events = Event.objects.all()
    
    context = {
        'total_events': total_events,
        'total_registrations': total_registrations,
        'total_present': total_present,
        'recent_events': recent_events,
        'all_events': all_events,
    }
    return render(request, 'admin_panel.html', context)


@login_required
def admin_events_view(request):
    """List all events in custom admin"""
    if not request.user.is_staff:
        return redirect('admin-login-page')
    
    events = Event.objects.all()
    context = {'events': events}
    return render(request, 'admin_events.html', context)


@login_required
def admin_create_event(request):
    """Create new event"""
    if not request.user.is_staff:
        return redirect('admin-login-page')
    
    if request.method == 'POST':
        try:
            event = Event.objects.create(
                name=request.POST.get('name'),
                description=request.POST.get('description'),
                start_date=request.POST.get('start_date'),
                end_date=request.POST.get('end_date'),
                venue=request.POST.get('venue'),
                max_capacity=request.POST.get('max_capacity'),
                status=request.POST.get('status'),
                created_by=request.user
            )
            return redirect('admin-events')
        except Exception as e:
            context = {'error': str(e)}
            return render(request, 'admin_create_event.html', context)
    
    return render(request, 'admin_create_event.html')


@login_required
def admin_edit_event(request, event_id):
    """Edit existing event"""
    if not request.user.is_staff:
        return redirect('admin-login-page')
    
    event = get_object_or_404(Event, id=event_id)
    
    if request.method == 'POST':
        try:
            event.name = request.POST.get('name')
            event.description = request.POST.get('description')
            event.start_date = request.POST.get('start_date')
            event.end_date = request.POST.get('end_date')
            event.venue = request.POST.get('venue')
            event.max_capacity = request.POST.get('max_capacity')
            event.status = request.POST.get('status')
            event.save()
            return redirect('admin-events')
        except Exception as e:
            context = {'event': event, 'error': str(e)}
            return render(request, 'admin_edit_event.html', context)
    
    context = {'event': event}
    return render(request, 'admin_edit_event.html', context)


@login_required
def admin_delete_event(request, event_id):
    """Delete event"""
    if not request.user.is_staff:
        return redirect('admin-login-page')
    
    event = get_object_or_404(Event, id=event_id)
    
    if request.method == 'POST':
        event.delete()
        return redirect('admin-events')
    
    context = {'event': event}
    return render(request, 'admin_delete_event.html', context)


@login_required
def admin_registrations_view(request):
    """View all registrations"""
    if not request.user.is_staff:
        return redirect('admin-login-page')
    
    registrations = Registration.objects.select_related('event').all()
    context = {'registrations': registrations}
    return render(request, 'admin_registrations.html', context)


@login_required
def admin_delete_registration(request, registration_id):
    """Delete a registration"""
    if not request.user.is_staff:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        registration = get_object_or_404(Registration, id=registration_id)
        registration.delete()
        return JsonResponse({'success': True, 'message': 'Registration deleted successfully'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def admin_logs_view(request):
    """View attendance logs"""
    if not request.user.is_staff:
        return redirect('admin-login-page')
    
    logs = AttendanceLog.objects.select_related('registration', 'registration__event').all()[:100]
    context = {'logs': logs}
    return render(request, 'admin_logs.html', context)


@login_required
def generate_attendance_pdf(request):
    """Generate attendance PDF directly using reportlab (works in cloud environments)"""
    if not request.user.is_staff:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    try:
        # Get event_id from query params if provided
        event_id = request.GET.get('event_id')
        
        # Fetch registrations from database, ordered by id (ascending)
        registrations = Registration.objects.select_related('event').order_by('id')
        
        # Filter by event if specified
        if event_id:
            registrations = registrations.filter(event_id=event_id)
            try:
                selected_event = Event.objects.get(id=event_id)
                event_name = selected_event.name
            except Event.DoesNotExist:
                return JsonResponse({'error': 'Event not found'}, status=404)
        else:
            event_name = "All Events"
        
        if not registrations.exists():
            return JsonResponse({'error': 'No registrations found'}, status=404)
        
        # Create PDF in memory
        buffer = io.BytesIO()
        
        # Create PDF with custom page template
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=40,
            leftMargin=40,
            topMargin=15,
            bottomMargin=40
        )
        
        # Container for PDF elements
        elements = []
        
        # Styles
        styles = getSampleStyleSheet()
        
        # Custom styles
        estd_style = ParagraphStyle(
            'ESTD',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.black,
            alignment=TA_RIGHT,
            fontName='Helvetica-Bold'
        )
        
        title_style = ParagraphStyle(
            'Title',
            parent=styles['Normal'],
            fontSize=18,
            textColor=colors.HexColor('#1a237e'),
            alignment=TA_CENTER,
            fontName='Helvetica-Bold',
            spaceAfter=3,
            spaceBefore=0,
            leading=20
        )
        
        subtitle_style = ParagraphStyle(
            'Subtitle',
            parent=styles['Normal'],
            fontSize=11,
            textColor=colors.HexColor('#d32f2f'),
            alignment=TA_CENTER,
            fontName='Helvetica-Bold',
            spaceAfter=3,
            leading=13
        )
        
        accredited_style = ParagraphStyle(
            'Accredited',
            parent=styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#006400'),
            alignment=TA_CENTER,
            fontName='Helvetica',
            spaceAfter=2,
            leading=11
        )
        
        approved_style = ParagraphStyle(
            'Approved',
            parent=styles['Normal'],
            fontSize=8,
            textColor=colors.HexColor('#006400'),
            alignment=TA_CENTER,
            fontName='Helvetica',
            spaceAfter=8,
            leading=10
        )
        
        dept_style = ParagraphStyle(
            'Department',
            parent=styles['Normal'],
            fontSize=11,
            textColor=colors.black,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold',
            spaceAfter=0,
            spaceBefore=0
        )
        
        event_style = ParagraphStyle(
            'Event',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.black,
            alignment=TA_LEFT,
            fontName='Helvetica'
        )
        
        heading_style = ParagraphStyle(
            'Heading',
            parent=styles['Normal'],
            fontSize=13,
            textColor=colors.black,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold',
            spaceAfter=12,
            spaceBefore=8
        )
        
        # Header Section with Logo and NAAC badge
        logo_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'cmrtc.png')
        naac_logo_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'NAAC.jpg')
        
        # Create header with logos - CMR logo on left, NAAC badge on right with ESTD
        header_left = ''
        header_center = ''
        header_right_content = []
        
        # Left: CMR Logo
        if os.path.exists(logo_path):
            try:
                header_left = RLImage(logo_path, width=1*inch, height=1*inch)
            except:
                header_left = ''
        
        # Center: Title
        header_center = Paragraph("<b>CMR TECHNICAL CAMPUS</b>", title_style)
        
        # Right: ESTD text on top, NAAC Badge below (if available)
        estd_text = Paragraph("<b>ESTD: 2009</b>", estd_style)
        
        if os.path.exists(naac_logo_path):
            try:
                naac_badge = RLImage(naac_logo_path, width=0.7*inch, height=0.7*inch)
                # Create a nested table for right side: ESTD on top, NAAC logo below
                right_table = Table([[estd_text], [naac_badge]], colWidths=[1.3*inch], rowHeights=[0.3*inch, 0.7*inch])
                right_table.setStyle(TableStyle([
                    ('ALIGN', (0, 0), (0, 0), 'RIGHT'),
                    ('ALIGN', (0, 1), (0, 1), 'RIGHT'),
                    ('VALIGN', (0, 0), (0, 0), 'TOP'),
                    ('VALIGN', (0, 1), (0, 1), 'MIDDLE'),
                ]))
                header_right = right_table
            except:
                header_right = estd_text
        else:
            header_right = estd_text
        
        # Create header table: Logo | Title | (ESTD + NAAC Badge)
        header_table = Table(
            [[header_left, header_center, header_right]],
            colWidths=[1.2*inch, 5*inch, 1.3*inch]
        )
        header_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),
            ('ALIGN', (1, 0), (1, 0), 'CENTER'),
            ('ALIGN', (2, 0), (2, 0), 'RIGHT'),
            ('VALIGN', (0, 0), (0, 0), 'MIDDLE'),
            ('VALIGN', (1, 0), (1, 0), 'MIDDLE'),
            ('VALIGN', (2, 0), (2, 0), 'TOP'),
        ]))
        elements.append(header_table)
        elements.append(Spacer(1, 3))
        
        # Title and accreditation info (without repeating title as it's in header)
        elements.append(Paragraph("<b>UGC AUTONOMOUS</b>", subtitle_style))
        elements.append(Paragraph("<b>Accredited by <font color='#d32f2f'>NBA</font> & NAAC with 'A' Grade</b>", accredited_style))
        elements.append(Paragraph("Approved by <b>AICTE, New Delhi</b> and <b>JNTU Hyderabad</b>", approved_style))
        
        # Department name with horizontal lines (underlined effect)
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.black, spaceBefore=0, spaceAfter=5))
        elements.append(Paragraph("<b>Department of CSE [Artificial Intelligence & Machine Learning]</b>", dept_style))
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.black, spaceBefore=5, spaceAfter=10))
        
        # Event name and date row
        current_date = datetime.now().strftime('%B %d, %Y')
        event_date_table = Table(
            [[Paragraph(f"<b>Event Name:</b> {event_name}", event_style), 
              Paragraph(f"<b>Date:</b> {current_date}", event_style)]],
            colWidths=[4.2*inch, 3.3*inch]
        )
        event_date_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),
            ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(event_date_table)
        elements.append(Spacer(1, 12))
        
        # Attendance Report heading
        elements.append(Paragraph("ATTENDANCE REPORT", heading_style))
        elements.append(Spacer(1, 8))
        
        # Prepare table data with Status column
        table_data = [['S.No', 'Student ID', 'Name', 'Email', 'Status']]
        
        # Track row indices for present and absent students
        present_rows = []
        absent_rows = []
        
        for idx, reg in enumerate(registrations, start=1):
            # Determine status
            if reg.has_attended:
                status = 'PRESENT'
                present_rows.append(idx)  # idx is the row number (1-based, +1 for header)
            else:
                status = 'ABSENT'
                absent_rows.append(idx)
            
            table_data.append([
                str(idx),
                reg.student_id,
                reg.name,
                reg.email,
                status
            ])
        
        # Create table with professional styling - adjusted column widths
        table = Table(table_data, colWidths=[0.5*inch, 1*inch, 2.2*inch, 2.3*inch, 1*inch])
        
        # Base table style
        base_style = [
            # Header row styling
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#5b7fbf')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('TOPPADDING', (0, 0), (-1, 0), 10),
            
            # Data rows styling
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('ALIGN', (0, 1), (0, -1), 'CENTER'),
            ('ALIGN', (1, 1), (1, -1), 'CENTER'),
            ('ALIGN', (2, 1), (2, -1), 'LEFT'),
            ('ALIGN', (3, 1), (3, -1), 'LEFT'),
            ('ALIGN', (4, 1), (4, -1), 'CENTER'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('FONTNAME', (4, 1), (4, -1), 'Helvetica-Bold'),  # Bold for Status column
            
            # Borders
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('BOX', (0, 0), (-1, -1), 1.5, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            
            # Padding
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
        ]
        
        # Add color coding for Present rows (green background)
        for row_idx in present_rows:
            base_style.append(('BACKGROUND', (4, row_idx), (4, row_idx), colors.HexColor('#d4edda')))
            base_style.append(('TEXTCOLOR', (4, row_idx), (4, row_idx), colors.HexColor('#155724')))
        
        # Add color coding for Absent rows (red background)
        for row_idx in absent_rows:
            base_style.append(('BACKGROUND', (4, row_idx), (4, row_idx), colors.HexColor('#f8d7da')))
            base_style.append(('TEXTCOLOR', (4, row_idx), (4, row_idx), colors.HexColor('#721c24')))
        
        # Apply the complete style
        table.setStyle(TableStyle(base_style))
        
        elements.append(table)
        elements.append(Spacer(1, 30))
        
        # Footer with HOD and COORDINATOR
        footer_style = ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.black,
            fontName='Helvetica-Bold'
        )
        
        footer_table = Table(
            [[Paragraph("HOD", footer_style), '', Paragraph("COORDINATOR", footer_style)]],
            colWidths=[2*inch, 3.5*inch, 2*inch]
        )
        footer_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),
            ('ALIGN', (2, 0), (2, 0), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(footer_table)
        elements.append(Spacer(1, 30))
        
        # Address footer
        address_style = ParagraphStyle(
            'Address',
            parent=styles['Normal'],
            fontSize=8,
            textColor=colors.black,
            alignment=TA_CENTER,
            fontName='Helvetica'
        )
        
        phone_style = ParagraphStyle(
            'Phone',
            parent=styles['Normal'],
            fontSize=8,
            textColor=colors.HexColor('#d32f2f'),
            alignment=TA_CENTER,
            fontName='Helvetica'
        )
        
        # Add horizontal line
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.black, spaceBefore=1, spaceAfter=8))
        
        elements.append(Paragraph("Kandlakoya (V), Medchal Road, Hyderabad, Telangana – 501401", address_style))
        elements.append(Paragraph("Ph.No: 9247033440/41: www.cmrtc.ac.in", phone_style))
        
        # Build PDF
        doc.build(elements)
        
        # Get PDF data
        buffer.seek(0)
        
        # Create filename with event name
        safe_event_name = "".join(c if c.isalnum() or c in (' ', '_') else '_' for c in event_name).replace(' ', '_')
        
        # Return PDF as file response
        response = FileResponse(
            buffer,
            content_type='application/pdf',
            as_attachment=True,
            filename=f'Attendance_{safe_event_name}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
        )
        
        return response
    
    except Exception as e:
        return JsonResponse({'error': f'Error: {str(e)}'}, status=500)


@api_view(['GET'])
def generate_id_card_pdf(request, registration_id):
    """
    Generate ID card PDF for a registered student
    A7 format (74mm x 105mm) with college logo, student details, and QR code
    """
    try:
        # Get registration details
        registration = get_object_or_404(Registration, id=registration_id)
        event = registration.event
        
        # Create in-memory buffer for PDF
        buffer = io.BytesIO()
        
        # A7 size: 74mm x 105mm (portrait)
        width, height = A7
        
        # Create PDF canvas
        c = canvas.Canvas(buffer, pagesize=A7)
        
        # Draw card border (5mm margin)
        margin = 5 * mm
        c.setStrokeColorRGB(0.2, 0.3, 0.5)  # Dark blue
        c.setLineWidth(2)
        c.rect(margin, margin, width - 2*margin, height - 2*margin, stroke=1, fill=0)
        
        # Current Y position (starting from top)
        y_pos = height - 15 * mm
        
        # Add College Logo at top
        try:
            logo_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'cmrtc.png')
            if os.path.exists(logo_path):
                logo = ImageReader(logo_path)
                logo_size = 20 * mm
                logo_x = (width - logo_size) / 2
                c.drawImage(logo, logo_x, y_pos - logo_size, width=logo_size, height=logo_size, preserveAspectRatio=True, mask='auto')
                y_pos -= logo_size + 5 * mm
        except Exception as e:
            print(f"Logo error: {e}")
            y_pos -= 5 * mm
        
        # Title "EVENT ID CARD"
        c.setFont("Helvetica-Bold", 8)
        c.setFillColorRGB(0.2, 0.3, 0.5)
        title_text = "EVENT ID CARD"
        title_width = c.stringWidth(title_text, "Helvetica-Bold", 8)
        c.drawString((width - title_width) / 2, y_pos, title_text)
        y_pos -= 8 * mm
        
        # Student Name (Bold)
        c.setFont("Helvetica-Bold", 10)
        c.setFillColorRGB(0, 0, 0)
        name_lines = []
        if len(registration.name) > 20:
            # Split long names into multiple lines
            words = registration.name.split()
            line = ""
            for word in words:
                test_line = line + word + " "
                if c.stringWidth(test_line, "Helvetica-Bold", 10) < width - 2*margin - 10*mm:
                    line = test_line
                else:
                    name_lines.append(line.strip())
                    line = word + " "
            if line:
                name_lines.append(line.strip())
        else:
            name_lines = [registration.name]
        
        for name_line in name_lines:
            name_width = c.stringWidth(name_line, "Helvetica-Bold", 10)
            c.drawString((width - name_width) / 2, y_pos, name_line)
            y_pos -= 5 * mm
        
        y_pos -= 2 * mm
        
        # Student ID
        c.setFont("Helvetica", 8)
        c.setFillColorRGB(0.3, 0.3, 0.3)
        student_id_text = f"ID: {registration.student_id}"
        student_id_width = c.stringWidth(student_id_text, "Helvetica", 8)
        c.drawString((width - student_id_width) / 2, y_pos, student_id_text)
        y_pos -= 6 * mm
        
        # Event Name
        c.setFont("Helvetica-Bold", 7)
        c.setFillColorRGB(0.2, 0.3, 0.5)
        event_lines = []
        if len(event.name) > 25:
            # Split long event names
            words = event.name.split()
            line = ""
            for word in words:
                test_line = line + word + " "
                if c.stringWidth(test_line, "Helvetica-Bold", 7) < width - 2*margin - 10*mm:
                    line = test_line
                else:
                    event_lines.append(line.strip())
                    line = word + " "
            if line:
                event_lines.append(line.strip())
        else:
            event_lines = [event.name]
        
        for event_line in event_lines:
            event_width = c.stringWidth(event_line, "Helvetica-Bold", 7)
            c.drawString((width - event_width) / 2, y_pos, event_line)
            y_pos -= 4 * mm
        
        y_pos -= 2 * mm
        
        # Generate QR Code
        try:
            # Decode base64 QR code image
            qr_data = registration.qr_code_image.split(',')[1] if ',' in registration.qr_code_image else registration.qr_code_image
            qr_image_data = base64.b64decode(qr_data)
            qr_image = Image.open(io.BytesIO(qr_image_data))
            
            # Convert to ImageReader for reportlab
            qr_buffer = io.BytesIO()
            qr_image.save(qr_buffer, format='PNG')
            qr_buffer.seek(0)
            qr_reader = ImageReader(qr_buffer)
            
            # Draw QR code (centered)
            qr_size = 25 * mm
            qr_x = (width - qr_size) / 2
            c.drawImage(qr_reader, qr_x, y_pos - qr_size, width=qr_size, height=qr_size)
            y_pos -= qr_size + 3 * mm
        except Exception as e:
            print(f"QR code error: {e}")
            c.setFont("Helvetica", 6)
            c.setFillColorRGB(1, 0, 0)
            error_text = "QR Code Error"
            error_width = c.stringWidth(error_text, "Helvetica", 6)
            c.drawString((width - error_width) / 2, y_pos, error_text)
            y_pos -= 10 * mm
        
        # Registration ID (small text at bottom)
        c.setFont("Helvetica", 5)
        c.setFillColorRGB(0.5, 0.5, 0.5)
        reg_id_text = f"Reg ID: {str(registration.id)[:8].upper()}"
        reg_id_width = c.stringWidth(reg_id_text, "Helvetica", 5)
        c.drawString((width - reg_id_width) / 2, 8 * mm, reg_id_text)
        
        # Save PDF
        c.showPage()
        c.save()
        
        # Get PDF data
        buffer.seek(0)
        
        # Return as downloadable file
        filename = f"ID_Card_{registration.student_id}_{event.name[:20].replace(' ', '_')}.pdf"
        response = FileResponse(
            buffer,
            content_type='application/pdf',
            as_attachment=True,
            filename=filename
        )
        
        return response
        
    except Registration.DoesNotExist:
        return JsonResponse({'error': 'Registration not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': f'Error generating ID card: {str(e)}'}, status=500)
