
class UniversityChatbot {
    constructor() {
        this.sessionId = null;
        this.selectedUniversities = new Set();
        this.filters = {
            scholarship_track: true,
            country: '',
            major: '',
            max_tuition: 5000,
            min_gpa: 4.0
        };

        this.init();
    }

    init() {
        this.cacheElements();
        this.attachEventListeners();
        this.loadFilterOptions();
        this.createSession();

    }


    showUniversityList(universities) {
        let html = '<div class="university-list"><ul>';

        universities.forEach(u => {
            html += `
            <li>
                <strong>${u.name}</strong> - ${u.country}
            </li>
        `;
        });

        html += '</ul></div>';

        this.addMessage(html, 'assistant');
    }

    async sendFilteredQuery() {
        const message = this.messageInput.value.trim();
        if (!message) return;


        this.addMessage(message, 'user');
        this.messageInput.value = '';
        this.showTypingIndicator();

        try {
            const payload = {
                message: message,          // matches ChatMessage.message
                session_id: this.sessionId,
                filters: this.filters
                // query: message,
                // filters: this.filters
            };

            const response = await fetch('/chatbot/university/query', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload)
            });

            if (!response.ok) {
                throw new Error(`HTTP error ${response.status}`);
            }

            const data = await response.json();
            console.log(data)

