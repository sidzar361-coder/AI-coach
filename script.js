const SUPABASE_URL = "https://fvgwubrhxlpwyoqkbakm.supabase.co/rest/v1/Signup_Data";
const SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZ2Z3d1YnJoeGxwd3lvcWtiYWttIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODkzNjUyMzAsImV4cCI6MjEwNDk0MTIzMH0.pFQl2ZDwJSj-Vjsp-jvUFCEDmDAmWEWg0Sar_-jTdn8";

const API_BASE_URL = window.AI_COACH_API_URL || "https://interviewai-backend-m02b.onrender.com";
let currentUserEmail = localStorage.getItem("user_email") || "";
let interviewSession = null;
let currentQuestion = null;
let latestScore = 0;
let sessionScores = []; // Tracks scores for all questions answered in the current session
let recognition = null;
let isListening = false;
let pendingTranscript = '';
let interimTranscript = '';
let completedQuestionCount = 0;
let processedFinalResults = new Set();
let recognitionRunning = false;
let submitRequested = false;

// Exact round name mapping matching your UI sidebar items
const ROUND_DISPLAY_NAMES = {
    1: 'Aptitude Round',
    2: 'Project / Managerial Round',
    3: 'Technical Round',
    4: 'Problem-Solving / Behavioral Round'
};

window.addEventListener('load', () => {
    if (currentUserEmail) {
        fetchUserData(currentUserEmail);
    } else {
        document.getElementById("username").innerText = "Candidate";
        document.getElementById("user-email-display").innerText = "Not logged in";
    }

    setTimeout(() => {
        const preloader = document.getElementById('preloader');
        preloader.classList.add('active');

        setTimeout(() => {
            document.querySelector('.container').classList.add('animate-bg');
            preloader.style.display = 'none';
        }, 2100); 

    }, 1200);
});

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
                latestScore = Number(progressVal) || 0;
                
                document.getElementById("progress-val").innerText = `${latestScore}/100`;
                document.getElementById("progress-fill").style.width = `${Math.max(0, Math.min(100, latestScore))}%`;

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

function switchTab(tabName) {
    document.querySelectorAll('.view-panel').forEach(panel => panel.classList.remove('active'));
    document.querySelectorAll('.rounds-list li').forEach(btn => btn.classList.remove('active'));
    
    if (tabName === 'dashboard') {
        document.getElementById('dashboard-view').classList.add('active');
        highlightSidebarButton('Summary & Progress');
    } else {
        document.getElementById('interview-view').classList.add('active');
    }
}

function highlightSidebarButton(roundName) {
    document.querySelectorAll('.rounds-list li').forEach(btn => btn.classList.remove('active'));
    
    const roundMapping = {
        'Summary & Progress': ['Summary & Progress'],
        'Aptitude Round': ['Aptitude Round'],
        'Project / Managerial Round': ['Project / Managerial Round'],
        'Technical Round': ['Technical Round'],
        'Problem-Solving / Behavioral Round': ['Problem-Solving / Behavioral Round']
    };

    const buttons = document.querySelectorAll('.rounds-list li');
    buttons.forEach(btn => {
        const text = btn.innerText.trim();
        for (const [key, aliases] of Object.entries(roundMapping)) {
            if (aliases.some(alias => text.includes(alias)) && key === roundName) {
                btn.classList.add('active');
            }
        }
    });
}

