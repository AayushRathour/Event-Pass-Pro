from django.contrib import admin
from .models import Event, Registration, AttendanceLog


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ['name', 'start_date', 'end_date', 'status', 'registered_count', 'present_count', 'venue']
    list_filter = ['status', 'start_date']
    search_fields = ['name', 'description', 'venue']
    readonly_fields = ['id', 'created_at', 'updated_at', 'registered_count', 'present_count', 'absent_count']
    
    fieldsets = (
        ('Event Information', {
            'fields': ('name', 'description', 'venue', 'status')
        }),
        ('Schedule', {
            'fields': ('start_date', 'end_date')
        }),
        ('Capacity', {
            'fields': ('max_capacity',)
        }),
        ('Statistics', {
            'fields': ('registered_count', 'present_count', 'absent_count'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('id', 'created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Registration)
class RegistrationAdmin(admin.ModelAdmin):
    list_display = ['name', 'student_id', 'email', 'event', 'is_valid', 'has_attended', 'registered_at']
    list_filter = ['is_valid', 'has_attended', 'event', 'registered_at']
    search_fields = ['name', 'student_id', 'email']
    readonly_fields = ['id', 'qr_code_data', 'qr_code_image', 'registered_at', 'scanned_at']
    
    fieldsets = (
        ('Participant Information', {
            'fields': ('name', 'student_id', 'email')
        }),
        ('Event Details', {
            'fields': ('event',)
        }),
        ('QR Code', {
            'fields': ('qr_code_data', 'qr_code_image'),
            'classes': ('collapse',)
        }),
        ('Attendance Status', {
            'fields': ('is_valid', 'has_attended', 'scanned_at')
        }),
        ('Metadata', {
            'fields': ('id', 'registered_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(AttendanceLog)
class AttendanceLogAdmin(admin.ModelAdmin):
    list_display = ['registration', 'scan_time', 'scan_result', 'ip_address']
    list_filter = ['scan_result', 'scan_time']
    search_fields = ['registration__name', 'registration__email', 'ip_address']
    readonly_fields = ['id', 'registration', 'scan_time', 'scan_result', 'ip_address']
    
    def has_add_permission(self, request):
        # Prevent manual creation of attendance logs
        return False
    
    def has_change_permission(self, request, obj=None):
        # Logs should be read-only
        return False