            this.removeTypingIndicator();

            
            
            
            const cleanText = this.cleanModelResponse(data.response);
            this.sessionId = data.session_id; 

            
            this.addMessage(cleanText, 'assistant', data.universities);

        } catch (error) {
            console.error('Error sending filtered query:', error);
            this.removeTypingIndicator();
            this.addMessage(
                'Sorry, I could not fetch recommendations.',
                'assistant'
            );
        }
    }


    hasAnyActiveFilter() {
        const f = this.filters;
        const hasCountry = f.country && f.country !== "";
        const hasMajor = f.major && f.major !== "";
        const hasTuition = f.max_tuition && f.max_tuition < this.maxBudget; 
        const hasGPA = f.min_gpa && f.min_gpa > 0;

        return hasCountry || hasMajor || hasTuition || hasGPA;
    }





    cacheElements() {
        // Containers
        this.messagesContainer = document.getElementById('messagesContainer');
        this.comparisonModal = document.getElementById('comparisonModal');
        this.comparisonContent = document.getElementById('comparisonContent');

        // Input elements
        this.messageInput = document.getElementById('messageInput');
        this.sendBtn = document.getElementById('sendBtn');

        // Filter elements
        this.countryFilter = document.getElementById('countryFilter');
        this.majorFilter = document.getElementById('majorFilter');
        this.budgetRange = document.getElementById('budgetRange');
        this.budgetValue = document.getElementById('budgetValue');
        this.gpaRange = document.getElementById('gpaRange');
        this.gpaValue = document.getElementById('gpaValue');

        // Buttons
        this.trackBtns = document.querySelectorAll('.track-btn');
        this.quickActionBtns = document.querySelectorAll('.quick-action-btn');
        this.applyFiltersBtn = document.getElementById('applyFiltersBtn');
        this.clearChatBtn = document.getElementById('clearChatBtn');
        this.closeModalBtn = document.getElementById('closeModalBtn');
    }

    attachEventListeners() {
        // Send message
        this.sendBtn.addEventListener('click', () => this.message_routing());
        // this.applyFiltersBtn.addEventListener('click',()=>this.sendFilteredQuery());
        console.log("apply filtered clicked");
        this.messageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.message_routing();
        });

        // Track selection
        this.trackBtns.forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.trackBtns.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                this.filters.scholarship_track = btn.dataset.track === 'scholarship';
            });
        });

        // Quick actions
        this.quickActionBtns.forEach(btn => {
            btn.addEventListener('click', (e) => {
                const message = btn.dataset.message;
                this.messageInput.value = message;
                console.log("Quick action clicked:", message);
                this.message_routing(); // Route correctly based on filters
            });
        });

        // Filters
        this.budgetRange.addEventListener('input', (e) => {
            const value = parseInt(e.target.value);
            this.budgetValue.textContent = value.toLocaleString();
            this.filters.max_tuition = value;
        });

        this.gpaRange.addEventListener('input', (e) => {
            const value = parseFloat(e.target.value);
            this.gpaValue.textContent = value.toFixed(1);
            this.filters.min_gpa = value;
        });

        this.applyFiltersBtn.addEventListener('click', () => {
            this.filters.country = this.countryFilter.value;
            this.filters.major = this.majorFilter.value;
            this.showToast('Filters applied! Send a message to see results.');
        });

        // Clear chat
        this.clearChatBtn.addEventListener('click', () => this.clearChat());

        // Modal
        this.closeModalBtn.addEventListener('click', () => this.closeModal());
        this.comparisonModal.addEventListener('click', (e) => {
            if (e.target === this.comparisonModal) this.closeModal();
        });
    }

    async loadFilterOptions() {
        try {
            const response = await fetch('/chatbot/university/filters');
            const data = await response.json();
            console.log(data)

            // Populate countries
            data.countries.forEach(country => {
                const option = document.createElement('option');
                option.value = country;
                option.textContent = country;
                this.countryFilter.appendChild(option);
            });

            // Populate majors
            data.majors.forEach(major => {
                const option = document.createElement('option');
                option.value = major;
                option.textContent = major;
                this.majorFilter.appendChild(option);
            });

            // Set budget range
            if (data.tuition_range) {
                this.maxBudget = data.tuition_range.max; // Save max for comparison
                this.budgetRange.min = data.tuition_range.min;
                this.budgetRange.max = data.tuition_range.max;
                this.budgetRange.value = data.tuition_range.max;
                this.budgetValue.textContent = data.tuition_range.max.toLocaleString();
                this.filters.max_tuition = data.tuition_range.max;
            }

        } catch (error) {
            console.error('Error loading filters:', error);
            this.showToast('Failed to load filter options', 'error');
        }
    }

    async createSession() {
        try {
            const response = await fetch('/chatbot/university/session', {
                method: 'POST',
                headers: this.getHeaders()
            });
            const data = await response.json();
            this.sessionId = data.session_id;
        } catch (error) {
            console.error('Error creating session:', error);
        }
    }

    cleanModelResponse(text) {
        if (!text) return "";

        return text

            .replace(/^\s*\*+\s?/gm, '')

            .replace(/\*\*/g, '')

            .replace(/\n{3,}/g, '\n\n')

            .trim();
    }


    async message_routing() {
        const message = this.messageInput.value.trim();
        if (!message) return;

        console.log("--- Message Routing ---");
        const hasFilters = this.hasAnyActiveFilter();
        console.log("Message:", message);
        console.log("Active Filters Detected:", hasFilters);
        console.log("Current Filter State:", JSON.stringify(this.filters));

        if (hasFilters) {
            await this.sendFilteredQuery();
        } else {
            await this.sendMessage();
        }
        console.log("message is");
    }

    async sendMessage() {
        const message = this.messageInput.value.trim();
        if (!message) return;

        // Display user message
        this.addMessage(message, 'user');
        this.messageInput.value = '';

        // Show typing indicator
        this.showTypingIndicator();

        try {
            const response = await fetch('/chatbot/university/chat', {
                method: 'POST',
                headers: this.getHeaders(),
                body: JSON.stringify({
                    message: message,
                    session_id: this.sessionId,
                    filters: this.filters
                })
            });


            if (!response.ok) throw new Error('Failed to get response');

            const data = await response.json();
            this.sessionId = data.session_id;

          
            this.removeTypingIndicator();
            // var model_rep = this.cleanModelResponse(data.response);
            // ✅ Convert markdown to HTML safely
            const rawHtml = marked.parse(data.response);
            const cleanHtml = DOMPurify.sanitize(rawHtml);
            this.addMessage(cleanHtml, 'assistant', data.universities,True);
            // this.addMessage(data.universities);

        } catch (error) {
            console.error('Error sending message:', error);
            this.removeTypingIndicator();
            this.addMessage('Sorry, I encountered an error. Please try again.', 'assistant');
            this.showToast('Failed to send message', 'error');
        }
    }


    // addMessage(content, role, universities = [],isHTML=false) {
    //     const wrapper = document.createElement('div');
    //     wrapper.className = `message-wrapper ${role}-message`;

    //     const bubble = document.createElement('div');
    //     bubble.className = 'message-bubble';

    //     const messageContent = document.createElement('div');
    //     messageContent.className = 'message-content';

    //     // Add text content
    //     const paragraphs = content.split('\n').filter(p => p.trim());
    //     paragraphs.forEach(p => {
    //         const para = document.createElement('p');
    //         para.textContent = p;
    //         messageContent.appendChild(para);
    //     });

    //     bubble.appendChild(messageContent);

    //     // Add university cards if present
    //     if (universities && universities.length > 0) {
    //         const cardsContainer = document.createElement('div');
    //         cardsContainer.className = 'university-cards';

    //         universities.forEach(uni => {
    //             const card = this.createUniversityCard(uni);
    //             cardsContainer.appendChild(card);
    //         });

    //         bubble.appendChild(cardsContainer);

    //         // Add compare button if multiple universities
    //         if (universities.length >= 2) {
    //             const compareBtn = document.createElement('button');
    //             compareBtn.className = 'apply-filters-btn';
    //             compareBtn.style.marginTop = '1rem';
    //             compareBtn.textContent = `Compare Selected (${this.selectedUniversities.size})`;
    //             compareBtn.onclick = () => this.compareUniversities();
    //             bubble.appendChild(compareBtn);
    //         }
    //     }

    //     wrapper.appendChild(bubble);
    //     this.messagesContainer.appendChild(wrapper);
    //     this.scrollToBottom();
    // }


    addMessage(content, role, universities = [], isHTML = false) {
    const wrapper = document.createElement('div');
    wrapper.className = `message-wrapper ${role}-message`;

    const bubble = document.createElement('div');
    bubble.className = 'message-bubble';

    const messageContent = document.createElement('div');
    messageContent.className = 'message-content';

    // ✅ If assistant message is HTML (rendered markdown)
    if (role === 'assistant' && isHTML) {
        messageContent.innerHTML = content;   // already sanitized
    } else {
        // Plain text rendering (user messages, system messages)
        const paragraphs = content.split('\n').filter(p => p.trim());
        paragraphs.forEach(p => {
            const para = document.createElement('p');
            para.textContent = p;
            messageContent.appendChild(para);
        });
    }

    bubble.appendChild(messageContent);

    // --- University cards logic (unchanged) ---
    if (universities && universities.length > 0) {
        const cardsContainer = document.createElement('div');
        cardsContainer.className = 'university-cards';

        universities.forEach(uni => {
            const card = this.createUniversityCard(uni);
            cardsContainer.appendChild(card);
        });

        bubble.appendChild(cardsContainer);

        if (universities.length >= 2) {
            const compareBtn = document.createElement('button');
            compareBtn.className = 'apply-filters-btn';
            compareBtn.style.marginTop = '1rem';
            compareBtn.textContent = `Compare Selected (${this.selectedUniversities.size})`;
            compareBtn.onclick = () => this.compareUniversities();
            bubble.appendChild(compareBtn);
        }
    }

    wrapper.appendChild(bubble);
    this.messagesContainer.appendChild(wrapper);
    this.scrollToBottom();
}

    createUniversityCard(uni) {
        const card = document.createElement('div');
        card.className = 'university-card';

        card.innerHTML = `
            <h3>${uni.name}</h3>
            <p>📍 ${uni.city}, ${uni.country}</p>
            <p>💰 $${uni.tuition_fee?.toLocaleString()}/year</p>
            <p>📊 Min GPA: ${uni.min_gpa}</p>
            <p>🏆 Ranking: ${uni.ranking}</p>
            ${uni.scholarship_available ? '<span class="badge">🎓 Scholarship Available</span>' : ''}
            <div class="compare-checkbox">
                <input type="checkbox" id="compare-${uni.id}" data-uni-id="${uni.id}">
                <label for="compare-${uni.id}">Compare</label>
            </div>
        `;

        // Add checkbox handler
        const checkbox = card.querySelector('input[type="checkbox"]');
        checkbox.addEventListener('change', (e) => {
            if (e.target.checked) {
                if (this.selectedUniversities.size >= 2) {
                    e.target.checked = false;
                    this.showToast('You can only compare up to 3 universities', 'warning');
                    return;
                }
                this.selectedUniversities.add(uni.id);
            } else {
                this.selectedUniversities.delete(uni.id);
            }
        });

        return card;
    }

    async compareUniversities() {
        if (this.selectedUniversities.size < 2) {
            this.showToast('Please select at least 2 universities to compare', 'warning');
            return;
        }

        if (this.selectedUniversities.size > 3) {
            this.showToast('You can only compare up to 3 universities', 'warning');
            return;
        }

        try {
            const response = await fetch('/chatbot/university/compare', {
                method: 'POST',
                headers: this.getHeaders(),
                body: JSON.stringify({
                    university_ids: Array.from(this.selectedUniversities)
                })
            });

            if (!response.ok) throw new Error('Failed to compare');

            const data = await response.json();
            this.displayComparison(data);

        } catch (error) {
            console.error('Error comparing universities:', error);
            this.showToast('Failed to compare universities', 'error');
        }
    }

    displayComparison(data) {
        const universities = data.universities;

        let tableHTML = '<table class="comparison-table"><thead><tr><th>Criteria</th>';
        universities.forEach(uni => {
            tableHTML += `<th>${uni.name}</th>`;
        });
        tableHTML += '</tr></thead><tbody>';

        // Add comparison rows
        const criteria = [
            { label: 'Country', key: 'country' },
            { label: 'City', key: 'city' },
            { label: 'Tuition Fee', key: 'tuition_fee', format: (v) => `$${v.toLocaleString()}/year` },
            { label: 'Min GPA', key: 'min_gpa' },
            { label: 'Scholarship', key: 'scholarship_available', format: (v) => v ? '✅ Yes' : '❌ No' },
            { label: 'Ranking', key: 'ranking', format: (v) => `#${v}` },
            { label: 'Acceptance Rate', key: 'acceptance_rate', format: (v) => `${(v * 100).toFixed(1)}%` },
            { label: 'Duration', key: 'duration' }
        ];

        criteria.forEach(criterion => {
            tableHTML += `<tr><td><strong>${criterion.label}</strong></td>`;
            universities.forEach(uni => {
                let value = uni[criterion.key];
                if (criterion.format) value = criterion.format(value);
                tableHTML += `<td>${value || 'N/A'}</td>`;
            });
            tableHTML += '</tr>';
        });

        tableHTML += '</tbody></table>';

        this.comparisonContent.innerHTML = tableHTML;
        this.comparisonModal.classList.add('active');
    }

    closeModal() {
        this.comparisonModal.classList.remove('active');
    }

    showTypingIndicator() {
        const indicator = document.createElement('div');
        indicator.className = 'message-wrapper assistant-message typing-indicator';
        indicator.id = 'typingIndicator';
        indicator.innerHTML = `
            <div class="message-bubble">
                <div class="typing-indicator">
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                </div>
            </div>
        `;
        this.messagesContainer.appendChild(indicator);
        this.scrollToBottom();
    }

    removeTypingIndicator() {
        const indicator = document.getElementById('typingIndicator');
        if (indicator) indicator.remove();
    }

    clearChat() {
        if (confirm('Are you sure you want to clear the chat?')) {
            // Keep only the welcome message
            const welcomeMessage = this.messagesContainer.firstElementChild;
            this.messagesContainer.innerHTML = '';
            if (welcomeMessage) {
                this.messagesContainer.appendChild(welcomeMessage);
            }
            this.selectedUniversities.clear();
            this.createSession();
            this.showToast('Chat cleared');
        }
    }

    scrollToBottom() {
        setTimeout(() => {
            this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
        }, 100);
    }

    showToast(message, type = 'info') {
        // Simple toast notification
        const toast = document.createElement('div');
        toast.style.cssText = `
            position: fixed;
            bottom: 2rem;
            right: 2rem;
            background: ${type === 'error' ? '#ef4444' : type === 'warning' ? '#f59e0b' : '#6366f1'};
            color: white;
            padding: 1rem 1.5rem;
            border-radius: 12px;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
            z-index: 10000;
            animation: slideIn 0.3s ease-out;
        `;
        toast.textContent = message;
        document.body.appendChild(toast);

        setTimeout(() => {
            toast.style.animation = 'slideOut 0.3s ease-out';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }

    getHeaders() {
        const token = localStorage.getItem('access_token');
        const headers = {
            'Content-Type': 'application/json'
        };
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }
        return headers;
    }
}

// Initialize chatbot when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.chatbot = new UniversityChatbot();
});

// Add CSS for animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            opacity: 0;
            transform: translateX(100px);
        }
        to {
            opacity: 1;
            transform: translateX(0);
        }
    }
    
    @keyframes slideOut {
        from {
            opacity: 1;
            transform: translateX(0);
        }
        to {
            opacity: 0;
            transform: translateX(100px);
        }
    }
`;
document.head.appendChild(style);