async function startInterview(roundName) {
    highlightSidebarButton(roundName);

    document.getElementById('current-round-title').innerText = roundName;
    switchTab('interview');
    setInterviewStatus("Connecting to the AI interviewer...");
    try {
        await ensureInterviewSession();
        const question = await getNextQuestion();
        completedQuestionCount = interviewSession.previous_questions?.filter(
            q => q.round_number === interviewSession.current_round && q.answered
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
    
    const roundDisplayName = ROUND_DISPLAY_NAMES[interviewSession.current_round] || 'Interview Round';
    document.getElementById('current-round-title').innerText = roundDisplayName;
    highlightSidebarButton(roundDisplayName);
    return currentQuestion;
}

function renderEvaluation(evaluation) {
    if (evaluation.score !== undefined) {
        sessionScores.push(Number(evaluation.score));
    }
    
    // Calculate the average score for all questions asked so far
    if (sessionScores.length > 0) {
        const sum = sessionScores.reduce((acc, curr) => acc + curr, 0);
        latestScore = Math.round(sum / sessionScores.length);
    } else {
        latestScore = Math.round(evaluation.score || 0);
    }

    const strengths = evaluation.strengths?.length ? evaluation.strengths : ['Keep building clear, structured answers.'];
    const weaknesses = evaluation.weaknesses?.length ? evaluation.weaknesses : ['No major gaps identified for this answer.'];
    const topics = evaluation.recommended_topics?.length ? evaluation.recommended_topics : [];
    
    document.getElementById('progress-val').innerText = `${latestScore}/100`;
    document.getElementById('progress-fill').style.width = `${latestScore}%`;

    const improvements = document.getElementById('ai-improvements');
    improvements.replaceChildren();
    
    if (evaluation.feedback) {
        const feedbackItem = document.createElement('li');
        feedbackItem.textContent = evaluation.feedback;
        improvements.appendChild(feedbackItem);
    }

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
    const score = report.overall_score == null ? latestScore : Math.round(report.overall_score);
    latestScore = score;
    document.getElementById('progress-val').innerText = `${score}/100`;
    document.getElementById('progress-fill').style.width = `${score}%`;
    
    const dashboardImprovements = document.getElementById('ai-improvements');
    dashboardImprovements.replaceChildren();

    const summary = document.getElementById('final-summary-card');
    document.getElementById('final-summary-text').innerText = `Overall average score: ${score}/100. ${report.strengths?.length ? `Strongest areas: ${report.strengths.join('; ')}.` : ''}`;
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

    switchTab('dashboard');
    highlightSidebarButton('Summary & Progress');
}

function resetInterviewForRetry() {
    interviewSession = null;
    currentQuestion = null;
    latestScore = 0;
    sessionScores = [];
    completedQuestionCount = 0;
    pendingTranscript = '';
    interimTranscript = '';
    processedFinalResults.clear();
    recognitionRunning = false;
    submitRequested = false;
    setListenButton('Speak Answer (STT)', false);
    localStorage.removeItem('ai_coach_session_id');
    
    document.getElementById('progress-val').innerText = '0/100';
    document.getElementById('progress-fill').style.width = '0%';
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
    setListenButton('Speak Answer (STT)', false);
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
    const reply = `Score ${Math.round(response.evaluation.score)} out of 100. Average score so far: ${latestScore}/100. ${response.evaluation.feedback}`;
    addChatMessage('AI Coach', reply);
    speakText(reply);
    setInterviewStatus('AI feedback is ready. Start another round or continue practising.');
    await persistAiProgress();
    
    if (interviewSession.final_report) {
        renderFinalReport(interviewSession.final_report);
        await persistAiProgress();
        speakText('All interview rounds are complete. Your summary and progress are now ready on the dashboard.');
    } else if (interviewSession.status !== 'completed') {
        try {
            const nextQuestion = await getNextQuestion();
            completedQuestionCount = interviewSession.previous_questions?.filter(
                q => q.round_number === interviewSession.current_round && q.answered
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
    
    const aggregatedFeedbackText = Array.from(document.querySelectorAll('#ai-improvements li'))
        .map(item => item.innerText)
        .join(' ');

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
            Progress_Description: aggregatedFeedbackText || 'No practice feedback recorded yet.'
        })
    });
    if (!response.ok) console.warn('Could not persist AI score to Supabase.');
}

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

function setListenButton(label, recording) {
    const listenBtn = document.getElementById('btn-listen');
    listenBtn.innerText = recording ? '⏹ Submit Answer' : `🎤 ${label}`;
    listenBtn.style.background = recording ? '#ef4444' : '#10b981';
}

function submitPendingTranscript() {
    const transcript = `${pendingTranscript} ${interimTranscript}`.trim();
    pendingTranscript = '';
    interimTranscript = '';
    processedFinalResults.clear();
    submitRequested = false;
    isListening = false;
    setListenButton('Speak Answer (STT)', false);
    if (!transcript) {
        setInterviewStatus('No speech was captured. Click Speak Answer and try again.');
        return;
    }
    addChatMessage('You', transcript);
    submitTranscript(transcript).catch(error => setInterviewStatus(error.message));
}

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
            submitRequested = true;
            if (recognitionRunning) recognition.stop();
            else submitPendingTranscript();
            return;
        }
        if (!currentQuestion) {
            setInterviewStatus('Start a round to generate an AI question.');
            return;
        }
        recognition.start();
        isListening = true;
        recognitionRunning = true;
        submitRequested = false;
        pendingTranscript = '';
        interimTranscript = '';
        processedFinalResults.clear();
        statusText.innerText = "Listening... speak your answer, then click Submit Answer.";
        setListenButton('Submit Answer', true);
    });

    recognition.onresult = (event) => {
        interimTranscript = '';
        for (let index = 0; index < event.results.length; index += 1) {
            const result = event.results[index];
            const text = result[0].transcript.trim();
            if (result.isFinal && !processedFinalResults.has(index)) {
                pendingTranscript = `${pendingTranscript} ${text}`.trim();
                processedFinalResults.add(index);
            } else if (!result.isFinal) {
                interimTranscript = `${interimTranscript} ${text}`.trim();
            }
        }
    };

    recognition.onend = () => {
        recognitionRunning = false;
        if (submitRequested) {
            window.setTimeout(submitPendingTranscript, 250);
        } else if (isListening) {
            setInterviewStatus('Listening... continue speaking when ready, then click Submit Answer.');
            window.setTimeout(() => {
                if (!isListening || submitRequested || recognitionRunning) return;
                try {
                    recognition.start();
                    recognitionRunning = true;
                    processedFinalResults.clear();
                    interimTranscript = '';
                } catch (error) {
                    setInterviewStatus('Recording paused by the browser. Click Submit Answer when finished.');
                }
            }, 250);
        }
    };
    recognition.onerror = (event) => {
        recognitionRunning = false;
        isListening = false;
        submitRequested = false;
        setListenButton('Speak Answer (STT)', false);
        setInterviewStatus(`Speech recognition error: ${event.error}`);
    };
} else {
    document.getElementById('btn-listen').disabled = true;
    setInterviewStatus('Speech recognition is not supported in this browser.');
}

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

function enableRoleChange() {
    document.getElementById('role-dropdown-container').style.display = 'block';
    document.getElementById('btn-edit-role').style.display = 'none';
    document.getElementById('selected-role-display').innerText = "";
    document.getElementById('role-search-input').value = "";
    filterRoles(); 
}

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