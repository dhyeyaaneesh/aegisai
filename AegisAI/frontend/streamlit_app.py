import streamlit as st
import requests
import json

# Page config
st.set_page_config(
    page_title="AegisAI | Scam Detector",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state - AUTH
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'session_id' not in st.session_state:
    st.session_state.session_id = None
if 'username' not in st.session_state:
    st.session_state.username = None
if 'user_id' not in st.session_state:
    st.session_state.user_id = None

# Initialize gamification stats
if 'total_scans' not in st.session_state:
    st.session_state.total_scans = 0
if 'threats_blocked' not in st.session_state:
    st.session_state.threats_blocked = 0
if 'xp_points' not in st.session_state:
    st.session_state.xp_points = 0
if 'quiz_score' not in st.session_state:
    st.session_state.quiz_score = 0
if 'current_question' not in st.session_state:
    st.session_state.current_question = 0
if 'quiz_completed' not in st.session_state:
    st.session_state.quiz_completed = False


# ============== AUTHENTICATION PAGE ==============

def show_auth_page():
    """Display login/signup page"""
    
    st.markdown("""
    <style>
        :root {
            --teal-mid: #54ACBF;
            --teal-light: #A7EBF2;
            --navy: #023859;
            --teal-dark: #26658C;
        }
        
        html, body, .stApp {
            background: linear-gradient(180deg, var(--teal-mid), var(--teal-light)) !important;
        }
        
        .auth-header {
            font-size: 3rem;
            font-weight: bold;
            color: var(--navy);
            text-align: center;
            margin-bottom: 1rem;
        }
        
        .auth-subheader {
            font-size: 1.2rem;
            color: var(--navy);
            text-align: center;
            margin-bottom: 2rem;
        }
        
        .stButton>button {
            width: 100%;
            background: linear-gradient(135deg, var(--teal-dark), var(--navy)) !important;
            color: white !important;
            font-weight: bold !important;
            padding: 0.75rem !important;
            border-radius: 0.5rem !important;
        }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="auth-header">🛡️ Welcome to AegisAI</div>', unsafe_allow_html=True)
    st.markdown('<div class="auth-subheader">Your AI-Powered Shield Against Online Scams</div>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    auth_tab1, auth_tab2 = st.tabs(["🔐 Login", "📝 Sign Up"])
    
    # LOGIN TAB
    with auth_tab1:
        st.markdown("### Login to Your Account")
        
        with st.form("login_form"):
            login_username = st.text_input("Username", key="login_user")
            login_password = st.text_input("Password", type="password", key="login_pass")
            login_submit = st.form_submit_button("Login", use_container_width=True)
            
            if login_submit:
                if login_username and login_password:
                    with st.spinner("Logging in..."):
                        try:
                            response = requests.post(
                                "http://localhost:5000/api/login",
                                json={"username": login_username, "password": login_password},
                                timeout=10
                            )
                            
                            if response.status_code == 200:
                                data = response.json()
                                if data.get('success'):
                                    st.session_state.authenticated = True
                                    st.session_state.session_id = data.get('session_id')
                                    st.session_state.username = data['user']['username']
                                    st.session_state.user_id = data['user']['id']
                                    
                                    # Load stats
                                    st.session_state.xp_points = data['user']['total_xp']
                                    st.session_state.total_scans = data['user']['total_scans']
                                    st.session_state.threats_blocked = data['user']['threats_blocked']
                                    st.session_state.quiz_score = data['user']['quiz_score']
                                    
                                    st.success(f"Welcome back, {st.session_state.username}!")
                                    st.rerun()
                                else:
                                    st.error(data.get('error', 'Login failed'))
                            else:
                                st.error("Invalid username or password")
                        except Exception as e:
                            st.error(f"Connection error: {str(e)}")
                            st.info("Make sure backend is running: `python backend/app.py`")
                else:
                    st.warning("Please enter both username and password")
    
    # SIGNUP TAB
    with auth_tab2:
        st.markdown("### Create New Account")
        
        with st.form("signup_form"):
            signup_username = st.text_input("Username (min 3 characters)", key="signup_user")
            signup_email = st.text_input("Email (optional)", key="signup_email")
            signup_password = st.text_input("Password (min 6 characters)", type="password", key="signup_pass")
            signup_password2 = st.text_input("Confirm Password", type="password", key="signup_pass2")
            signup_submit = st.form_submit_button("Sign Up", use_container_width=True)
            
            if signup_submit:
                if not signup_username or not signup_password:
                    st.warning("Username and password are required")
                elif len(signup_username) < 3:
                    st.warning("Username must be at least 3 characters")
                elif len(signup_password) < 6:
                    st.warning("Password must be at least 6 characters")
                elif signup_password != signup_password2:
                    st.error("Passwords don't match")
                else:
                    with st.spinner("Creating account..."):
                        try:
                            response = requests.post(
                                "http://localhost:5000/api/register",
                                json={
                                    "username": signup_username,
                                    "password": signup_password,
                                    "email": signup_email if signup_email else None
                                },
                                timeout=10
                            )
                            
                            if response.status_code == 200:
                                data = response.json()
                                if data.get('success'):
                                    st.session_state.authenticated = True
                                    st.session_state.session_id = data.get('session_id')
                                    st.session_state.username = data.get('username')
                                    st.success(f"Account created! Welcome, {st.session_state.username}!")
                                    st.rerun()
                                else:
                                    st.error(data.get('error', 'Signup failed'))
                            else:
                                data = response.json()
                                st.error(data.get('error', 'Signup failed'))
                        except Exception as e:
                            st.error(f"Connection error: {str(e)}")
                            st.info("Make sure backend is running: `python backend/app.py`")
    
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #6B7280; margin-top: 2rem;'>
        🛡️ <b>AegisAI</b> - Protecting users from online threats since 2025<br>
        Built with ♡ by Team Foresight Furies
    </div>
    """, unsafe_allow_html=True)


# ============== MAIN APP (Your exact design) ==============

def show_main_app():
    """Display main AegisAI application"""
    
    # Your exact CSS
    st.markdown("""
    <style>

    :root {
        --teal-light: #A7EBF2;
        --teal-mid: #54ACBF;
        --teal-dark: #26658C;
        --navy: #023859;
        --deep-navy: #011C40;
        --tab-selected: #4A2C82;
        --sidebar-text: #d2f6fa;
    }

    html, body, .main, .stApp {
        background: linear-gradient(180deg, var(--teal-mid), var(--teal-light)) !important;
        color: var(--deep-navy) !important;
    }

    .main-header {
        font-size: 3.5rem !important;
        font-weight: bold !important;
        color: var(--navy) !important;
        text-align: center !important;
        margin-bottom: 0.25rem !important;
    }

    .sub-header {
        font-size: 1.3rem !important;
        color: #023859 !important;
        text-align: center !important;
        display: block !important;
        width: 100% !important;
        margin: 0 auto 2rem auto !important;
    }

    .stButton>button {
        width: 100%;
        background: linear-gradient(135deg, var(--teal-dark), var(--navy)) !important;
        color: var(--sidebar-text) !important;
        font-weight: bold !important;
        padding: 0.75rem !important;
        border-radius: 0.5rem !important;
        border: none !important;
        font-size: 1.1rem !important;
        transition: transform 0.2s, box-shadow 0.2s !important;
    }
    .stButton>button:hover {
        transform: scale(1.05) !important;
        box-shadow: 0 0 15px rgba(2, 56, 89, 0.4) !important;
    }

    section[data-testid="stSidebar"], div[data-testid="stSidebar"] {
        background-color: var(--teal-dark) !important;
    }

    section[data-testid="stSidebar"], section[data-testid="stSidebar"] * {
        color: var(--sidebar-text) !important;
    }

    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3,
    section[data-testid="stSidebar"] p {
        color: var(--sidebar-text) !important;
    }

    section[data-testid="stSidebar"] a {
        color: var(--deep-navy) !important;
        font-weight: 500 !important;
        text-decoration: none !important;
    }
    section[data-testid="stSidebar"] a:hover {
        color: white !important;
        text-decoration: underline !important;
    }

    div[data-baseweb="tab-list"] {
        background-color: rgba(255,255,255,0.1) !important;
        border-radius: 8px !important;
    }
    div[data-baseweb="tab"] {
        color: var(--navy) !important;
        font-weight: 500 !important;
    }
    div[data-baseweb="tab"][aria-selected="true"] {
        background-color: var(--tab-selected) !important;
        color: white !important;
        border-radius: 6px !important;
        border-bottom: 3px solid var(--tab-selected) !important;
    }

    .xp-badge {
        background: linear-gradient(135deg, var(--tab-selected), #2B1859) !important;
        color: white !important;
        padding: 0.4rem 1rem !important;
        border-radius: 2rem !important;
        font-weight: bold !important;
    }

    div[data-testid="stMetricValue"] {
        color: var(--navy) !important;
        font-weight: bold !important;
    }
    div[data-testid="stMetricLabel"] {
        color: var(--teal-dark) !important;
    }

    section.main div[data-testid="stMarkdownContainer"] p {
        color: #023859 !important;
    }

    section.main .stButton > button,
    section.main .stButton > button * {
        color: #d2f6fa !important;
        fill: #d2f6fa !important;
        stroke: #d2f6fa !important;
    }

    header[data-testid="stHeader"] {
        background-color: #27445c !important;
    }

    header[data-testid="stHeader"] button,
    header[data-testid="stHeader"] button *,
    header[data-testid="stHeader"] span,
    header[data-testid="stHeader"] div {
        color: #d2f6fa !important;
    }

    </style>
    """, unsafe_allow_html=True)

    # Header
    st.markdown('<div class="main-header">🛡️ AegisAI</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Your AI-Powered Shield Against Online Scams</div>', unsafe_allow_html=True)

    # Backend check
    try:
        response = requests.get("http://localhost:5000/api/health", timeout=2)
        if response.status_code != 200:
            st.warning("⚠️ Backend connection issue")
    except:
        st.error("❌ Cannot connect to backend!")
        st.stop()

    st.markdown("---")

    # Display results function
    def display_results(result):
        """Display analysis results"""
        st.markdown("---")
        st.markdown("## Analysis Results")
        
        risk_level = result.get('risk_level', 'UNKNOWN')
        risk_score = result.get('risk_score', 0)
        status = result.get('status', 'UNKNOWN')
        
        # Update stats
        st.session_state.total_scans += 1
        if risk_level in ["HIGH", "MEDIUM"]:
            st.session_state.threats_blocked += 1
            st.session_state.xp_points += 20
            st.balloons()
        else:
            st.session_state.xp_points += 10
        
        # Sync with backend
        if st.session_state.user_id:
            try:
                requests.post(
                    "http://localhost:5000/api/update-stats",
                    json={
                        "user_id": st.session_state.user_id,
                        "xp_gained": 20 if risk_level in ["HIGH", "MEDIUM"] else 10,
                        "scan_increment": 1,
                        "threat_increment": 1 if risk_level in ["HIGH", "MEDIUM"] else 0
                    },
                    timeout=5
                )
            except:
                pass
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("🎯 Risk Level", risk_level)
        with col2:
            st.metric("📊 Risk Score", f"{risk_score}%")
        with col3:
            st.metric("📍 Status", status)
        
        xp_earned = 20 if risk_level in ["HIGH", "MEDIUM"] else 10
        st.markdown(f'<div class="xp-badge">+{xp_earned} XP Earned! 🌟</div>', unsafe_allow_html=True)
        
        if risk_level == "HIGH":
            st.error("### HIGH RISK DETECTED")
            st.markdown(result.get('explanation', ''))
        elif risk_level == "MEDIUM":
            st.warning("### MEDIUM RISK")
            st.markdown(result.get('explanation', ''))
        else:
            st.success("### LOW RISK")
            st.markdown(result.get('explanation', ''))
        
        if 'warning_signs' in result and result['warning_signs']:
            st.markdown("### Red Flags Detected")
            for warning in result['warning_signs']:
                st.write(f"• {warning}")
        
        if 'safety_tips' in result and result['safety_tips']:
            st.markdown("### How to Stay Safe")
            for tip in result['safety_tips']:
                st.write(f"✓ {tip}")
        
        if result.get('google_threat'):
            st.error(f"**Google Safe Browsing Alert:** Flagged as **{result['google_threat']}**")

    # TABS
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["Check URL", "Check Message", "Check Email", "Voice Call", "Quiz", "Dashboard"])    
    # TAB 1: URL Checker
    with tab1:
        st.markdown("### Enter a Suspicious Link")
        st.write("Paste any URL you're unsure about")
        
        url_input = st.text_input("URL:", placeholder="https://example.com/suspicious", key="url_input", label_visibility="collapsed")
        
        if st.button("Analyze URL", key="url_button", use_container_width=True):
            if url_input:
                with st.spinner("🔎 Scanning URL..."):
                    try:
                        response = requests.post("http://localhost:5000/api/check-url", json={"url": url_input}, timeout=20)
                        if response.status_code == 200:
                            result = response.json()
                            display_results(result)
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
            else:
                st.warning("Please enter a URL")
        
        with st.expander("Try example URLs"):
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Test Safe URL", key="safe_url"):
                    st.code("https://www.google.com")
            with col2:
                if st.button("Test Suspicious", key="sus_url"):
                    st.code("http://192.168.1.1/verify-urgent")
    
    # TAB 2: Message Checker
    with tab2:
        st.markdown("### Paste a Suspicious Message")
        st.write("Copy and paste any message you think might be a scam")
        
        text_input = st.text_area("Message:", height=200, placeholder="URGENT! Your account will be suspended...", key="text_input", label_visibility="collapsed")
        
        if st.button("Analyze Message", key="text_button", use_container_width=True):
            if text_input:
                with st.spinner("🔎 Analyzing..."):
                    try:
                        response = requests.post("http://localhost:5000/api/check-text", json={"text": text_input}, timeout=15)
                        if response.status_code == 200:
                            result = response.json()
                            display_results(result)
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
            else:
                st.warning("Please enter message text")
    
    # TAB 3: Email Checker
    with tab3:
        st.markdown("### Verify Email Legitimacy")
        st.write("Check if an email is a phishing attempt")
        
        col1, col2 = st.columns(2)
        with col1:
            sender_email = st.text_input("Sender Email:", placeholder="support@paypal.com")
        with col2:
            subject_line = st.text_input("Subject:", placeholder="Verify your account")
        
        email_body = st.text_area("Email Body:", height=250, placeholder="Dear customer...", help="Paste full email content")
        
        if st.button("Analyze Email", key="email_button", use_container_width=True):
            if sender_email or email_body:
                with st.spinner("🔎 Checking..."):
                    try:
                        payload = {"email": sender_email, "subject": subject_line, "body": email_body}
                        response = requests.post("http://localhost:5000/api/check-email", json=payload, timeout=25)
                        if response.status_code == 200:
                            result = response.json()
                            display_results(result)
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
            else:
                st.warning("Enter at least sender email or body")
        
        with st.expander("Email Safety Tips"):
            st.markdown("""
            **Common Phishing Signs:**
            - Free email for business
            - Generic greetings
            - Urgent language
            - Requests for passwords
            - Poor grammar
            """)
    # TAB 4: Voice Call Checker
    with tab4:
        st.markdown("### 🎤 Analyze Voice Call Recording")
        st.write("Upload a recorded call to check for scam indicators")
        
        # File uploader
        audio_file = st.file_uploader(
            "Upload Audio File",
            type=['mp3', 'wav', 'm4a', 'ogg', 'flac', 'webm'],
            help="Supported formats: MP3, WAV, M4A, OGG, FLAC, WEBM",
            key="voice_uploader"
        )
        
        if audio_file is not None:
            # Show file details
            st.info(f"📁 **File:** {audio_file.name} ({audio_file.size / 1024:.1f} KB)")
            
            # Audio player
            st.audio(audio_file, format=f'audio/{audio_file.name.split(".")[-1]}')
            
            st.markdown("---")
            
            if st.button("🔍 Analyze Voice Call", key="voice_button", use_container_width=True):
                with st.spinner("🎤 Transcribing and analyzing call..."):
                    try:
                        # Prepare file for upload
                        files = {'audio': (audio_file.name, audio_file, f'audio/{audio_file.name.split(".")[-1]}')}
                        
                        # Send to backend
                        response = requests.post(
                            "http://localhost:5000/api/check-voice",
                            files=files,
                            timeout=60  # Voice processing takes longer
                        )
                        
                        if response.status_code == 200:
                            result = response.json()
                            
                            # Display transcript first
                            st.markdown("---")
                            st.markdown("### 📝 Call Transcript")
                            with st.expander("View Full Transcript", expanded=True):
                                st.text_area(
                                    "Transcribed Text:",
                                    value=result.get('transcript', 'No transcript available'),
                                    height=200,
                                    key="transcript_display",
                                    disabled=True
                                )
                            
                            # Display analysis results
                            display_results(result)
                            
                        elif response.status_code == 503:
                            st.error("❌ Voice analysis not configured")
                            st.info("💡 Backend needs OPENAI_API_KEY in .env file")
                        else:
                            error_data = response.json()
                            st.error(f"Error: {error_data.get('message', 'Unknown error')}")
                    
                    except requests.exceptions.Timeout:
                        st.error("⏱️ Request timed out - file may be too large or backend is slow")
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
                        st.info("Make sure backend is running with OpenAI API key configured")
        
        else:
            st.info("👆 Upload an audio file to begin analysis")
        
        st.markdown("---")
        
        # Voice Call Safety Tips
        with st.expander("🛡️ Phone Scam Warning Signs"):
            st.markdown("""
            **Common Phone Scam Tactics:**
            - 🚨 Claims to be from IRS, Social Security, or law enforcement
            - ⚡ Creates urgency ("Act now or face arrest!")
            - 💰 Demands payment via gift cards or wire transfer
            - 🔒 Asks for passwords, SSN, or banking info
            - 🎭 Caller ID spoofing (fake numbers)
            - 🖥️ "Tech support" for viruses you don't have
            - 👴 Targets elderly with "grandchild in trouble" scams
            
            **What to Do:**
            ✅ Hang up immediately if suspicious
            ✅ Call back using official number from company website
            ✅ Never give personal info over unsolicited calls
            ✅ Report scam calls to FTC or local authorities
            """)
        
        with st.expander("💡 How Voice Analysis Works"):
            st.markdown("""
            **Our AI analyzes:**
            1. **Transcription** - Converts speech to text using OpenAI Whisper
            2. **Keyword Detection** - Identifies scam-related phrases
            3. **Pressure Tactics** - Detects urgency and threats
            4. **Impersonation** - Flags fake government/company claims
            5. **Payment Requests** - Warns about suspicious payment methods
            
            **Note:** Analysis accuracy depends on audio quality and clarity.
            """)
    
    # TAB 5: Quiz
    with tab5:
        st.markdown("### Cybersecurity Quiz")
        st.write("Test your knowledge and earn XP!")
        
        if 'quiz_questions' not in st.session_state:
            try:
                quiz_response = requests.get("http://localhost:5000/api/quiz", timeout=5)
                if quiz_response.status_code == 200:
                    st.session_state.quiz_questions = quiz_response.json()
                else:
                    st.error("Unable to load quiz")
                    st.session_state.quiz_questions = None
            except Exception as e:
                st.error(f"Error: {str(e)}")
                st.session_state.quiz_questions = None
        
        if st.session_state.quiz_questions:
            questions = st.session_state.quiz_questions
            
            if not st.session_state.quiz_completed:
                current_q = st.session_state.current_question
                
                if current_q < len(questions):
                    q = questions[current_q]
                    
                    st.markdown(f"### Question {current_q + 1} of {len(questions)}")
                    st.markdown(f"**{q['question']}**")
                    
                    answer = st.radio("Select answer:", q['options'], key=f"q_{current_q}")
                    
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        if st.button("Submit", key=f"submit_{current_q}", use_container_width=True):
                            selected_index = q['options'].index(answer)
                            
                            if selected_index == q['correct']:
                                st.success("✅ Correct! " + q['explanation'])
                                st.session_state.quiz_score += 1
                                st.session_state.xp_points += 15
                                st.balloons()
                            else:
                                st.error("❌ Incorrect. " + q['explanation'])
                                st.session_state.xp_points += 5
                            
                            st.session_state.current_question += 1
                            
                            if st.session_state.current_question >= len(questions):
                                st.session_state.quiz_completed = True
                            
                            # Sync quiz score
                            if st.session_state.user_id:
                                try:
                                    requests.post(
                                        "http://localhost:5000/api/update-stats",
                                        json={
                                            "user_id": st.session_state.user_id,
                                            "xp_gained": 15 if selected_index == q['correct'] else 5,
                                            "quiz_score_increment": 1 if selected_index == q['correct'] else 0
                                        },
                                        timeout=5
                                    )
                                except:
                                    pass
                            
                            import time
                            time.sleep(1.5)
                            st.rerun()
                    
                    with col2:
                        st.metric("Progress", f"{current_q + 1}/{len(questions)}")
                
                else:
                    st.session_state.quiz_completed = True
                    st.rerun()
            
            else:
                score = st.session_state.quiz_score
                total = len(questions)
                percentage = (score / total) * 100
                
                st.markdown("## 🎉 Quiz Complete!")
                st.markdown(f"### Your Score: {score}/{total} ({percentage:.0f}%)")
                
                if 'quiz_bonus_awarded' not in st.session_state:
                    if percentage >= 80:
                        st.success("🏆 Excellent!")
                        bonus_xp = 50
                    elif percentage >= 60:
                        st.info("👍 Good job!")
                        bonus_xp = 30
                    else:
                        st.warning("📚 Keep studying!")
                        bonus_xp = 10
                    
                    st.markdown(f'<div class="xp-badge">+{bonus_xp} Bonus XP! 🌟</div>', unsafe_allow_html=True)
                    st.session_state.xp_points += bonus_xp
                    st.session_state.quiz_bonus_awarded = True
                
                st.markdown("---")
                st.markdown("### Review Answers")
                for i, q in enumerate(questions):
                    with st.expander(f"Q{i + 1}: {q['question']}"):
                        st.write(f"**Answer:** {q['options'][q['correct']]}")
                        st.write(f"**Why:** {q['explanation']}")
                
                st.markdown("---")
                if st.button("🔄 Retake Quiz", use_container_width=True):
                    st.session_state.quiz_completed = False
                    st.session_state.current_question = 0
                    st.session_state.quiz_score = 0
                    st.session_state.quiz_bonus_awarded = False
                    del st.session_state.quiz_questions
                    st.rerun()
        else:
            st.warning("Quiz unavailable. Check backend.")
            if st.button("🔄 Retry"):
                if 'quiz_questions' in st.session_state:
                    del st.session_state.quiz_questions
                st.rerun()
    
    # TAB 6: Dashboard
    with tab6:
        st.markdown("### 📊 Your Stats")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("🔍 Scans", st.session_state.total_scans)
        with col2:
            st.metric("🛡️ Threats Blocked", st.session_state.threats_blocked)
        with col3:
            st.metric("⭐ XP", st.session_state.xp_points)
        with col4:
            level = st.session_state.xp_points // 50 + 1
            st.metric("🏆 Level", level)
        
        st.markdown("---")
        
        # Progress bar
        level = st.session_state.xp_points // 50 + 1
        current_xp = st.session_state.xp_points % 50
        progress = current_xp / 50
        
        st.markdown(f"### 🌟 Progress to Level {level + 1}")
        st.progress(progress)
        st.caption(f"{current_xp}/50 XP")
        
        st.markdown("---")
        st.markdown("### 🎯 Common Scams We Detect")
        
        col1, col2 = st.columns(2)
        
        with col1:
            with st.expander("🎣 Phishing"):
                st.write("Fake emails from banks")
            with st.expander("💸 Prize Scams"):
                st.write("You won money you never entered for")
            with st.expander("🔒 Account Suspension"):
                st.write("Threats to close your account")
        
        with col2:
            with st.expander("💳 Payment Fraud"):
                st.write("Requests for card info")
            with st.expander("📦 Fake Delivery"):
                st.write("Phony package notifications")
            with st.expander("👨‍💼 Impersonation"):
                st.write("Pretending to be trusted brands")
        
        st.markdown("---")
        
        # Leaderboard
        st.markdown("### 🏆 Leaderboard")
        try:
            leaderboard = requests.get("http://localhost:5000/api/leaderboard?limit=10", timeout=5)
            if leaderboard.status_code == 200:
                data = leaderboard.json()
                if data:
                    for entry in data[:5]:
                        st.write(f"**#{entry['rank']}** {entry['username']} - Level {entry['level']} ({entry['xp']} XP)")
                else:
                    st.info("Be the first on the leaderboard!")
        except:
            st.warning("Leaderboard unavailable")
    
    # SIDEBAR
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state.username}")
        st.markdown("---")
        st.markdown("### Quick Stats")
        st.markdown(f"**Level:** {st.session_state.xp_points // 50 + 1}")
        st.markdown(f"**XP:** {st.session_state.xp_points}")
        st.markdown(f"**Scans:** {st.session_state.total_scans}")
        st.markdown(f"**Quiz:** {st.session_state.quiz_score}/5")
        
        st.markdown("---")
        
        if st.button(" Logout", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.session_id = None
            st.session_state.username = None
            st.session_state.user_id = None
            st.rerun()
        
        st.markdown("---")
        st.markdown("###  Learn More")
        st.markdown("• [FTC Scam Alerts](https://consumer.ftc.gov/scams)")
        st.markdown("• [FBI IC3](https://www.ic3.gov/)")
        st.markdown("• [Stay Safe Online](https://staysafeonline.org/)")
        
        st.markdown("---")
        st.markdown("###  Team Foresight Furies")
        st.write("• Riya (CSE)")
        st.write("• Dhyeya (AIML)")
        st.write("• Anvi (ECE)")
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #6B7280;'>
        🛡️ <b>AegisAI</b> - Protecting users since 2025<br>
        Built with ♡ by Team Foresight Furies<br><br>
        <small>**Disclaimer: This site does not guarantee complete accuracy. Exercise caution before clicking any URL.**</small>
    </div>
    """, unsafe_allow_html=True)


# ============== MAIN ROUTING ==============

if st.session_state.authenticated:
    show_main_app()
else:
    show_auth_page()
