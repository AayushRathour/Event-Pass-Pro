// API base URL
const API_BASE = '';

// Carousel functionality
let currentSlideIndex = 0;
let autoSlideInterval;

// Initialize carousel on page load
document.addEventListener('DOMContentLoaded', function() {
    // Start auto-slide
    startAutoSlide();
    
    // Pause auto-slide on hover
    const carouselContainer = document.querySelector('.carousel-container');
    if (carouselContainer) {
        carouselContainer.addEventListener('mouseenter', () => {
            clearInterval(autoSlideInterval);
        });
        
        carouselContainer.addEventListener('mouseleave', () => {
            startAutoSlide();
        });
    }
    
    // Initialize EmailJS with your Public Key (wait for EmailJS to load)
    if (typeof emailjs !== 'undefined') {
        emailjs.init("LW8AvJdD_7yUt0D9M");
        console.log("✅ EmailJS initialized");
    } else {
        console.error("❌ EmailJS library not loaded");
    }
    
    loadQuickRunningEvents();
    loadEventOptions();
    
    // Check if event was pre-selected from events page
    const urlParams = new URLSearchParams(window.location.search);
    const eventId = urlParams.get('event');
    if (eventId) {
        // Wait a bit for the dropdown to populate
        setTimeout(() => {
            const eventSelect = document.getElementById('event');
            eventSelect.value = eventId;
            eventSelect.scrollIntoView({ behavior: 'smooth', block: 'center' });
            eventSelect.focus();
        }, 500);
    }
});

// Move to next/previous slide
function moveSlide(direction) {
    const slides = document.querySelectorAll('.carousel-slide');
    const dots = document.querySelectorAll('.carousel-dot');
    
    if (slides.length === 0) return;
    
    // Remove active class from current slide and dot
    slides[currentSlideIndex].classList.remove('active');
    dots[currentSlideIndex].classList.remove('active');
    
    // Calculate new index
    currentSlideIndex += direction;
    
    // Wrap around
    if (currentSlideIndex >= slides.length) {
        currentSlideIndex = 0;
    } else if (currentSlideIndex < 0) {
        currentSlideIndex = slides.length - 1;
    }
    
    // Add active class to new slide and dot
    slides[currentSlideIndex].classList.add('active');
    dots[currentSlideIndex].classList.add('active');
}

// Jump to specific slide
function currentSlide(index) {
    const slides = document.querySelectorAll('.carousel-slide');
    const dots = document.querySelectorAll('.carousel-dot');
    
    if (slides.length === 0) return;
    
    // Remove active class from current slide and dot
    slides[currentSlideIndex].classList.remove('active');
    dots[currentSlideIndex].classList.remove('active');
    
    // Set new index
    currentSlideIndex = index;
    
    // Add active class to new slide and dot
    slides[currentSlideIndex].classList.add('active');
    dots[currentSlideIndex].classList.add('active');
}

// Auto-slide functionality
function startAutoSlide() {
    autoSlideInterval = setInterval(() => {
        moveSlide(1);
    }, 3000); // Change slide every 3 seconds
}

