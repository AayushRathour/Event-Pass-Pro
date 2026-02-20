// Initialize QR Scanner
let html5QrCode;
let scanCount = 0;
const API_BASE = '';

document.addEventListener('DOMContentLoaded', function() {
    initializeScanner();
});

function initializeScanner() {
    html5QrCode = new Html5Qrcode("reader");
    
    const config = {
        fps: 10,
        qrbox: { width: 250, height: 250 }
    };
    
    html5QrCode.start(
        { facingMode: "environment" },
        config,
        onScanSuccess,
        onScanError
    ).catch(err => {
        console.error('Error starting scanner:', err);
        // Fallback to file input if camera fails
        showFileInput();
    });
}

async function onScanSuccess(decodedText, decodedResult) {
    console.log(`Scan result: ${decodedText}`);
    
    // Pause scanning to prevent multiple scans
    html5QrCode.pause();
    
    // Verify QR code with backend
    try {
        const response = await fetch(`${API_BASE}/api/registrations/verify_qr/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({
                qr_data: decodedText
            })
        });
        
        const data = await response.json();
        
        displayScanResult(data);
        
        if (data.valid && data.scan_result === 'success') {
            scanCount++;
            document.getElementById('scanCount').textContent = scanCount;
        }
        
        // Resume scanning after 3 seconds
        setTimeout(() => {
            html5QrCode.resume();
            document.getElementById('scanResult').style.display = 'none';
        }, 3000);
        
    } catch (error) {
        console.error('Error verifying QR code:', error);
        showError('Failed to verify QR code. Please try again.');
        setTimeout(() => {
            html5QrCode.resume();
        }, 2000);
    }
}

function onScanError(errorMessage) {
    // Ignore scan errors (they're frequent when no QR code is in view)
    // console.warn(`Scan error: ${errorMessage}`);
}

function displayScanResult(data) {
    const resultDiv = document.getElementById('scanResult');
    const resultTitle = document.getElementById('resultTitle');
    const resultText = document.getElementById('resultText');
    const attendeeInfo = document.getElementById('attendeeInfo');
    
    resultDiv.style.display = 'block';
    
    if (data.valid && data.scan_result === 'success') {
        resultDiv.className = 'scan-result success';
        resultTitle.innerHTML = '<i class="fas fa-check-circle"></i>';
        resultText.textContent = data.message;
        
        const reg = data.registration;
        attendeeInfo.innerHTML = `
            <p><strong>Name:</strong> ${reg.name}</p>
            <p><strong>Student ID:</strong> ${reg.student_id}</p>
            <p><strong>Email:</strong> ${reg.email}</p>
            <p><strong>Event:</strong> ${reg.event_name}</p>
            <p><strong>Scan Time:</strong> ${new Date().toLocaleString()}</p>
        `;
    } else {
        resultDiv.className = 'scan-result error';
        resultTitle.innerHTML = '<i class="fas fa-times-circle"></i>';
        resultText.textContent = data.message;
        
        if (data.registration) {
            const reg = data.registration;
            attendeeInfo.innerHTML = `
                <p><strong>Name:</strong> ${reg.name}</p>
                <p><strong>Student ID:</strong> ${reg.student_id}</p>
                <p><strong>Status:</strong> ${data.scan_result === 'already_used' ? 'Already Used' : 'Invalid'}</p>
                ${reg.scanned_at ? `<p><strong>Previously Scanned:</strong> ${new Date(reg.scanned_at).toLocaleString()}</p>` : ''}
            `;
        } else {
            attendeeInfo.innerHTML = '<p>No registration information available</p>';
        }
    }
}

function showError(message) {
    const resultDiv = document.getElementById('scanResult');
    const resultTitle = document.getElementById('resultTitle');
    const resultText = document.getElementById('resultText');
    const attendeeInfo = document.getElementById('attendeeInfo');
    
    resultDiv.className = 'scan-result error';
    resultDiv.style.display = 'block';
    resultTitle.innerHTML = '<i class="fas fa-exclamation-circle"></i>';
    resultText.textContent = message;
    attendeeInfo.innerHTML = '';
}

function showFileInput() {
    const readerDiv = document.getElementById('reader');
    readerDiv.innerHTML = `
        <div style="padding: 2rem; text-align: center;">
            <p>Camera not available. Upload QR code image:</p>
            <input type="file" id="qr-input-file" accept="image/*" style="margin-top: 1rem;">
        </div>
    `;
    
    document.getElementById('qr-input-file').addEventListener('change', function(e) {
        if (e.target.files.length === 0) return;
        
        const imageFile = e.target.files[0];
        html5QrCode.scanFile(imageFile, true)
            .then(decodedText => {
                onScanSuccess(decodedText);
            })
            .catch(err => {
                showError('Unable to scan QR code from image');
            });
    });
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

// Cleanup on page unload
window.addEventListener('beforeunload', function() {
    if (html5QrCode) {
        html5QrCode.stop();
    }
});
