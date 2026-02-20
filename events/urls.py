from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'events', views.EventViewSet, basename='event')
router.register(r'registrations', views.RegistrationViewSet, basename='registration')

urlpatterns = [
    # API endpoints
    path('api/', include(router.urls)),
    path('api/dashboard/statistics/', views.dashboard_statistics, name='dashboard-statistics'),
    path('api/admin/login/', views.admin_login_view, name='admin-login'),
    path('api/admin/logout/', views.admin_logout_view, name='admin-logout'),
    
    # Template views
    path('', views.index_view, name='index'),
    path('events/', views.events_view, name='events'),
    path('scan/', views.scan_view, name='scan'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('admin-login/', views.admin_login_page, name='admin-login-page'),
    path('admin-register/', views.admin_register_page, name='admin-register-page'),
    path('admin-panel/', views.admin_panel_view, name='admin-panel'),
    path('admin-panel/events/', views.admin_events_view, name='admin-events'),
    path('admin-panel/events/create/', views.admin_create_event, name='admin-create-event'),
    path('admin-panel/events/<uuid:event_id>/edit/', views.admin_edit_event, name='admin-edit-event'),
    path('admin-panel/events/<uuid:event_id>/delete/', views.admin_delete_event, name='admin-delete-event'),
    path('admin-panel/registrations/', views.admin_registrations_view, name='admin-registrations'),
    path('admin-panel/registrations/<uuid:registration_id>/delete/', views.admin_delete_registration, name='admin-delete-registration'),
    path('admin-panel/logs/', views.admin_logs_view, name='admin-logs'),
    path('attendance/download/', views.generate_attendance_pdf, name='attendance-pdf'),
    path('id-card/<uuid:registration_id>/download/', views.generate_id_card_pdf, name='id-card-pdf'),
]
