const SUPABASE_URL = "https://fvgwubrhxlpwyoqkbakm.supabase.co/rest/v1/Signup_Data";
const SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZ2Z3d1YnJoeGxwd3lvcWtiYWttIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODkzNjUyMzAsImV4cCI6MjEwNDk0MTIzMH0.pFQl2ZDwJSj-Vjsp-jvUFCEDmDAmWEWg0Sar_-jTdn8";

const API_BASE_URL = window.AI_COACH_API_URL || "https://interviewai-backend-m02b.onrender.com";
let currentUserEmail = localStorage.getItem("user_email") || "";
let interviewSession = null;
let currentQuestion = null;
let latestScore = 0;
let recognition = null;
let isListening = false;
let pendingTranscript = '';
let completedQuestionCount = 0;
let lastProcessedResultIndex = 0;

window.addEventListener('load', () => {
    // 1. Fetch user information from Supabase
    if (currentUserEmail) {
        fetchUserData(currentUserEmail);
    } else {
        document.getElementById("username").innerText = "Candidate";
        document.getElementById("user-email-display").innerText = "Not logged in";
    }

    // 2. Start opening the vertical stairs after an initial pause
    setTimeout(() => {
        const preloader = document.getElementById('preloader');
        preloader.classList.add('active'); // Triggers stairs moving UP and DOWN

        // 3. Wait for transition to finish
        setTimeout(() => {
            document.querySelector('.container').classList.add('animate-bg');
            preloader.style.display = 'none';
        }, 2100); 

    }, 1200);
});

// Fetch user data from Supabase
async function fetchUserData(email) {
    try {
        const response = await fetch(`${SUPABASE_URL}?Email_ID=eq.${encodeURIComponent(email)}`, {
            method: 'GET',
            headers: {
                'apikey': SUPABASE_KEY,
                'Authorization': `Bearer ${SUPABASE_KEY}`,
                'Content-Type': 'application/json'
            }
        });

        if (response.ok) {
            const data = await response.json();
            if (data.length > 0) {
                const user = data[0];
                document.getElementById("username").innerText = `${user.First_Name || ''} ${user.Last_Name || ''}`.trim() || 'User';
                document.getElementById("user-email-display").innerText = user.Email_ID;

                const progressVal = user.Progress !== undefined ? user.Progress : 0;
                const progressDesc = user.Progress_Description || "No practice feedback recorded yet.";

                latestScore = Number(progressVal) || 0;
                document.getElementById("progress-val").innerText = `${latestScore}/100`;
                document.getElementById("progress-fill").style.width = `${Math.max(0, Math.min(100, latestScore))}%`;
                document.getElementById("progress-desc").innerText = progressDesc;

                // Handle loading and displaying saved role from database
                if (user.Role) {
                    document.getElementById('selected-role-display').innerText = "Selected Role: " + user.Role;
                    document.getElementById('role-dropdown-container').style.display = 'none';
                    document.getElementById('btn-edit-role').style.display = 'inline-block';
                }
            }
        }
    } catch (err) {
        console.error("Error fetching user data from Supabase:", err);
    }
}

// UI Navigation
function switchTab(tabName) {
    document.querySelectorAll('.view-panel').forEach(panel => panel.classList.remove('active'));
    
    if (tabName === 'dashboard') {
        document.getElementById('dashboard-view').classList.add('active');
    } else {
        document.getElementById('interview-view').classList.add('active');
    }
}

async function startInterview(roundName) {
    document.getElementById('current-round-title').innerText = roundName;
    switchTab('interview');
    setInterviewStatus("Connecting to the AI interviewer...");
    try {
        await ensureInterviewSession();
        const question = await getNextQuestion();
        completedQuestionCount = interviewSession.previous_questions?.filter(
            question => question.round_number === interviewSession.current_round && question.answered
        ).length || 0;
        const greeting = `Welcome to the ${roundName}. Question ${completedQuestionCount + 1} of 7.`;
        addChatMessage("AI Coach", `${greeting} ${question.text}`);
        speakText(`${greeting} ${question.text}`);
    } catch (error) {
        setInterviewStatus(error.message);
        addChatMessage("AI Coach", error.message);
    }
}

