from django.db import models
from django.contrib.auth.models import User
import uuid
from django.utils import timezone


class Event(models.Model):
    """Model for managing events"""
    STATUS_CHOICES = [
        ('upcoming', 'Upcoming'),
        ('ongoing', 'Ongoing'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    description = models.TextField()
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    venue = models.CharField(max_length=200)
    max_capacity = models.IntegerField(default=100)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='upcoming')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='events_created')
    
    class Meta:
        ordering = ['-start_date']
    
    def __str__(self):
        return self.name
    
    @property
    def is_active(self):
        """Check if event is currently running"""
        now = timezone.now()
        return self.start_date <= now <= self.end_date and self.status == 'ongoing'
    
    @property
    def registered_count(self):
        """Count of registered participants"""
        return self.registrations.count()
    
    @property
    def present_count(self):
        """Count of participants who attended"""
        return self.registrations.filter(has_attended=True).count()
    
    @property
    def absent_count(self):
        """Count of registered but not attended"""
        return self.registered_count - self.present_count


class Registration(models.Model):
    """Model for event registrations"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='registrations')
    name = models.CharField(max_length=200)
    student_id = models.CharField(max_length=50)
    email = models.EmailField()
    qr_code_data = models.TextField(unique=True)  # Encrypted QR data
    qr_code_image = models.TextField(blank=True)  # Base64 encoded QR image
    is_valid = models.BooleanField(default=True)  # Single-use validation
    has_attended = models.BooleanField(default=False)
    registered_at = models.DateTimeField(auto_now_add=True)
    scanned_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-registered_at']
        unique_together = ['event', 'email']
    
    def __str__(self):
        return f"{self.name} - {self.event.name}"
    
    def mark_as_scanned(self):
        """Mark QR code as used (invalid after first scan)"""
        if self.is_valid:
            self.is_valid = False
            self.has_attended = True
            self.scanned_at = timezone.now()
            self.save()
            return True
        return False


class AttendanceLog(models.Model):
    """Model for tracking all scan attempts"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    registration = models.ForeignKey(Registration, on_delete=models.CASCADE, related_name='scan_logs')
    scan_time = models.DateTimeField(auto_now_add=True)
    scan_result = models.CharField(max_length=20, choices=[
        ('success', 'Success'),
        ('already_used', 'Already Used'),
        ('invalid', 'Invalid'),
    ])
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    class Meta:
        ordering = ['-scan_time']
    
    def __str__(self):
        return f"{self.registration.name} - {self.scan_result} at {self.scan_time}"
