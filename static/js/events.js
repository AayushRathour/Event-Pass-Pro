// Load all events for the events page
async function loadAllEvents() {
    try {
        const response = await fetch('/api/events/');
        const events = await response.json();
        
        const container = document.getElementById('allEventsContainer');
        
        if (events.length === 0) {
            container.innerHTML = `
                <div style="text-align: center; padding: 3rem; color: #666;">
                    <i class="fas fa-calendar-times" style="font-size: 3rem; margin-bottom: 1rem; opacity: 0.5;"></i>
                    <p style="font-size: 1.1rem;">No events available at the moment</p>
                    <p style="font-size: 0.9rem; margin-top: 0.5rem;">Check back later for upcoming events!</p>
                </div>
            `;
            return;
        }

        // Categorize events
        const now = new Date();
        const runningEvents = [];
        const upcomingEvents = [];
        const completedEvents = [];

        events.forEach(event => {
            const startDate = new Date(event.start_date);
            const endDate = new Date(event.end_date);
            
            if (event.status === 'ongoing' && startDate <= now && endDate >= now) {
                runningEvents.push(event);
            } else if (startDate > now) {
                upcomingEvents.push(event);
            } else {
                completedEvents.push(event);
            }
        });

        let html = '';

        // Running Events Section
        if (runningEvents.length > 0) {
            html += `
                <div class="section-title">
                    <i class="fas fa-circle" style="color: #10b981;"></i> Running Events (${runningEvents.length})
                </div>
                <div class="events-grid">
                    ${runningEvents.map(event => createEventCard(event, 'running')).join('')}
                </div>
            `;
        }

        // Upcoming Events Section
        if (upcomingEvents.length > 0) {
            html += `
                <div class="section-title" style="margin-top: 2rem;">
                    <i class="fas fa-clock" style="color: #f59e0b;"></i> Upcoming Events (${upcomingEvents.length})
                </div>
                <div class="events-grid">
                    ${upcomingEvents.map(event => createEventCard(event, 'upcoming')).join('')}
                </div>
            `;
        }

        // Completed Events Section
        if (completedEvents.length > 0) {
            html += `
                <div class="section-title" style="margin-top: 2rem;">
                    <i class="fas fa-check-circle" style="color: #6b7280;"></i> Completed Events (${completedEvents.length})
                </div>
                <div class="events-grid">
                    ${completedEvents.map(event => createEventCard(event, 'completed')).join('')}
                </div>
            `;
        }

        container.innerHTML = html;

        // Add event listeners to register buttons
        document.querySelectorAll('.register-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const eventId = e.target.dataset.eventId;
                const eventName = e.target.dataset.eventName;
                
                // Redirect to home page with event pre-selected
                window.location.href = `/?event=${eventId}&name=${encodeURIComponent(eventName)}`;
            });
        });

    } catch (error) {
        console.error('Error loading events:', error);
        document.getElementById('allEventsContainer').innerHTML = `
            <div style="text-align: center; padding: 3rem; color: #ef4444;">
                <i class="fas fa-exclamation-triangle" style="font-size: 3rem; margin-bottom: 1rem;"></i>
                <p style="font-size: 1.1rem;">Failed to load events</p>
                <p style="font-size: 0.9rem; margin-top: 0.5rem;">Please try refreshing the page</p>
            </div>
        `;
    }
}

function createEventCard(event, type) {
    const registered = event.registered_count || 0;
    const capacity = event.max_capacity;
    const percentage = capacity > 0 ? (registered / capacity) * 100 : 0;
    const availableSeats = capacity - registered;
    
    const startDate = new Date(event.start_date).toLocaleString('en-US', {
        month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit'
    });
    const endDate = new Date(event.end_date).toLocaleString('en-US', {
        month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit'
    });

    let statusBadge = '';
    let buttonHtml = '';

    if (type === 'running') {
        statusBadge = '<span class="event-status-badge live"><i class="fas fa-circle"></i> LIVE NOW</span>';
        buttonHtml = `<button class="register-btn primary" data-event-id="${event.id}" data-event-name="${event.name}">
            <i class="fas fa-ticket-alt"></i> Register Now
        </button>`;
    } else if (type === 'upcoming') {
        statusBadge = '<span class="event-status-badge upcoming"><i class="fas fa-clock"></i> UPCOMING</span>';
        buttonHtml = `<button class="register-btn secondary" data-event-id="${event.id}" data-event-name="${event.name}">
            <i class="fas fa-calendar-plus"></i> Pre-Register
        </button>`;
    } else {
        statusBadge = '<span class="event-status-badge completed"><i class="fas fa-check-circle"></i> COMPLETED</span>';
        buttonHtml = `<button class="register-btn disabled" disabled>
            <i class="fas fa-lock"></i> Closed
        </button>`;
    }

    return `
        <div class="event-card">
            <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 1rem;">
                <h3 style="margin: 0; font-size: 1.5rem; color: #1f2937;">
                    <i class="fas fa-calendar-alt" style="color: var(--primary-color);"></i> ${event.name}
                </h3>
                ${statusBadge}
            </div>
            
            <p class="event-description"><i class="fas fa-info-circle"></i> ${event.description || 'No description available'}</p>
            
            <div style="margin: 1rem 0; padding: 1rem; background: #f9fafb; border-radius: 8px;">
                <p style="margin: 0.5rem 0; color: #4b5563; display: flex; align-items: center;">
                    <i class="fas fa-map-marker-alt" style="width: 20px; color: var(--primary-color);"></i>
                    <strong>Venue:</strong>&nbsp;${event.venue}
                </p>
                <p style="margin: 0.5rem 0; color: #4b5563; display: flex; align-items: center;">
                    <i class="fas fa-play-circle" style="width: 20px; color: var(--primary-color);"></i>
                    <strong>Starts:</strong>&nbsp;${startDate}
                </p>
                <p style="margin: 0.5rem 0; color: #4b5563; display: flex; align-items: center;">
                    <i class="fas fa-stop-circle" style="width: 20px; color: var(--primary-color);"></i>
                    <strong>Ends:</strong>&nbsp;${endDate}
                </p>
            </div>

            <div class="capacity-info">
                <div class="capacity-header">
                    <span><i class="fas fa-users"></i> Capacity</span>
                    <span><strong>${registered}</strong> / ${capacity}</span>
                </div>
                <div class="capacity-bar">
                    <div class="capacity-fill" style="width: ${percentage}%"></div>
                </div>
                <p style="text-align: center; margin-top: 0.5rem; font-size: 0.9rem; color: ${availableSeats > 0 ? '#10b981' : '#ef4444'}; font-weight: 600;">
                    <i class="fas fa-chair"></i> ${availableSeats > 0 ? `${availableSeats} seats available` : 'Full capacity reached'}
                </p>
            </div>

            ${buttonHtml}
        </div>
    `;
}

// Load events when page loads
document.addEventListener('DOMContentLoaded', loadAllEvents);
