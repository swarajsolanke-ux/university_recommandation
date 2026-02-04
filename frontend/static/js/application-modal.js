class ApplicationModal {
    constructor() {
        this.selectedUniversity = null;
        this.selectedMajor = null;
        this.universities = [];
        this.majors = [];
        this.init();
    }

    init() {
        this.createModal();
        this.attachEventListeners();
    }

    createModal() {
        const modalHTML = `
            <div class="modal-overlay" id="applicationModal">
                <div class="application-modal">
                    <div class="modal-header">
                        <h2>Apply to University</h2>
                        <button class="modal-close" id="closeModal">&times;</button>
                    </div>
                    <div class="modal-body">
                        <div class="search-section">
                            <div class="search-box">
                                <input 
                                    type="text" 
                                    id="universitySearch" 
                                    placeholder="Search universities by name, country, or city..."
                                    autocomplete="off"
                                >
                            </div>
                        </div>
                        
                        <div class="university-grid" id="universityGrid">
                            <div class="empty-state">
                                <div class="empty-state-icon">🎓</div>
                                <h3>Loading universities...</h3>
                                <p>Please wait while we fetch available universities</p>
                            </div>
                        </div>

                        <div class="major-selection" id="majorSection" style="display: none;">
                            <h3>Select Your Major</h3>
                            <select class="major-select" id="majorSelect" disabled>
                                <option value="">Select a major...</option>
                            </select>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button class="modal-btn modal-btn-cancel" id="cancelBtn">Cancel</button>
                        <button class="modal-btn modal-btn-primary" id="continueBtn" disabled>
                            Continue to Application
                        </button>
                    </div>
                </div>
            </div>
        `;

        document.body.insertAdjacentHTML('beforeend', modalHTML);
    }

    attachEventListeners() {
        const modal = document.getElementById('applicationModal');
        const closeBtn = document.getElementById('closeModal');
        const cancelBtn = document.getElementById('cancelBtn');
        const continueBtn = document.getElementById('continueBtn');
        const searchInput = document.getElementById('universitySearch');
        const majorSelect = document.getElementById('majorSelect');

        // Close modal
        closeBtn.addEventListener('click', () => this.close());
        cancelBtn.addEventListener('click', () => this.close());

        // Close on overlay click
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                this.close();
            }
        });

        // Search functionality
        searchInput.addEventListener('input', (e) => {
            this.filterUniversities(e.target.value);
        });

        // Major selection
        majorSelect.addEventListener('change', (e) => {
            this.selectedMajor = e.target.value;
            this.updateContinueButton();
        });

        // Continue button
        continueBtn.addEventListener('click', () => this.createApplication());
    }

    async open() {
        const modal = document.getElementById('applicationModal');
        modal.classList.add('active');
        document.body.style.overflow = 'hidden';

        // Load universities
        await this.loadUniversities();
    }

    close() {
        const modal = document.getElementById('applicationModal');
        modal.classList.remove('active');
        document.body.style.overflow = '';

        // Reset state
        this.selectedUniversity = null;
        this.selectedMajor = null;
        document.getElementById('universitySearch').value = '';
        document.getElementById('majorSection').style.display = 'none';
        document.getElementById('continueBtn').disabled = true;
    }

    async loadUniversities() {
        try {
            const response = await fetch('/api/universities/list');
            const data = await response.json();

            if (!response.ok) {
                throw new Error('Failed to load universities');
            }

            this.universities = data.universities || data;
            this.displayUniversities(this.universities);
        } catch (error) {
            console.error('Error loading universities:', error);
            this.showError('Failed to load universities. Please try again.');
        }
    }

    displayUniversities(universities) {
        const grid = document.getElementById('universityGrid');

        if (universities.length === 0) {
            grid.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">🔍</div>
                    <h3>No universities found</h3>
                    <p>Try adjusting your search criteria</p>
                </div>
            `;
            return;
        }

        grid.innerHTML = universities.map(uni => `
            <div class="university-card" data-id="${uni.id}">
                <div class="university-name">${uni.name}</div>
                <div class="university-location">
                    📍 ${uni.city}, ${uni.country}
                </div>
                <div class="university-info">
                    <span class="info-badge tuition">
                        ${uni.tuition_fee === 0 ? 'Free' : '$' + uni.tuition_fee.toLocaleString()}
                    </span>
                    <span class="info-badge gpa">
                        Min GPA: ${uni.min_gpa}
                    </span>
                    ${uni.scholarship_available ? '<span class="info-badge scholarship">💰 Scholarships</span>' : ''}
                </div>
            </div>
        `).join('');

        // Attach click handlers
        grid.querySelectorAll('.university-card').forEach(card => {
            card.addEventListener('click', () => {
                const uniId = parseInt(card.dataset.id);
                this.selectUniversity(uniId);
            });
        });
    }

    filterUniversities(searchTerm) {
        const term = searchTerm.toLowerCase().trim();

        if (!term) {
            this.displayUniversities(this.universities);
            return;
        }

        const filtered = this.universities.filter(uni =>
            uni.name.toLowerCase().includes(term) ||
            uni.country.toLowerCase().includes(term) ||
            uni.city.toLowerCase().includes(term)
        );

        this.displayUniversities(filtered);
    }

    async selectUniversity(universityId) {
        // Update UI
        document.querySelectorAll('.university-card').forEach(card => {
            card.classList.remove('selected');
        });
        document.querySelector(`[data-id="${universityId}"]`).classList.add('selected');

        this.selectedUniversity = universityId;

        // Load majors for this university
        await this.loadMajors(universityId);

        // Show major section
        document.getElementById('majorSection').style.display = 'block';
        document.getElementById('majorSelect').disabled = false;

        // Scroll to major section
        document.getElementById('majorSection').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }

    async loadMajors(universityId) {
        try {
            const response = await fetch(`/api/universities/${universityId}/majors`);
            const data = await response.json();

            if (!response.ok) {
                throw new Error('Failed to load majors');
            }

            this.majors = data.majors || data;
            this.displayMajors();
        } catch (error) {
            console.error('Error loading majors:', error);
            this.showError('Failed to load majors. Please try again.');
        }
    }

    displayMajors() {
        const select = document.getElementById('majorSelect');

        select.innerHTML = '<option value="">Select a major...</option>' +
            this.majors.map(major => `
                <option value="${major.id || major.major_id}">${major.name || major.major_name}</option>
            `).join('');
    }

    updateContinueButton() {
        const continueBtn = document.getElementById('continueBtn');
        continueBtn.disabled = !(this.selectedUniversity && this.selectedMajor);
    }

    async createApplication() {
        const continueBtn = document.getElementById('continueBtn');
        const originalText = continueBtn.innerHTML;

        try {
            // Show loading state
            continueBtn.disabled = true;
            continueBtn.innerHTML = '<span class="loading-spinner"></span>Creating application...';

            // Get user ID from localStorage or session
            const userId = this.getUserId();

            if (!userId) {
                throw new Error('User not logged in');
            }

            // Create application
            const response = await fetch('/api/applications/create', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    user_id: userId,
                    university_id: this.selectedUniversity,
                    major_id: parseInt(this.selectedMajor)
                })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || 'Failed to create application');
            }

            // Redirect to application page
            window.location.href = `/Apply_university?app_id=${data.application_id}`;

        } catch (error) {
            console.error('Error creating application:', error);
            continueBtn.disabled = false;
            continueBtn.innerHTML = originalText;
            this.showError(error.message);
        }
    }

    getUserId() {
        // Try to get user ID from localStorage
        const userStr = localStorage.getItem('user');
        if (userStr) {
            try {
                const user = JSON.parse(userStr);
                return user.id || user.user_id;
            } catch (e) {
                console.error('Error parsing user data:', e);
            }
        }

        // Fallback to a default user ID for testing
        // In production, this should redirect to login
        return 1;
    }

    showError(message) {
        // Create a temporary notification
        const notification = document.createElement('div');
        notification.className = 'notification notification-error';
        notification.innerHTML = `
            <span>${message}</span>
            <button onclick="this.parentElement.remove()">×</button>
        `;

        document.body.appendChild(notification);

        setTimeout(() => {
            notification.remove();
        }, 5000);
    }
}

// Initialize modal
const applicationModal = new ApplicationModal();

// Export for use in other scripts
if (typeof window !== 'undefined') {
    window.applicationModal = applicationModal;
}