function addChatMessage(sender, text) {
    const chatBox = document.getElementById('chat-box');
    const msg = document.createElement('div');
    msg.className = `chat-message ${sender === 'AI Coach' ? 'ai-message' : 'user-message'}`;
    const label = document.createElement('strong');
    label.textContent = `${sender}:`;
    msg.append(label, document.createTextNode(` ${text}`));
    chatBox.appendChild(msg);
    chatBox.scrollTop = chatBox.scrollHeight;
}

function setInterviewStatus(message) {
    document.getElementById('stt-status').innerText = message;
    document.getElementById('ai-status').innerText = message;
}

async function apiRequest(path, options = {}) {
    const response = await fetch(`${API_BASE_URL}${path}`, {
        ...options,
        headers: { 'Content-Type': 'application/json', ...(options.headers || {}) }
    });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) {
        const detail = typeof body.detail === 'string'
            ? body.detail
            : body.detail
                ? JSON.stringify(body.detail)
                : `AI service returned ${response.status}.`;
        throw new Error(detail);
    }
    return body;
}

function getCandidateId() {
    let candidateId = localStorage.getItem('ai_coach_candidate_id');
    if (!candidateId) {
        candidateId = crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random().toString(16).slice(2)}`;
        localStorage.setItem('ai_coach_candidate_id', candidateId);
    }
    return candidateId;
}

function getSessionId() {
    return interviewSession?.session_id || interviewSession?.id;
}

async function ensureInterviewSession() {
    const storedId = localStorage.getItem('ai_coach_session_id');
    if (storedId) {
        try {
            interviewSession = await apiRequest(`/session/${storedId}`);
            return interviewSession;
        } catch (error) {
            localStorage.removeItem('ai_coach_session_id');
        }
    }
    const response = await apiRequest('/session', {
        method: 'POST',
        body: JSON.stringify({ candidate_id: getCandidateId() })
    });
    interviewSession = { ...response.session, session_id: response.session_id };
    localStorage.setItem('ai_coach_session_id', response.session_id);
    return interviewSession;
}

async function getNextQuestion() {
    const sessionId = getSessionId();
    if (!sessionId) throw new Error('Interview session ID is missing. Please start the round again.');
    const response = await apiRequest(`/session/${sessionId}/question`);
    currentQuestion = response.question;
    interviewSession = await apiRequest(`/session/${sessionId}`);
    const roundNames = {
        1: 'Background Round',
        2: 'Project Deep-Dive Round',
        3: 'Technical Knowledge Round',
        4: 'Problem-Solving Round'
    };
    document.getElementById('current-round-title').innerText = roundNames[interviewSession.current_round] || 'Interview Round';
    return currentQuestion;
}

function renderEvaluation(evaluation) {
    latestScore = Math.round(evaluation.score);
    const strengths = evaluation.strengths?.length ? evaluation.strengths : ['Keep building clear, structured answers.'];
    const weaknesses = evaluation.weaknesses?.length ? evaluation.weaknesses : ['No major gaps identified for this answer.'];
    const topics = evaluation.recommended_topics?.length ? evaluation.recommended_topics : [];
    document.getElementById('progress-val').innerText = `${latestScore}/100`;
    document.getElementById('progress-fill').style.width = `${latestScore}%`;
    document.getElementById('progress-desc').innerText = evaluation.feedback || 'AI feedback is ready.';

    const improvements = document.getElementById('ai-improvements');
    improvements.replaceChildren();
    [
        `Strengths: ${strengths.join('; ')}`,
        `Focus next: ${weaknesses.join('; ')}`,
        ...(topics.length ? [`Practice next: ${topics.join(', ')}`] : [])
    ].forEach(summary => {
        const item = document.createElement('li');
        item.textContent = summary;
        improvements.appendChild(item);
    });
}

function renderFinalReport(report) {
    const score = report.overall_score == null ? 0 : Math.round(report.overall_score);
    latestScore = score;
    document.getElementById('progress-val').innerText = `${score}/100`;
    document.getElementById('progress-fill').style.width = `${score}%`;
    document.getElementById('progress-desc').innerText = 'All interview rounds are complete. Your final AI summary is ready.';
    const dashboardImprovements = document.getElementById('ai-improvements');
    dashboardImprovements.replaceChildren();

    const summary = document.getElementById('final-summary-card');
    document.getElementById('final-summary-text').innerText = `Overall score: ${score}/100. ${report.strengths?.length ? `Strongest areas: ${report.strengths.join('; ')}.` : ''}`;
    const improvements = document.getElementById('final-summary-improvements');
    improvements.replaceChildren();
    const items = report.weaknesses?.length ? report.weaknesses : (report.recommendations || []);
    items.slice(0, 5).forEach(text => {
        const item = document.createElement('li');
        item.textContent = text;
        improvements.appendChild(item);
        dashboardImprovements.appendChild(item.cloneNode(true));
    });
    summary.style.display = 'block';
}

function resetInterviewForRetry() {
    interviewSession = null;
    currentQuestion = null;
    latestScore = 0;
    completedQuestionCount = 0;
    pendingTranscript = '';
    lastProcessedResultIndex = 0;
    localStorage.removeItem('ai_coach_session_id');
    document.getElementById('progress-val').innerText = '0/100';
    document.getElementById('progress-fill').style.width = '0%';
    document.getElementById('progress-desc').innerText = 'No completed interview yet.';
    document.getElementById('ai-improvements').replaceChildren();
    document.getElementById('final-summary-card').style.display = 'none';
    document.getElementById('chat-box').innerHTML = '<div class="chat-message ai-message"><strong>AI Coach:</strong> Start a round to receive an AI-generated question.</div>';
    resetStoredProgress();
    switchTab('dashboard');
}

async function resetStoredProgress() {
    if (!currentUserEmail) return;
    await fetch(`${SUPABASE_URL}?Email_ID=eq.${encodeURIComponent(currentUserEmail)}`, {
        method: 'PATCH',
        headers: {
            'apikey': SUPABASE_KEY,
            'Authorization': `Bearer ${SUPABASE_KEY}`,
            'Content-Type': 'application/json',
            'Prefer': 'return=minimal'
        },
        body: JSON.stringify({ Progress: 0, Progress_Description: 'A new interview attempt is ready.' })
    });
}

async function submitTranscript(transcript) {
    if (!currentQuestion || !interviewSession) throw new Error('Start a round before submitting an answer.');
    const sessionId = getSessionId();
    if (!sessionId) throw new Error('Interview session ID is missing. Please start the round again.');
    setInterviewStatus('Sending your answer to the AI evaluator...');
    const response = await apiRequest(`/session/${sessionId}/answer`, {
        method: 'POST',
        body: JSON.stringify({
            question_id: currentQuestion.id,
            question: currentQuestion.text,
            answer: transcript,
            session_version: interviewSession.version
        })
    });
    interviewSession = response.session;
    renderEvaluation(response.evaluation);
    const reply = `Score ${Math.round(response.evaluation.score)} out of 100. ${response.evaluation.feedback}`;
    addChatMessage('AI Coach', reply);
    speakText(reply);
    setInterviewStatus('AI feedback is ready. Start another round or continue practising.');
    await persistAiProgress();
    if (interviewSession.final_report) {
        renderFinalReport(interviewSession.final_report);
        await persistAiProgress();
        switchTab('dashboard');
        speakText('All interview rounds are complete. Your summary is ready on the dashboard.');
    } else if (interviewSession.status !== 'completed') {
        try {
            const nextQuestion = await getNextQuestion();
            completedQuestionCount = interviewSession.previous_questions?.filter(
                question => question.round_number === interviewSession.current_round && question.answered
            ).length || 0;
            const nextText = `Question ${completedQuestionCount + 1} of 7. ${nextQuestion.text}`;
            addChatMessage('AI Coach', nextText);
            speakText(nextText);
        } catch (error) {
            currentQuestion = null;
            setInterviewStatus(error.message);
        }
    } else {
        currentQuestion = null;
    }
}

async function persistAiProgress() {
    if (!currentUserEmail) return;
    const response = await fetch(`${SUPABASE_URL}?Email_ID=eq.${encodeURIComponent(currentUserEmail)}`, {
        method: 'PATCH',
        headers: {
            'apikey': SUPABASE_KEY,
            'Authorization': `Bearer ${SUPABASE_KEY}`,
            'Content-Type': 'application/json',
            'Prefer': 'return=minimal'
        },
        body: JSON.stringify({
            Progress: latestScore,
            Progress_Description: [
                document.getElementById('progress-desc').innerText,
                ...Array.from(document.querySelectorAll('#ai-improvements li')).map(item => item.innerText)
            ].join(' ')
        })
    });
    if (!response.ok) console.warn('Could not persist AI score to Supabase.');
}

/* TTS & STT Functions */
function speakText(text) {
    if ('speechSynthesis' in window) {
        window.speechSynthesis.cancel();
        const utterance = new SpeechSynthesisUtterance(text);
        const voiceSelect = document.getElementById('voice-select');
        const voices = window.speechSynthesis.getVoices();
        if (voiceSelect && voices[voiceSelect.selectedIndex]) {
            utterance.voice = voices[voiceSelect.selectedIndex];
        }
        const pulse = document.getElementById('ai-pulse');
        
        utterance.onstart = () => pulse.classList.add('speaking');
        utterance.onend = () => pulse.classList.remove('speaking');
        
        window.speechSynthesis.speak(utterance);
    }
}

document.getElementById('btn-speak').addEventListener('click', () => {
    if (currentQuestion) speakText(currentQuestion.text);
    else setInterviewStatus('Start a round to generate an AI question.');
});

document.getElementById('btn-retry-interview').addEventListener('click', resetInterviewForRetry);

const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

if (SpeechRecognition) {
    recognition = new SpeechRecognition();
    recognition.lang = 'en-US';
    recognition.continuous = true;
    recognition.interimResults = true;

    const listenBtn = document.getElementById('btn-listen');
    const statusText = document.getElementById('stt-status');

    listenBtn.addEventListener('click', () => {
        if (isListening) {
            recognition.stop();
            isListening = false;
            if (pendingTranscript.trim()) {
                const transcript = pendingTranscript.trim();
                pendingTranscript = '';
                addChatMessage("You", transcript);
                submitTranscript(transcript).catch(error => setInterviewStatus(error.message));
            }
            return;
        }
        if (!currentQuestion) {
            setInterviewStatus('Start a round to generate an AI question.');
            return;
        }
        recognition.start();
        isListening = true;
        lastProcessedResultIndex = 0;
        statusText.innerText = "Listening... Speak now.";
        listenBtn.style.background = "#ef4444";
    });

    recognition.onresult = (event) => {
        const finalText = Array.from(event.results)
            .slice(lastProcessedResultIndex)
            .filter(result => result.isFinal)
            .map(result => result[0].transcript)
            .join(' ')
            .trim();
        lastProcessedResultIndex = event.results.length;
        if (finalText) pendingTranscript = `${pendingTranscript} ${finalText}`.trim();
    };

    recognition.onend = () => {
        listenBtn.style.background = "#10b981";
        if (isListening) {
            setInterviewStatus('Paused. Still listening; continue speaking or press the button to submit.');
            lastProcessedResultIndex = 0;
            try { recognition.start(); } catch (error) { /* The browser is already restarting. */ }
        }
    };
    recognition.onerror = (event) => {
        isListening = false;
        listenBtn.style.background = "#10b981";
        setInterviewStatus(`Speech recognition error: ${event.error}`);
    };
} else {
    document.getElementById('btn-listen').disabled = true;
    setInterviewStatus('Speech recognition is not supported in this browser.');
}

// ==========================================
// Role Selection & Supabase Sync Functions
// ==========================================

// Filter roles dynamically from search bar input
function filterRoles() {
    let input = document.getElementById('role-search-input').value.toLowerCase();
    let container = document.getElementById('role-dropdown-container');
    let options = container.getElementsByClassName('role-option');

    for (let i = 0; i < options.length; i++) {
        let txtValue = options[i].textContent || options[i].innerText;
        if (txtValue.toLowerCase().indexOf(input) > -1) {
            options[i].style.display = "";
        } else {
            options[i].style.display = "none";
        }
    }
}

// Handle selection of a role from the list
function selectRole(role) {
    document.getElementById('selected-role-display').innerText = "Selected Role: " + role;
    document.getElementById('role-dropdown-container').style.display = 'none';
    document.getElementById('btn-edit-role').style.display = 'inline-block';
    
    let otherContainer = document.getElementById('other-role-container');
    if (role === 'Other') {
        otherContainer.style.display = 'block';
    } else {
        otherContainer.style.display = 'none';
        updateRoleInSupabase(role);
    }
}

// Handle saving custom role when "Other" is chosen
function saveCustomRole() {
    let customRole = document.getElementById('custom-role-input').value.trim();
    if (!customRole) {
        alert("Please enter a valid role description.");
        return;
    }
    document.getElementById('selected-role-display').innerText = "Selected Role: " + customRole;
    document.getElementById('other-role-container').style.display = 'none';
    document.getElementById('role-dropdown-container').style.display = 'none';
    document.getElementById('btn-edit-role').style.display = 'inline-block';
    
    updateRoleInSupabase(customRole);
}

// Re-enable role selection view so user can change it
function enableRoleChange() {
    document.getElementById('role-dropdown-container').style.display = 'block';
    document.getElementById('btn-edit-role').style.display = 'none';
    document.getElementById('selected-role-display').innerText = "";
    document.getElementById('role-search-input').value = "";
    filterRoles(); 
}

// Update the user's role field in Supabase database
async function updateRoleInSupabase(roleName) {
    if (!currentUserEmail) {
        alert("User session not found. Please log in again.");
        return;
    }

    try {
        const response = await fetch(`${SUPABASE_URL}?Email_ID=eq.${encodeURIComponent(currentUserEmail)}`, {
            method: "PATCH",
            headers: {
                "apikey": SUPABASE_KEY,
                "Authorization": `Bearer ${SUPABASE_KEY}`,
                "Content-Type": "application/json",
                "Prefer": "return=minimal"
            },
            body: JSON.stringify({ Role: roleName })
        });

        if (response.ok) {
            alert("Role successfully updated in Supabase!");
        } else {
            let err = await response.text();
            console.error("Supabase role update error:", err);
            alert("Failed to save role to database.");
        }
    } catch (error) {
        console.error("Network exception while updating role:", error);
        alert("An error occurred while saving your role.");
    }
}

function logout() {
    localStorage.removeItem("user_email");
    window.location.href = "signin.html";
}

function populateVoices() {
    const voiceSelect = document.getElementById('voice-select');
    if (!voiceSelect || !('speechSynthesis' in window)) return;
    const voices = window.speechSynthesis.getVoices();
    voiceSelect.replaceChildren();
    voices.forEach(voice => {
        const option = document.createElement('option');
        option.textContent = `${voice.name} (${voice.lang})`;
        voiceSelect.appendChild(option);
    });
}

if ('speechSynthesis' in window) {
    populateVoices();
    window.speechSynthesis.onvoiceschanged = populateVoices;
}