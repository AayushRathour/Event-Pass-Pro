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
import subprocess
import tempfile
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
from reportlab.lib.pagesizes import A7
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
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
    """Generate attendance PDF using template with proper table data insertion"""
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
        
        # Load the user's template (which has logos and formatting)
        template_path = os.path.join(
            settings.BASE_DIR, 
            'events', 
            'docx_templates', 
            'CSE_AIML_Attendance_Template_Updated.docx'
        )
        
        if not os.path.exists(template_path):
            return JsonResponse({'error': 'Template file not found'}, status=404)
        
        # Create temporary directory for file operations
        temp_dir = tempfile.mkdtemp()
        
        try:
            # Load template as Document
            doc = Document(template_path)
            
            # Update Event Name and Date in the document
            current_date = datetime.now().strftime('%B %d, %Y')
            
            # Replace placeholders in paragraphs
            for paragraph in doc.paragraphs:
                # Replace {{ event_name }} placeholder
                if '{{ event_name }}' in paragraph.text:
                    paragraph.text = paragraph.text.replace('{{ event_name }}', event_name)
                if '{{ date }}' in paragraph.text:
                    paragraph.text = paragraph.text.replace('{{ date }}', current_date)
                
                # Also check for variations
                # Replace "Event:" or "Event Name:" labels
                if 'Event:' in paragraph.text and event_name not in paragraph.text:
                    paragraph.text = paragraph.text.replace('Event:', f'Event: {event_name}')
                elif 'Event Name:' in paragraph.text and event_name not in paragraph.text:
                    paragraph.text = paragraph.text.replace('Event Name:', f'Event Name: {event_name}')
                # Also handle old Ref. No: if it exists in template
                elif 'Ref. No:' in paragraph.text:
                    paragraph.text = paragraph.text.replace('Ref. No:', f'Event: {event_name}')
                
                if 'Date:' in paragraph.text and '2026' not in paragraph.text:
                    for run in paragraph.runs:
                        if 'Date:' in run.text:
                            run.text = f'Date: {current_date}'
            
            # Find the attendance table (should have 5 columns)
            attendance_table = None
            for table in doc.tables:
                if len(table.columns) == 5:
                    # Check if it has the correct headers
                    first_row_text = [cell.text.strip() for cell in table.rows[0].cells]
                    if 'S.No' in first_row_text or 'Student ID' in first_row_text:
                        attendance_table = table
                        break
            
            if not attendance_table:
                import shutil
                shutil.rmtree(temp_dir, ignore_errors=True)
                return JsonResponse({'error': 'Could not find attendance table in template'}, status=500)
            
            # Clear existing data rows (keep only header row)
            # Remove all rows except the first one (header)
            while len(attendance_table.rows) > 1:
                attendance_table._element.remove(attendance_table.rows[-1]._element)
            
            # Add student data rows
            for idx, reg in enumerate(registrations, start=1):
                # Add new row
                row = attendance_table.add_row()
                row.cells[0].text = str(idx)
                row.cells[1].text = reg.student_id
                row.cells[2].text = reg.name
                row.cells[3].text = reg.email
                row.cells[4].text = str(reg.id)[:8].upper()
                
                # Format the cells
                for cell in row.cells:
                    for paragraph in cell.paragraphs:
                        for run in paragraph.runs:
                            run.font.size = Pt(10)
            
            # Save the modified document
            temp_docx = os.path.join(temp_dir, 'attendance_report.docx')
            doc.save(temp_docx)
            
            # Convert DOCX to PDF using LibreOffice
            temp_pdf = os.path.join(temp_dir, 'attendance_report.pdf')
            
            # Find LibreOffice executable
            import shutil as sh
            soffice_cmd = None
            
            # Try to find in PATH first
            soffice_in_path = sh.which('soffice')
            if soffice_in_path:
                soffice_cmd = soffice_in_path
            else:
                # Check common Windows installation paths
                common_paths = [
                    r'C:\Program Files\LibreOffice\program\soffice.exe',
                    r'C:\Program Files (x86)\LibreOffice\program\soffice.exe',
                ]
                
                # Also check in PROGRAMFILES environment variables
                if 'PROGRAMFILES' in os.environ:
                    common_paths.append(os.path.join(os.environ['PROGRAMFILES'], 'LibreOffice', 'program', 'soffice.exe'))
                if 'PROGRAMFILES(X86)' in os.environ:
                    common_paths.append(os.path.join(os.environ['PROGRAMFILES(X86)'], 'LibreOffice', 'program', 'soffice.exe'))
                
                for path in common_paths:
                    if os.path.exists(path):
                        soffice_cmd = path
                        break
            
            if not soffice_cmd:
                import shutil
                shutil.rmtree(temp_dir, ignore_errors=True)
                return JsonResponse({
                    'error': 'LibreOffice not found. Please install LibreOffice from https://www.libreoffice.org/download/',
                    'note': 'After installation, restart your computer or add LibreOffice to system PATH.'
                }, status=500)
            
            # Run LibreOffice conversion
            try:
                result = subprocess.run(
                    [
                        soffice_cmd,
                        '--headless',
                        '--convert-to',
                        'pdf',
                        '--outdir',
                        temp_dir,
                        temp_docx
                    ],
                    capture_output=True,
                    text=True,
                    timeout=60,
                    cwd=temp_dir
                )
            except FileNotFoundError:
                import shutil
                shutil.rmtree(temp_dir, ignore_errors=True)
                return JsonResponse({
                    'error': f'LibreOffice executable not accessible: {soffice_cmd}',
                    'note': 'Please restart your computer after installing LibreOffice.'
                }, status=500)
            except Exception as e:
                import shutil
                shutil.rmtree(temp_dir, ignore_errors=True)
                return JsonResponse({
                    'error': f'Error running LibreOffice: {str(e)}'
                }, status=500)
            
            # Check if conversion was successful
            if not os.path.exists(temp_pdf):
                import shutil
                shutil.rmtree(temp_dir, ignore_errors=True)
                return JsonResponse({
                    'error': 'PDF conversion failed. Please ensure LibreOffice is installed.',
                    'details': result.stderr
                }, status=500)
            
            # Create filename with event name
            safe_event_name = "".join(c if c.isalnum() or c in (' ', '_') else '_' for c in event_name).replace(' ', '_')
            
            # Return PDF as file response
            response = FileResponse(
                open(temp_pdf, 'rb'),
                content_type='application/pdf',
                as_attachment=True,
                filename=f'Attendance_{safe_event_name}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
            )
            
            # Schedule cleanup after response is sent
            def cleanup():
                try:
                    import shutil
                    shutil.rmtree(temp_dir, ignore_errors=True)
                except:
                    pass
            
            # Register cleanup callback
            response.close = cleanup
            
            return response
            
        except subprocess.TimeoutExpired:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
            return JsonResponse({'error': 'PDF conversion timed out'}, status=500)
        
        except Exception as e:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
            return JsonResponse({'error': f'Error generating PDF: {str(e)}'}, status=500)
    
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
