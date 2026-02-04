
let currentQuestion = 0;
let assessmentData = {
    data:[]
};

document.addEventListener('DOMContentLoaded', () => {
    // Check authentication
    if (!isLoggedIn()) {
        window.location.href = '/login';
        return;
    }

    // Setup event listeners
    setupEventListeners();

    // Start assessment after a brief delay
    setTimeout(() => {
        askQuestion(0);
    }, 1500);
});

function setupEventListeners() {
    const userInput = document.getElementById('userInput');
    const sendBtn = document.getElementById('sendBtn');

    // Auto-resize textarea
    userInput.addEventListener('input', () => {
        userInput.style.height = 'auto';
        userInput.style.height = userInput.scrollHeight + 'px';
    });

    // Send on Enter (Shift+Enter for new line)
    userInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendAnswer();
        }
    });

    sendBtn.addEventListener('click', sendAnswer);
}



function askQuestion(index) {
  if (index >= assessmentQuestions.length) {
    processAssessment();
    return;
  }

  const questionObj = assessmentQuestions[index]; 
  currentQuestion = index;

  // Update progress
  const progress = ((index + 1) / assessmentQuestions.length) * 100;
  document.getElementById('progressFill').style.width = progress + '%';
  document.getElementById('currentStep').textContent = `Step ${index + 1}`;
  document.getElementById('totalSteps').textContent = assessmentQuestions.length;

  // Show typing indicator
  showTypingIndicator();

  setTimeout(() => {
    hideTypingIndicator();
    addAIMessage(questionObj.question); 
    enableInput(); 
  }, 1000);
}


function addAIMessage(message) {
    const chatContainer = document.getElementById('chatContainer');
    const messageGroup = document.createElement('div');
    messageGroup.className = 'message-group';

    messageGroup.innerHTML = `
        <div class="ai-avatar">🤖</div>
        <div class="message-bubble ai-message">
            <p>${message}</p>
        </div>
    `;

    chatContainer.appendChild(messageGroup);
    scrollToBottom();
}

function addUserMessage(message) {
    const chatContainer = document.getElementById('chatContainer');
    const messageGroup = document.createElement('div');
    messageGroup.className = 'message-group user';

    const userInitial = localStorage.getItem('userInitial') || 'U';

    messageGroup.innerHTML = `
        <div class="user-avatar">${userInitial}</div>
        <div class="message-bubble user-message">
            <p>${message}</p>
        </div>
    `;

    chatContainer.appendChild(messageGroup);
    scrollToBottom();
}

function showTypingIndicator() {
    const chatContainer = document.getElementById('chatContainer');
    const indicator = document.createElement('div');
    indicator.className = 'message-group typing';
    indicator.id = 'typingIndicator';

    indicator.innerHTML = `
        <div class="ai-avatar">🤖</div>
        <div class="typing-indicator">
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
        </div>
    `;

    chatContainer.appendChild(indicator);
    scrollToBottom();
}

function hideTypingIndicator() {
    const indicator = document.getElementById('typingIndicator');
    if (indicator) {
        indicator.remove();
    }
}

function showQuickAnswers(answers) {
    const quickActions = document.getElementById('quickActions');
    quickActions.innerHTML = '';

    answers.forEach(answer => {
        const btn = document.createElement('button');
        btn.className = 'quick-btn';
        btn.textContent = answer;
        btn.onclick = () => selectQuickAnswer(answer);
        quickActions.appendChild(btn);
    });
}

function selectQuickAnswer(answer) {
    document.getElementById('userInput').value = answer;
    sendAnswer();
}

function enableInput() {
    const userInput = document.getElementById('userInput');
    const sendBtn = document.getElementById('sendBtn');

    userInput.disabled = false;
    sendBtn.disabled = false;
    userInput.focus();
}

function disableInput() {
    const userInput = document.getElementById('userInput');
    const sendBtn = document.getElementById('sendBtn');

    userInput.disabled = true;
    sendBtn.disabled = true;
}


function buildAssessmentQuestions(apiResponse) {
  const questionsArray = [];

  let step = 1;
  for (const [category, questionText] of Object.entries(apiResponse)) {
    questionsArray.push({
      step: step++,
      category: category,
      question: questionText
    });
  }

  return questionsArray;
}


