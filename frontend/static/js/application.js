class ApplicationManager {
    constructor() {
        this.currentApplicationId = null;
        this.uploadedDocuments = [];
        this.init();
    }

    async init() {
        try {
            // Get application ID from URL if exists
            const urlParams = new URLSearchParams(window.location.search);
            const appIdFromUrl = urlParams.get('app_id');

            if (appIdFromUrl) {
                this.currentApplicationId = appIdFromUrl;
                console.log('Application ID from URL:', this.currentApplicationId);
                await this.loadApplicationDetails();
            } else {
                console.log('No application ID in URL');
            }
        } catch (error) {
            console.error('Error during initialization:', error);
            this.showNotification('Error loading application. Please try again.', 'error');
        }
    }

    /**
     * Create a new application
     */
    async createApplication(userId, universityId, majorId, notes = null) {
        try {
            const response = await fetch('/api/applications/create', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    user_id: userId,
                    university_id: universityId,
                    major_id: majorId,
                    notes: notes
                })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || 'Failed to create application');
            }
            console.log("application id is feth sucessfully:", data.application_id)
            this.currentApplicationId = data.application_id;
            console.log("current application id :", this.currentApplicationId)

            // Redirect to application page
            window.location.href = `/Apply_university?app_id=${data.application_id}`;

            return data;
        } catch (error) {
            console.error('Error creating application:', error);
            this.showNotification('Error creating application: ' + error.message, 'error');
            throw error;
        }
    }

    /**
     * Load application details
     */
    async loadApplicationDetails() {
        try {
            console.log('Loading application details for ID:', this.currentApplicationId);
            const response = await fetch(`/api/applications/${this.currentApplicationId}`);
            const data = await response.json();

            if (!response.ok) {
                console.error('Failed to load application:', data);
                throw new Error(data.detail || 'Failed to load application details');
            }

            console.log('Application loaded successfully:', data);
            this.displayApplicationDetails(data);
            this.uploadedDocuments = data.documents || [];
            this.updateDocumentTable();

            // Handle UI elements based on status
            const submitBtn = document.getElementById('submitBtn');
            const uploadZone = document.getElementById('uploadZone');
            const docTypeSelector = document.querySelector('.document-type-selector');

            if (data.status !== 'Draft') {
                if (submitBtn) submitBtn.style.display = 'none';
                if (uploadZone) uploadZone.style.display = 'none';
                if (docTypeSelector) docTypeSelector.style.display = 'none';

                const timeline = document.getElementById('applicationTimeline');
                if (timeline) {
                    const submissionItem = `
                        <div class="timeline-item active">
                            <div class="timeline-icon">✓</div>
                            <div class="timeline-content">
                                <div class="timeline-title">Application Submitted</div>
                                <div class="timeline-date">${new Date(data.last_updated).toLocaleDateString()}</div>
                                <div class="timeline-desc">Your application is now under review.</div>
                            </div>
                        </div>
                    `;
                    timeline.innerHTML += submissionItem;
                }
            }

            return data;
        } catch (error) {
            console.error('Error loading application:', error);
            this.showNotification('Error loading application: ' + error.message, 'error');
            // Don't reset currentApplicationId here - keep it for retry
        }
    }

    /**
     * Display application details in the UI
     */
    displayApplicationDetails(application) {
        const detailsContainer = document.getElementById('applicationDetails');
        if (!detailsContainer) return;

        const date = new Date(application.application_date);
        const createdDateEl = document.getElementById('createdDate');
        if (createdDateEl) {
            createdDateEl.textContent = date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        }

        detailsContainer.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: start;">
                <div>
                    <h1>${application.university_name}</h1>
                    <p class="major-name" style="font-size: 18px; color: #667eea; font-weight: 600; margin-top: 4px;">
                        ${application.major_name}
                    </p>
                    <p style="color: #718096; margin-top: 8px; display: flex; align-items: center; gap: 8px;">
                        📍 ${application.city}, ${application.country}
                    </p>
                </div>
                <div style="text-align: right;">
                    <span class="status-badge status-${application.status.toLowerCase().replace(/ /g, '-')}">
                        ${application.status}
                    </span>
                    <p style="font-size: 12px; color: #a0aec0; margin-top: 8px;">
                        Last updated: ${new Date(application.last_updated).toLocaleDateString()}
                    </p>
                </div>
            </div>
        `;

        // Update progress indicator based on status
        this.updateProgressIndicator(application.status);
    }

    updateProgressIndicator(status) {
        const steps = document.querySelectorAll('.progress-step');
        const statusMap = {
            'Draft': 1,
            'Submitted': 2,
            'Under Review': 3,
            'Missing Documents': 3,
            'Conditional Offer': 4,
            'Final Offer': 4,
            'Rejected': 4
        };

        const currentStep = statusMap[status] || 1;

        steps.forEach((step, index) => {
            step.classList.remove('active', 'completed');
            if (index + 1 < currentStep) {
                step.classList.add('completed');
                const circle = step.querySelector('.progress-circle');
                if (circle) circle.textContent = '✓';
            } else if (index + 1 === currentStep) {
                step.classList.add('active');
                const circle = step.querySelector('.progress-circle');
                if (circle && index + 1 > 1) circle.textContent = index + 1;
            } else {
                const circle = step.querySelector('.progress-circle');
                if (circle) circle.textContent = index + 1;
            }
        });
    }

    /**
     * Upload document
     */
    async uploadDocument(file, documentType) {
        console.log('Upload attempt - Current Application ID:', this.currentApplicationId);
        console.log('File:', file ? file.name : 'No file', 'Type:', documentType);

        // Try to get application ID from URL if not set
        if (!this.currentApplicationId) {
            const urlParams = new URLSearchParams(window.location.search);
            const appIdFromUrl = urlParams.get('app_id');

            if (appIdFromUrl) {
                this.currentApplicationId = appIdFromUrl;
                console.log('Retrieved application ID from URL:', this.currentApplicationId);
            } else {
                this.showNotification('No active application. Please refresh the page.', 'error');
                console.error('Upload failed: No application ID set');
                return;
            }
        }
        console.log("application id is feth sucessfully:", this.currentApplicationId)
        const formData = new FormData();
        formData.append('file', file);
        formData.append('document_type', documentType);
        console.log("file is uploaded ", file)
        try {
            console.log('Uploading to:', `/api/applications/${this.currentApplicationId}/upload`);
            const response = await fetch(`/api/applications/${this.currentApplicationId}/upload`, {
                method: 'POST',
                body: formData
            });

            const data = await response.json();
            console.log('Upload response:', response.status, data);

            if (!response.ok) {
                throw new Error(data.detail || 'Upload failed');
            }

            this.uploadedDocuments.push(data);
            this.updateDocumentTable();
            this.showNotification('Document uploaded successfully', 'success');

            return data;
        } catch (error) {
            console.error('Error uploading document:', error);
            this.showNotification('Error uploading document: ' + error.message, 'error');
            throw error;
        }
    }

    /**
     * Update document table
     */
    updateDocumentTable() {
        const tableBody = document.getElementById('docTableBody');
        if (!tableBody) return;

        tableBody.innerHTML = '';

        this.uploadedDocuments.forEach((doc, index) => {
            const row = document.createElement('tr');
            const statusClass = doc.is_verified ? 'status-final-offer' : 'status-submitted';
            const statusText = doc.is_verified ? 'Verified' : 'Pending Verification';

            row.innerHTML = `
                <td>${index + 1}</td>
                <td>
                    <div style="font-weight: 500;">${doc.filename}</div>
                    <div style="font-size: 11px; color: #a0aec0;">${(new Date(doc.uploaded_at)).toLocaleString()}</div>
                </td>
                <td><span class="info-badge">${doc.document_type.toUpperCase()}</span></td>
                <td>${new Date(doc.uploaded_at).toLocaleDateString()}</td>
                <td>
                    <span class="status-badge ${statusClass}" style="font-size: 10px; padding: 4px 8px;">
                        ${statusText}
                    </span>
                </td>
                <td>
                    <button class="btn preview-btn" style="padding: 6px 12px; font-size: 12px;" onclick="appManager.previewDocument('${doc.file_path}')">
                        View
                    </button>
                </td>
            `;
            tableBody.appendChild(row);
        });

        // Update submit button visibility
        const submitBtn = document.getElementById('submitBtn');
        if (submitBtn) {
            // Only enabled if in draft and has documents
            // This logic will be further refined in loadApplicationDetails
        }
    }

    /**
     * Submit application
     */
    async submitApplication() {
        if (!this.currentApplicationId) {
            this.showNotification('No active application', 'error');
            return;
        }

        if (this.uploadedDocuments.length === 0) {
            this.showNotification('Please upload at least one document before submitting', 'warning');
            return;
        }

        if (!confirm('Are you sure you want to submit this application? You will not be able to edit it after submission.')) {
            return;
        }

        try {
            const response = await fetch(`/api/applications/${this.currentApplicationId}/submit`, {
                method: 'POST'
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || 'Submission failed');
            }

            this.showNotification('Application submitted successfully!', 'success');

            // Reload to show updated status
            setTimeout(() => {
                window.location.reload();
            }, 2000);

            return data;
        } catch (error) {
            console.error('Error submitting application:', error);
            this.showNotification('Error submitting application: ' + error.message, 'error');
            throw error;
        }
    }

    /**
     * Preview document
     */
    previewDocument(filePath) {
        // Open document in new tab
        window.open(`/static/uploads/${filePath.split('/').pop()}`, '_blank');
    }

    /**
     * Show notification
     */
    showNotification(message, type = 'info') {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.innerHTML = `
            <span>${message}</span>
            <button onclick="this.parentElement.remove()">×</button>
        `;

        // Add to page
        let container = document.getElementById('notificationContainer');
        if (!container) {
            container = document.createElement('div');
            container.id = 'notificationContainer';
            container.style.cssText = 'position: fixed; top: 20px; right: 20px; z-index: 9999;';
            document.body.appendChild(container);
        }

        container.appendChild(notification);

        // Auto remove after 5 seconds
        setTimeout(() => {
            notification.remove();
        }, 5000);
    }

    /**
     * Load user's all applications
     */
    async loadUserApplications(userId, statusFilter = null) {
        try {
            let url = `/api/applications/user/${userId}`;
            if (statusFilter) {
                url += `?status=${statusFilter}`;
            }

            const response = await fetch(url);
            const data = await response.json();

            if (!response.ok) {
                throw new Error('Failed to load applications');
            }

            return data;
        } catch (error) {
            console.error('Error loading applications:', error);
            this.showNotification('Error loading applications', 'error');
            return { applications: [], total_count: 0, status_counts: {} };
        }
    }

    /**
     * Display applications list
     */
    displayApplicationsList(applications) {
        const container = document.getElementById('applicationsContainer');
        if (!container) return;

        if (applications.length === 0) {
            container.innerHTML = '<p class="no-applications">No applications found</p>';
            return;
        }

        container.innerHTML = applications.map(app => `
            <div class="application-card" onclick="window.location.href='/Apply_university?app_id=${app.id}'">
                <div class="app-header">
                    <h4>${app.university_name}</h4>
                    <span class="status-badge status-${app.status.toLowerCase().replace(' ', '-')}">
                        ${app.status}
                    </span>
                </div>
                <p class="app-major">${app.major_name}</p>
                <p class="app-country">${app.country}</p>
                <div class="app-footer">
                    <span class="app-date">Applied: ${new Date(app.application_date).toLocaleDateString()}</span>
                    <span class="app-docs">${app.document_count} documents</span>
                </div>
            </div>
        `).join('');
    }

    /**
     * Load and display notifications
     */
    async loadNotifications(userId, unreadOnly = false) {
        try {
            const response = await fetch(`/api/applications/notifications/${userId}?unread_only=${unreadOnly}`);
            const data = await response.json();

            if (!response.ok) {
                throw new Error('Failed to load notifications');
            }

            return data;
        } catch (error) {
            console.error('Error loading notifications:', error);
            return { notifications: [], unread_count: 0 };
        }
    }

    /**
     * Mark notification as read
     */
    async markNotificationRead(notificationId, userId) {
        try {
            const response = await fetch(`/api/applications/notifications/${notificationId}/read?user_id=${userId}`, {
                method: 'POST'
            });

            if (!response.ok) {
                throw new Error('Failed to mark notification as read');
            }

            return true;
        } catch (error) {
            console.error('Error marking notification as read:', error);
            return false;
        }
    }
}

// Initialize global instance
const appManager = new ApplicationManager();

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ApplicationManager;
}