// Load running events in compact format for homepage
async function loadQuickRunningEvents() {
    try {
        const response = await fetch(`${API_BASE}/api/events/`);
        const events = await response.json();
        
        const eventsContainer = document.getElementById('runningEventsQuick');
        
        // Filter only running events
        const now = new Date();
        const runningEvents = events.filter(event => {
            const startDate = new Date(event.start_date);
            const endDate = new Date(event.end_date);
            return event.status === 'ongoing' && startDate <= now && endDate >= now;
        });
        
        if (runningEvents.length === 0) {
            eventsContainer.innerHTML = `
                <div style="grid-column: 1/-1; text-align: center; padding: 2rem; background: #f9fafb; border-radius: 12px;">
                    <i class="fas fa-calendar-times" style="font-size: 2rem; color: #9ca3af; margin-bottom: 1rem;"></i>
                    <p style="color: #6b7280; margin: 0;">No events currently running</p>
                    <a href="/events/" style="color: var(--primary-color); text-decoration: none; font-weight: 500; display: inline-block; margin-top: 0.5rem;">
                        <i class="fas fa-arrow-right"></i> Check upcoming events
                    </a>
                </div>
            `;
            return;
        }
        
        // Show max 3 running events on homepage
        const displayEvents = runningEvents.slice(0, 3);
        
        let html = displayEvents.map(event => createQuickEventCard(event)).join('');
        
        if (runningEvents.length > 3) {
            html += `
                <div style="grid-column: 1/-1; text-align: center; padding: 1.5rem; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 12px; color: white;">
                    <p style="margin: 0 0 1rem 0; font-size: 1.1rem; font-weight: 600;">
                        <i class="fas fa-plus-circle"></i> ${runningEvents.length - 3} more events running
                    </p>
                    <a href="/events/" class="view-all-link" style="color: white; text-decoration: none; font-weight: 600; padding: 0.75rem 1.5rem; background: rgba(255,255,255,0.2); border-radius: 8px; display: inline-block; transition: all 0.3s;">
                        <i class="fas fa-list"></i> View All Events
                    </a>
                </div>
            `;
        }
        
        eventsContainer.innerHTML = html;
        
        // Add click handlers to quick register buttons
        document.querySelectorAll('.quick-register-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const eventId = e.target.dataset.eventId;
                const eventSelect = document.getElementById('event');
                eventSelect.value = eventId;
                eventSelect.scrollIntoView({ behavior: 'smooth', block: 'center' });
                eventSelect.focus();
            });
        });
        
    } catch (error) {
        console.error('Error loading events:', error);
        document.getElementById('runningEventsQuick').innerHTML = '<p style="text-align: center; color: #dc3545;">Error loading events</p>';
    }
}

// Create compact event card for homepage
function createQuickEventCard(event) {
    const availableSeats = event.max_capacity - event.registered_count;
    const capacityPercentage = (event.registered_count / event.max_capacity * 100).toFixed(0);
    
    return `
        <div class="event-card-quick">
            <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 0.75rem;">
                <h3 style="margin: 0; font-size: 1.2rem; color: #1f2937;">
                    <i class="fas fa-calendar-alt" style="color: var(--primary-color);"></i> ${event.name}
                </h3>
                <span class="event-status-badge live" style="font-size: 0.75rem;">
                    <i class="fas fa-circle"></i> LIVE
                </span>
            </div>
            
            <p style="margin: 0.5rem 0; color: #6b7280; font-size: 0.9rem;">
                <i class="fas fa-map-marker-alt" style="color: var(--primary-color); width: 16px;"></i> ${event.venue}
            </p>
            
            <div style="margin: 0.75rem 0;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.25rem; font-size: 0.85rem;">
                    <span style="color: #6b7280;"><i class="fas fa-users"></i> ${event.registered_count}/${event.max_capacity}</span>
                    <span style="color: ${availableSeats > 10 ? '#10b981' : availableSeats > 0 ? '#f59e0b' : '#ef4444'}; font-weight: 600;">
                        ${availableSeats} seats left
                    </span>
                </div>
                <div class="capacity-bar" style="height: 6px;">
                    <div class="capacity-fill" style="width: ${capacityPercentage}%; height: 6px;"></div>
                </div>
            </div>
            
            <button class="quick-register-btn" data-event-id="${event.id}">
                <i class="fas fa-ticket-alt"></i> Register Now
            </button>
        </div>
    `;
}

// Load events for dropdown
async function loadEventOptions() {
    try {
        const response = await fetch(`${API_BASE}/api/events/`);
        const events = await response.json();
        
        const eventSelect = document.getElementById('event');
        eventSelect.innerHTML = '<option value="">Choose an event...</option>' +
            events.map(event => `
                <option value="${event.id}">${event.name} - ${new Date(event.start_date).toLocaleDateString()}</option>
            `).join('');
    } catch (error) {
        console.error('Error loading event options:', error);
    }
}