const categories = [
  "personality",
  "Academic_Strengths",
  "thinking_style",
  "Learning_Style",
  "Interests",
  "carrer_tendencies"
];



async function loadQuestions() {
  try {
    const res = await authenticatedFetch('/assessment/generatequestion', {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        list_category: categories
      })
    });

    if (!res.ok) {
      throw new Error("Failed to generate questions");
    }

    const data = await res.json();

    console.log("API response:", data); 

    assessmentQuestions = buildAssessmentQuestions(data);

    console.log("Built questions:", assessmentQuestions); 

    currentQuestion = 0;
    // askQuestion(currentQuestion);

  } catch (err) {
    console.error("Error fetching questions:", err);
  }
}







  function sendAnswer() {
  const userInput = document.getElementById('userInput');
  const answer = userInput.value.trim();
  if (!answer) return;

 
  addUserMessage(answer);
  const questionObj = assessmentQuestions[currentQuestion];

  // Store answer
  assessmentData.data.push({
    question: questionObj.question,
    answer: answer
  });

  
  userInput.value = '';
  userInput.style.height = 'auto';
  document.getElementById('quickActions').innerHTML = '';
  disableInput();

  // Move to next question
  setTimeout(() => {
    askQuestion(currentQuestion + 1);
  }, 500);
}

loadQuestions();

async function processAssessment() {
    disableInput();
    document.getElementById('quickActions').innerHTML = '';

    showTypingIndicator();

    // addAIMessage("Thank you for completing the assessment! Let me analyze your responses and find the perfect majors for you...");

    try {
        const response = await authenticatedFetch('/assessment/evaluate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                user_data: assessmentData.data
            })
        }); 

        if (response.ok) {
            const results = await response.json();
            console.log("results",results)
            hideTypingIndicator();

            setTimeout(() => {
                showResults(results);
            }, 1500);
            addAIMessage("Thank you for completing the assessment! Let me analyze your responses and find the perfect majors for you...")
        } else {
            hideTypingIndicator();
            addAIMessage("I apologize, but I encountered an error processing your assessment. Please try again.");
            enableInput();
        }
    } catch (error) {
        console.error('Assessment error:', error);
        hideTypingIndicator();
        addAIMessage("I apologize, but I encountered an error.");
    }
}

function showResults(results) {
    const modal = document.getElementById('resultsModal');
    const content = document.getElementById('resultsContent');

    const recommendations = results.recommendations || [];

    let html = '';

    if (recommendations.length === 0) {
        html = '<p>No recommendations available. Please complete your profile for better results.</p>';
    } else {
        recommendations.forEach((major, index) => {
            // const matchPercent = Math.round(major.match_score * 100);

            html += `
                <div class="major-card">
                    <div class="major-header">
                        <h3 class="major-title">${index + 1}. ${major.major_name}</h3>
                        <span class="match-score">${major.match_percentage}% Match</span>
                    </div>
                    
                    <p><strong>Why this major?</strong> </p>
                    
                    <div class="major-meta">
                        <div class="meta-item">
                            <div class="meta-label">Difficulty</div>
                            <div class="meta-value">${major.difficulty_level || 'Medium' }</div>
                        </div>
                        <div class="meta-item">
                            <div class="meta-label">Estimated Cost</div>
                            <div class="meta-value">${major.estimated_cost||'$1800'}</div>
                        </div>
                        <div class="meta-item">
                            <div class="meta-label">Duration</div>
                            <div class="meta-value">${major.study_duration ||'3-4 years'}</div>
                        </div>
                    </div>
                    
                    <p><strong>Career Opportunities:</strong> </p>
                    
                    <div class="roadmap">
                        <h4>📚 Your Study Roadmap:</h4>
                        <ol>
                            ${major.roadmap?.map(step => `<li>${step}</li>`).join('') || '<li> "Complete foundational courses","Develop core skills and knowledge","Gain practical experience through internships","Complete advanced specialization courses"</li>'}
                        </ol>
                    </div>
                </div>
            `;
        });
    }

    content.innerHTML = html;
    modal.classList.add('show');
}
function closeResults() {
    document.getElementById('resultsModal').classList.remove('show');
}

function viewUniversities() {
    window.location.href = '/universities';
}

function scrollToBottom() {
    const chatContainer = document.getElementById('chatContainer');
    chatContainer.scrollTop = chatContainer.scrollHeight;
}
