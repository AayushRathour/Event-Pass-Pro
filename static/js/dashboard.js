// API base URL
const API_BASE = '';
let attendanceChart = null;

document.addEventListener('DOMContentLoaded', function() {
    loadDashboardData();
    loadEventsList();
});

async function loadDashboardData() {
    try {
        const response = await fetch(`${API_BASE}/api/dashboard/statistics/`, {
            credentials: 'include'
        });
        
        if (!response.ok) {
            if (response.status === 401 || response.status === 403) {
                window.location.href = '/admin-login/';
                return;
            }
            throw new Error('Failed to load statistics');
        }
        
        const data = await response.json();
        
        // Update stat cards
        document.getElementById('totalEvents').textContent = data.total_events;
        document.getElementById('totalRegistrations').textContent = data.total_registrations;
        document.getElementById('totalPresent').textContent = data.total_present;
        document.getElementById('totalAbsent').textContent = data.total_absent;
        
        // Create pie chart
        createAttendanceChart(data);
        
    } catch (error) {
        console.error('Error loading dashboard data:', error);
        alert('Error loading dashboard data. Please refresh the page.');
    }
}

function createAttendanceChart(data) {
    const ctx = document.getElementById('attendanceChart').getContext('2d');
    
    // Destroy existing chart if it exists
    if (attendanceChart) {
        attendanceChart.destroy();
    }
    
    attendanceChart = new Chart(ctx, {
        type: 'pie',
        data: {
            labels: ['Present', 'Absent', 'Registered (Not Yet Attended)'],
            datasets: [{
                data: [data.total_present, data.total_absent, data.total_registrations - data.total_present - data.total_absent],
                backgroundColor: [
                    '#4facfe',  // Blue for Present
                    '#fa709a',  // Pink/Red for Absent
                    '#f5f5f5'   // Gray for not yet attended
                ],
                borderColor: [
                    '#4facfe',
                    '#fa709a',
                    '#ddd'
                ],
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        padding: 20,
                        font: {
                            size: 14,
                            family: 'Poppins'
                        }
                    }
                },
                title: {
                    display: true,
                    text: `Overall Attendance Rate: ${data.attendance_rate}%`,
                    font: {
                        size: 16,
                        family: 'Poppins',
                        weight: 'bold'
                    },
                    padding: 20
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const label = context.label || '';
                            const value = context.parsed || 0;
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = ((value / total) * 100).toFixed(1);
                            return `${label}: ${value} (${percentage}%)`;
                        }
                    }
                }
            }
        }
    });
}

async function loadEventsList() {
    try {
        const response = await fetch(`${API_BASE}/api/events/`);
        const events = await response.json();
        
        const eventsList = document.getElementById('eventsList');
        
        if (events.length === 0) {
            eventsList.innerHTML = '<p style="text-align: center; color: #666;">No events found</p>';
            return;
        }
        
        eventsList.innerHTML = events.map(event => {
            const attendanceRate = event.registered_count > 0 
                ? ((event.present_count / event.registered_count) * 100).toFixed(1)
                : 0;
            
            let statusBadge = '';
            if (event.status === 'ongoing') {
                statusBadge = '<span class="badge badge-success"><i class="fas fa-circle"></i> Ongoing</span>';
            } else if (event.status === 'upcoming') {
                statusBadge = '<span class="badge badge-primary">Upcoming</span>';
            } else {
                statusBadge = '<span class="badge badge-secondary">Completed</span>';
            }
            
            return `
                <div class="event-item">
                    <div>
                        <h3 style="margin: 0 0 0.5rem 0;">${event.name}</h3>
                        <p style="margin: 0; color: #666; font-size: 0.9rem;">
                            <i class="fas fa-map-marker-alt"></i> ${event.venue} | 
                            <i class="fas fa-calendar"></i> ${new Date(event.start_date).toLocaleDateString()}
                        </p>
                    </div>
                    <div style="text-align: right;">
                        ${statusBadge}
                        <div class="event-stats" style="margin-top: 0.5rem;">
                            <span title="Registered"><i class="fas fa-users"></i> ${event.registered_count}</span>
                            <span title="Present"><i class="fas fa-user-check" style="color: #4facfe;"></i> ${event.present_count}</span>
                            <span title="Absent"><i class="fas fa-user-times" style="color: #fa709a;"></i> ${event.absent_count}</span>
                            <span title="Attendance Rate"><i class="fas fa-percentage"></i> ${attendanceRate}%</span>
                        </div>
                    </div>
                </div>
            `;
        }).join('');
        
    } catch (error) {
        console.error('Error loading events list:', error);
        document.getElementById('eventsList').innerHTML = '<p style="text-align: center; color: #dc3545;">Error loading events</p>';
    }
}

async function logout() {
    try {
        const response = await fetch(`${API_BASE}/api/admin/logout/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            },
            credentials: 'include'
        });
        
        if (response.ok) {
            window.location.href = '/admin-login/';
        }
    } catch (error) {
        console.error('Error logging out:', error);
        window.location.href = '/admin-login/';
    }
}

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}
