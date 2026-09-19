const SUPABASE_URL = "https://fvgwubrhxlpwyoqkbakm.supabase.co/rest/v1/Signup_Data";
const SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZ2Z3d1YnJoeGxwd3lvcWtiYWttIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODkzNjUyMzAsImV4cCI6MjEwNDk0MTIzMH0.pFQl2ZDwJSj-Vjsp-jvUFCEDmDAmWEWg0Sar_-jTdn8";

const API_BASE_URL = window.AI_COACH_API_URL || "https://interviewai-backend-m02b.onrender.com";
let currentUserEmail = localStorage.getItem("user_email") || "";
let interviewSession = null;
let currentQuestion = null;
let latestScore = 0;
let recognition = null;
let isListening = false;

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

// Save progress to Supabase
async function saveSessionProgress() {
    if (!currentUserEmail) {
        alert("User session not found!");
        return;
    }

    const newProgress = latestScore;
    const newDesc = document.getElementById("progress-desc").innerText;

    try {
        const response = await fetch(`${SUPABASE_URL}?Email_ID=eq.${encodeURIComponent(currentUserEmail)}`, {
            method: 'PATCH',
            headers: {
                'apikey': SUPABASE_KEY,
                'Authorization': `Bearer ${SUPABASE_KEY}`,
                'Content-Type': 'application/json',
                'Prefer': 'return=minimal'
            },
            body: JSON.stringify({
                "Progress": newProgress,
                "Progress_Description": newDesc
            })
        });

        if (response.ok) {
            alert("AI score and improvement feedback saved to Supabase!");
            fetchUserData(currentUserEmail);
        } else {
            alert("Failed to save progress.");
        }
    } catch (err) {
        console.error("Error saving progress:", err);
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
        const greeting = `Welcome to the ${roundName}.`;
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
    interviewSession = response.session;
    localStorage.setItem('ai_coach_session_id', response.session_id);
    return interviewSession;
}

async function getNextQuestion() {
    const response = await apiRequest(`/session/${interviewSession.session_id}/question`);
    currentQuestion = response.question;
    interviewSession = await apiRequest(`/session/${interviewSession.session_id}`);
    return currentQuestion;
}

function renderEvaluation(evaluation) {
    latestScore = Math.round(evaluation.score);
    const strengths = evaluation.strengths?.length ? evaluation.strengths.join('; ') : 'Keep building clear, structured answers.';
    const weaknesses = evaluation.weaknesses?.length ? evaluation.weaknesses.join('; ') : 'No major gaps identified for this answer.';
    const topics = evaluation.recommended_topics?.length ? ` Recommended practice: ${evaluation.recommended_topics.join(', ')}.` : '';
    const description = `${evaluation.feedback} Strengths: ${strengths} Areas to improve: ${weaknesses}.${topics}`;
    document.getElementById('progress-val').innerText = `${latestScore}/100`;
    document.getElementById('progress-fill').style.width = `${latestScore}%`;
    document.getElementById('progress-desc').innerText = description;
    document.getElementById('ai-improvements').innerText = `Improve next: ${weaknesses}`;
}

async function submitTranscript(transcript) {
    if (!currentQuestion || !interviewSession) throw new Error('Start a round before submitting an answer.');
    setInterviewStatus('Sending your answer to the AI evaluator...');
    const response = await apiRequest(`/session/${interviewSession.session_id}/answer`, {
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
    if (interviewSession.status !== 'completed') {
        try {
            const nextQuestion = await getNextQuestion();
            addChatMessage('AI Coach', nextQuestion.text);
            speakText(nextQuestion.text);
        } catch (error) {
            currentQuestion = null;
            setInterviewStatus(error.message);
        }
    } else {
        currentQuestion = null;
    }
}

async function persistAiProgress() {
    if (!currentUserEmail || !latestScore) return;
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
            Progress_Description: document.getElementById('progress-desc').innerText
        })
    });
    if (!response.ok) console.warn('Could not persist AI score to Supabase.');
}

/* TTS & STT Functions */
function speakText(text) {
    if ('speechSynthesis' in window) {
        window.speechSynthesis.cancel();
        const utterance = new SpeechSynthesisUtterance(text);
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

const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

if (SpeechRecognition) {
    recognition = new SpeechRecognition();
    recognition.lang = 'en-US';
    recognition.continuous = false;
    recognition.interimResults = true;

    const listenBtn = document.getElementById('btn-listen');
    const statusText = document.getElementById('stt-status');

    listenBtn.addEventListener('click', () => {
        if (isListening) {
            recognition.stop();
            return;
        }
        if (!currentQuestion) {
            setInterviewStatus('Start a round to generate an AI question.');
            return;
        }
        recognition.start();
        isListening = true;
        statusText.innerText = "Listening... Speak now.";
        listenBtn.style.background = "#ef4444";
    });

    recognition.onresult = (event) => {
        const transcript = Array.from(event.results).map(result => result[0].transcript).join(' ').trim();
        if (event.results[event.results.length - 1].isFinal && transcript) {
            addChatMessage("You", transcript);
            submitTranscript(transcript).catch(error => setInterviewStatus(error.message));
        }
    };

    recognition.onend = () => {
        isListening = false;
        listenBtn.style.background = "#10b981";
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