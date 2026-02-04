# University Application System - Quick Start Guide

## For Students

### 1. Applying to a University

**From Dashboard:**
1. Browse universities on the dashboard
2. Click "Apply to University" button
3. System creates a draft application
4. You'll be redirected to the application form

**From University Chatbot:**
1. Get university recommendations
2. Click "Apply" on any recommended university
3. Application is created automatically

### 2. Uploading Documents

**On the Application Page:**
1. Select document type (Transcript, SOP, LOR, Resume, Passport, Other)
2. Drag & drop your PDF file OR click to browse
3. File is uploaded automatically
4. Repeat for all required documents

**Requirements:**
- Only PDF files accepted
- Maximum file size: 10MB
- At least one document required to submit

### 3. Submitting Your Application

1. Review all uploaded documents
2. Click "Submit Application" button
3. Confirm submission
4. Application status changes to "Submitted"
5. You'll receive a notification

### 4. Tracking Your Applications

**View All Applications:**
- Go to `/applications` page
- See all your applications with statuses
- Filter by status (Draft, Submitted, Under Review, etc.)
- Click any application to view details

**Application Statuses:**
- 🟡 **Draft** - Not yet submitted
- 🔵 **Submitted** - Submitted, waiting for review
- 🟣 **Under Review** - Being reviewed by university
- 🔴 **Missing Documents** - Additional documents needed
- 🟢 **Conditional Offer** - Offer with conditions
- 🟢 **Final Offer** - Congratulations! Accepted
- ⚫ **Rejected** - Not accepted

### 5. Notifications

You'll receive notifications when:
- Application is submitted
- Status changes to "Under Review"
- Documents are missing
- You receive an offer (conditional or final)

---

## API Endpoints Reference

### Application Management

```
POST   /api/applications/create
GET    /api/applications/{application_id}
GET    /api/applications/user/{user_id}
POST   /api/applications/{application_id}/upload
POST   /api/applications/{application_id}/submit
PATCH  /api/applications/{application_id}/status
DELETE /api/applications/{application_id}
```

### Notifications

```
GET    /api/applications/notifications/{user_id}
POST   /api/applications/notifications/{notification_id}/read
POST   /api/applications/notifications/user/{user_id}/read-all
```

### Helper

```
GET    /api/applications/requirements/{university_id}/{major_id}
```

---

## For Developers

### Creating an Application Programmatically

```javascript
const response = await fetch('/api/applications/create', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        user_id: 1,
        university_id: 5,
        major_id: 2,
        notes: "Optional notes"
    })
});

const data = await response.json();
// Returns: { application_id: 123, status: "Draft", message: "..." }
```

### Uploading a Document

```javascript
const formData = new FormData();
formData.append('file', fileObject);
formData.append('document_type', 'transcript');

const response = await fetch('/api/applications/123/upload', {
    method: 'POST',
    body: formData
});
```

### Using the ApplicationManager Class

```javascript
// Global instance available
const appManager = new ApplicationManager();

// Create application
await appManager.createApplication(userId, universityId, majorId);

// Upload document
await appManager.uploadDocument(file, 'transcript');

// Submit application
await appManager.submitApplication();

// Load user's applications
const data = await appManager.loadUserApplications(userId);
```

---

## File Locations

**Backend:**
- Service: `backend/services/application_service.py`
- Router: `backend/routers/application.py`
- Notifications: `backend/services/notification_service.py`

**Frontend:**
- Manager: `frontend/static/js/application.js`
- Helper: `frontend/static/js/apply-helper.js`
- Form: `frontend/static/templates/apply.html`
- List: `frontend/static/templates/applications.html`

**Uploads:**
- Documents saved to: `backend/uploads/` (configured in `settings.UPLOAD_DIR`)

---

## Troubleshooting

**"Application already exists" error:**
- You can only have one application per university/major combination
- Check your applications list to see existing applications

**Upload fails:**
- Ensure file is PDF format
- Check file size is under 10MB
- Verify application exists and is in Draft status

**Cannot submit:**
- At least one document must be uploaded
- Application must be in Draft status

**Notifications not showing:**
- Check `/api/applications/notifications/{user_id}` endpoint
- Ensure user_id is correct
- Notifications are created on status changes
