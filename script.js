const SUPABASE_URL = "https://fvgwubrhxlpwyoqkbakm.supabase.co/rest/v1/Signup_Data";
const SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZ2Z3d1YnJoeGxwd3lvcWtiYWttIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODkzNjUyMzAsImV4cCI6MjEwNDk0MTIzMH0.pFQl2ZDwJSj-Vjsp-jvUFCEDmDAmWEWg0Sar_-jTdn8";

let currentUserEmail = localStorage.getItem("user_email") || "";

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

        // 3. Wait for the 1.5s stair transition + stagger delays to finish
        setTimeout(() => {
            // Start the container background effect
            document.querySelector('.container').classList.add('animate-bg');
            
            // Remove preloader screen entirely
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

                document.getElementById("progress-val").innerText = `${progressVal}%`;
                document.getElementById("progress-fill").style.width = `${progressVal}%`;
                document.getElementById("progress-desc").innerText = progressDesc;
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

    const newProgress = 50;
    const newDesc = "Completed Technical Round. Excellent articulation, but need to work on system design scalability.";

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
            alert("Progress saved to Supabase!");
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

function startInterview(roundName) {
    document.getElementById('current-round-title').innerText = roundName;
    switchTab('interview');
    
    const greeting = `Welcome to the ${roundName}. Please begin when ready.`;
    addChatMessage("AI Coach", greeting);
    speakText(greeting);
}

function addChatMessage(sender, text) {
    const chatBox = document.getElementById('chat-box');
    const msg = document.createElement('div');
    msg.className = `chat-message ${sender === 'AI Coach' ? 'ai-message' : 'user-message'}`;
    msg.innerHTML = `<strong>${sender}:</strong> ${text}`;
    chatBox.appendChild(msg);
    chatBox.scrollTop = chatBox.scrollHeight;
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
    const question = "How do you handle database index optimization for high-throughput reads?";
    addChatMessage("AI Coach", question);
    speakText(question);
});

const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

if (SpeechRecognition) {
    const recognition = new SpeechRecognition();
    recognition.lang = 'en-US';

    const listenBtn = document.getElementById('btn-listen');
    const statusText = document.getElementById('stt-status');

    listenBtn.addEventListener('click', () => {
        recognition.start();
        statusText.innerText = "Listening... Speak now.";
        listenBtn.style.background = "#ef4444";
    });

    recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        addChatMessage("You", transcript);
        statusText.innerText = "Speech recognized.";
        listenBtn.style.background = "#10b981";
        
        setTimeout(() => {
            const reply = "Great response. Let's move forward.";
            addChatMessage("AI Coach", reply);
            speakText(reply);
        }, 1000);
    };

    recognition.onend = () => {
        listenBtn.style.background = "#10b981";
    };
}

function logout() {
    // Clear user session from storage
    localStorage.removeItem("user_email");
    
    // Redirect user to the sign-in page
    window.location.href = "signin.html";
}