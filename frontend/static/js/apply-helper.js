/**
 * University Apply Integration
 * Handles "Apply" button clicks from university cards
 */

// Function to handle Apply button click
async function applyToUniversity(universityId, universityName, majorId = null) {
    // Get user ID from storage
    const userId = parseInt(localStorage.getItem('user_id') || sessionStorage.getItem('user_id') || '1');

    // If no major selected, prompt user to select
    if (!majorId) {
        // For now, use a default major ID (you can enhance this with a modal)
        majorId = 1; // Default to first major
    }

    try {
        // Show loading state
        showNotification('Creating application...', 'info');

        // Create application via API
        const response = await fetch('/api/applications/create', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                user_id: userId,
                university_id: universityId,
                major_id: majorId,
                notes: `Application for ${universityName}`
            })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || 'Failed to create application');
        }

        // Redirect to application page
        showNotification('Application created successfully!', 'success');
        setTimeout(() => {
            window.location.href = `/Apply_university?app_id=${data.application_id}`;
        }, 1000);

    } catch (error) {
        console.error('Error creating application:', error);
        showNotification('Error: ' + error.message, 'error');
    }
}

// Helper function to show notifications
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 16px 24px;
        border-radius: 8px;
        color: white;
        font-weight: 500;
        box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        z-index: 9999;
        animation: slideIn 0.3s ease;
    `;

    const colors = {
        success: '#10b981',
        error: '#ef4444',
        warning: '#f59e0b',
        info: '#3b82f6'
    };

    notification.style.background = colors[type] || colors.info;
    notification.innerHTML = `
        <span>${message}</span>
        <button onclick="this.parentElement.remove()" style="background: none; border: none; color: white; font-size: 20px; cursor: pointer; margin-left: 12px; padding: 0;">×</button>
    `;

    document.body.appendChild(notification);

    setTimeout(() => {
        notification.remove();
    }, 5000);
}

// Make function globally available
window.applyToUniversity = applyToUniversity;