// Select event from running events section
function selectEvent(eventId) {
    document.getElementById('event').value = eventId;
    document.getElementById('gatePassForm').scrollIntoView({ behavior: 'smooth' });
}

// Handle form submission
document.getElementById("gatePassForm").addEventListener("submit", async function(e) {
    e.preventDefault();

    const eventId = document.getElementById("event").value;
    const name = document.getElementById("name").value;
    const studentId = document.getElementById("id").value;
    const email = document.getElementById("email").value;

    if (!eventId) {
        alert("Please select an event");
        return;
    }

    try {
        // Create registration via API
        const response = await fetch(`${API_BASE}/api/registrations/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({
                event: eventId,
                name: name,
                student_id: studentId,
                email: email
            })
        });

        const data = await response.json();

        if (response.ok) {
            // Send email using EmailJS (your working frontend method)
            let emailSentViaEmailJS = false;
            const qrContainer = document.getElementById("qrcode");
            
            // Show loading state
            qrContainer.innerHTML = `
                <div class="qr-success">
                    <i class="fas fa-spinner fa-spin" style="font-size: 2rem; color: var(--primary-color);"></i>
                    <p style="margin-top: 1rem;">Sending confirmation email...</p>
                </div>
            `;
            
            try {
                // Get event details for email
                const eventResponse = await fetch(`${API_BASE}/api/events/${eventId}/`);
                const eventData = await eventResponse.json();
                
                // CMR Technical Campus Logo - Using a working public URL
                // IMPORTANT: Replace this with your actual uploaded CMR logo URL from imgbb.com or imgur.com
                const collegeLogoUrl = 'https://i.postimg.cc/9FLqJd5t/cmrtc.png'; // Temporary CMR logo - REPLACE with your upload
                
                const collegeName = 'CMR TECHNICAL CAMPUS';
                const collegeTagline = 'EXPLORE TO INVENT';
                
                console.log("📧 Sending email with logo URL:", collegeLogoUrl);
                
                // Send via EmailJS
                await emailjs.send("service_4noajtf", "template_eh5mdow", {
                    name: name,
                    id: studentId,
                    email: email,
                    qr_code: data.qr_code_image,
                    college_logo: collegeLogoUrl,
                    college_name: collegeName,
                    college_tagline: collegeTagline,
                    event_name: eventData.name || 'Event',
                    event_venue: eventData.venue || 'TBA',
                    event_date: new Date(eventData.start_date).toLocaleString() || 'TBA'
                });
                emailSentViaEmailJS = true;
                console.log("✅ Email sent successfully via EmailJS to:", email);
            } catch (emailError) {
                console.error("❌ EmailJS failed:", emailError);
                emailSentViaEmailJS = false;
            }
            
            // Display QR code with email status
            const emailStatus = emailSentViaEmailJS
                ? '<p style="color: #10b981; font-size: 0.9rem; font-weight: 600;"><i class="fas fa-check-circle"></i> Confirmation email sent to ' + email + '</p>'
                : '<p style="color: #f59e0b; font-size: 0.9rem;"><i class="fas fa-exclamation-triangle"></i> Email delivery failed. Please save this QR code.</p>';
            
            qrContainer.innerHTML = `
                <div class="qr-success">
                    <i class="fas fa-check-circle"></i>
                    <h3>Registration Successful!</h3>
                    <p>Your gate pass has been generated</p>
                    ${emailStatus}
                    <img src="${data.qr_code_image}" alt="QR Code" style="max-width: 300px; margin: 1rem auto; display: block; border: 2px solid #e0e0e0; border-radius: 10px; padding: 15px; background: white;">
                    <p><strong>Registration ID:</strong> ${data.id}</p>
                    <p style="color: #666; font-size: 0.9rem;">
                        <i class="fas fa-info-circle"></i> This QR code is valid for single entry only
                    </p>
                    <div style="margin-top: 1rem; display: flex; gap: 1rem; justify-content: center; flex-wrap: wrap;">
                        <button onclick="downloadIDCard('${data.id}', '${name}')" class="submit-btn" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);">
                            <i class="fas fa-id-card"></i> Download ID Card
                        </button>
                        <button onclick="downloadQR('${data.qr_code_image}', '${name}')" class="submit-btn" style="background: linear-gradient(135deg, #10b981 0%, #059669 100%);">
                            <i class="fas fa-download"></i> Download QR Code
                        </button>
                    </div>
                    <div id="download-status" style="margin-top: 1rem;"></div>
                </div>
            `;
            
            // Scroll to QR code
            qrContainer.scrollIntoView({ behavior: 'smooth' });
            
            // Reset form
            document.getElementById("gatePassForm").reset();
            
        } else {
            alert(`Error: ${data.error || 'Registration failed. You may already be registered for this event.'}`);
        }
    } catch (error) {
        console.error('Error:', error);
        alert('An error occurred during registration. Please try again.');
    }
});

// Download QR code as image
function downloadQR(qrCodeImage, name) {
    const link = document.createElement('a');
    link.href = qrCodeImage;
    link.download = `event-pass-${name.replace(/\s+/g, '-')}.png`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

// Print only the QR code pass section
function printPass() {
    // Add print-ready class to body
    document.body.classList.add('printing');
    
    // Trigger print
    window.print();
    
    // Remove class after printing
    setTimeout(() => {
        document.body.classList.remove('printing');
    }, 1000);
}

// Download ID Card PDF
async function downloadIDCard(registrationId, name) {
    const statusDiv = document.getElementById('download-status');
    
    try {
        // Show loading message
        if (statusDiv) {
            statusDiv.innerHTML = '<p style="color: #667eea; font-size: 0.9rem;"><i class="fas fa-spinner fa-spin"></i> Generating ID Card PDF...</p>';
        }
        
        // Call backend API to get ID card PDF
        const response = await fetch(`${API_BASE}/id-card/${registrationId}/download/`);
        
        if (!response.ok) {
            throw new Error('Failed to generate ID card');
        }
        
        // Get the PDF blob
        const blob = await response.blob();
        
        // Create download link
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `ID_Card_${name.replace(/\s+/g, '_')}.pdf`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        // Clean up the URL object
        window.URL.revokeObjectURL(url);
        
        // Show success message
        if (statusDiv) {
            statusDiv.innerHTML = '<p style="color: #10b981; font-size: 0.9rem; font-weight: 600;"><i class="fas fa-check-circle"></i> ID Card downloaded successfully!</p>';
            
            // Clear message after 5 seconds
            setTimeout(() => {
                statusDiv.innerHTML = '';
            }, 5000);
        }
        
    } catch (error) {
        console.error('Error downloading ID card:', error);
        
        // Show error message
        if (statusDiv) {
            statusDiv.innerHTML = '<p style="color: #f5576c; font-size: 0.9rem;"><i class="fas fa-exclamation-circle"></i> Failed to download ID card. Please try again.</p>';
            
            // Clear message after 5 seconds
            setTimeout(() => {
                statusDiv.innerHTML = '';
            }, 5000);
        }
    }
}

// Get CSRF token
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

// Function to convert image to base64
function getLogoBase64() {
    return new Promise((resolve, reject) => {
        const img = new Image();
        img.crossOrigin = 'Anonymous';
        img.onload = function() {
            const canvas = document.createElement('canvas');
            canvas.width = img.width;
            canvas.height = img.height;
            const ctx = canvas.getContext('2d');
            ctx.drawImage(img, 0, 0);
            try {
                const dataURL = canvas.toDataURL('image/png');
                resolve(dataURL);
            } catch (e) {
                reject(e);
            }
        };
        img.onerror = function() {
            reject(new Error('Failed to load logo'));
        };
        // Try to load the logo from static directory
        img.src = '/static/images/cmrtc.png';
    });
}
