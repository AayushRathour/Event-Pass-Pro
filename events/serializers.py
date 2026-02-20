from rest_framework import serializers
from .models import Event, Registration, AttendanceLog


class EventSerializer(serializers.ModelSerializer):
    registered_count = serializers.IntegerField(read_only=True)
    present_count = serializers.IntegerField(read_only=True)
    absent_count = serializers.IntegerField(read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Event
        fields = [
            'id', 'name', 'description', 'start_date', 'end_date',
            'venue', 'max_capacity', 'status', 'created_at', 'updated_at',
            'registered_count', 'present_count', 'absent_count', 'is_active'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class RegistrationSerializer(serializers.ModelSerializer):
    event_name = serializers.CharField(source='event.name', read_only=True)
    
    class Meta:
        model = Registration
        fields = [
            'id', 'event', 'event_name', 'name', 'student_id', 'email',
            'is_valid', 'has_attended', 'registered_at', 'scanned_at'
        ]
        read_only_fields = ['id', 'is_valid', 'has_attended', 'registered_at', 'scanned_at']


class RegistrationCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new registrations"""
    class Meta:
        model = Registration
        fields = ['event', 'name', 'student_id', 'email']


class AttendanceLogSerializer(serializers.ModelSerializer):
    registration_name = serializers.CharField(source='registration.name', read_only=True)
    registration_email = serializers.CharField(source='registration.email', read_only=True)
    
    class Meta:
        model = AttendanceLog
        fields = [
            'id', 'registration', 'registration_name', 'registration_email',
            'scan_time', 'scan_result', 'ip_address'
        ]
        read_only_fields = ['id', 'scan_time']


class EventStatisticsSerializer(serializers.Serializer):
    """Serializer for dashboard statistics"""
    total_events = serializers.IntegerField()
    active_events = serializers.IntegerField()
    total_registrations = serializers.IntegerField()
    total_present = serializers.IntegerField()
    total_absent = serializers.IntegerField()
    attendance_rate = serializers.FloatField()
