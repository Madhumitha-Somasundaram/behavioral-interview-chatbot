from streamlit_webrtc import webrtc_streamer,WebRtcMode,VideoProcessorBase
from interview_engine import InterviewEngine  
from db_schema import initialize_tables
from datetime import datetime,timedelta
from resume_parser import parse_resume 
from collections import Counter 
from sqlalchemy import text 
from database_connection import engine
from fer import FER
import streamlit as st
import tempfile
import whisper
import bcrypt
import queue
import json
import uuid
import time
import os
import av
import cv2


st.set_page_config(page_title="Behaview",page_icon="/Users/madhumithas/Downloads/Projects/InterviewChatBot/logo.png",  layout="wide")
st.markdown(
    """
    <link href="https://fonts.googleapis.com/css2?family=Inter&display=swap" rel="stylesheet">
    """,
    unsafe_allow_html=True
)
st.sidebar.markdown(
    """
    <h1 style='
        font-family: "Inter", sans-serif; 
        font-size: 50px; 
        color: #023E42; 
        text-align: center;
        margin-bottom: 10px;
    '>Behaview</h1>
    """,
    unsafe_allow_html=True
)

st.html(
                        """
                    <style>
                        .stChatInput div {
                            min-height: 70px
                        }
                    </style>
                        """
                    )

initialize_tables()


@st.cache_resource
def load_fer():
    return FER(mtcnn=True)
detector = load_fer()

def save_emotion(emotion):
    with open("emotions.txt", "a") as f:
        f.write(emotion + "\n")
        #print(emotion)
def read_emotions():
    with open("emotions.txt", "r") as f:
        return [line.strip() for line in f.readlines()]
def reset_emotions():
    if os.path.exists("emotions.txt"):
        open("emotions.txt", "w").close()

def reset_question_number():
    st.session_state.current_question_number = 1
    st.session_state.webcam_last_active = time.time()
def log_asked_question(username, question):
    resume_hash = st.session_state.engine.get_resume_hash()
    now = datetime.now()
    with engine.begin() as conn:
        try:
            conn.execute(
                text("""
                    INSERT IGNORE INTO asked_questions (username, resume_hash, question, asked_at)
                    VALUES (:username, :resume_hash, :question, :asked_at)
                """),
                {
                    "username": username,
                    "resume_hash": resume_hash,
                    "question": question,
                    "asked_at": now
                }
            )
        except Exception as e:
            print("Error logging asked question:", e)


def add_user(username, password):
    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    try:
        with engine.begin() as conn:
            conn.execute(
                text("INSERT INTO candidate_details (username, password_hash) VALUES (:username, :password_hash)"),
                {"username": username, "password_hash": password_hash}
            )
        return True
    except Exception as e:
        print("Error adding user:", e)
        return False

def verify_user(username, password):
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT password_hash FROM candidate_details WHERE username = :username"),
            {"username": username}
        ).fetchone()
    if result:
        stored_hash = result[0].encode()
        return bcrypt.checkpw(password.encode(), stored_hash)
    return False

def save_interview_session(session_id, username, resume_text, conversation, interview_done):
    conversation_json = json.dumps(conversation)
    now = datetime.now()
    with engine.begin() as conn:
        existing = conn.execute(
            text("SELECT id FROM interview_sessions WHERE session_id = :session_id"),
            {"session_id": session_id}
        ).fetchone()
        if existing:
            conn.execute(
                text("""
                    UPDATE interview_sessions
                    SET conversation = :conversation, interview_done = :interview_done
                    WHERE session_id = :session_id
                """),
                {"conversation": conversation_json, "interview_done": interview_done, "session_id": session_id}
            )
        else:
            conn.execute(
                text("""
                    INSERT INTO interview_sessions (session_id, username, created_at, resume_text, conversation, interview_done)
                    VALUES (:session_id, :username, :created_at, :resume_text, :conversation, :interview_done)
                """),
                {
                    "session_id": session_id,
                    "username": username,
                    "created_at": now,
                    "resume_text": resume_text,
                    "conversation": conversation_json,
                    "interview_done": interview_done
                }
            )

def fetch_interview_sessions(username):
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT session_id, created_at FROM interview_sessions WHERE username = :username ORDER BY created_at DESC"),
            {"username": username}
        ).fetchall()
    return rows

def fetch_interview_conversation(session_id):
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT conversation, resume_text, interview_done FROM interview_sessions WHERE session_id = :session_id"),
            {"session_id": session_id}
        ).fetchone()
    if row:
        conversation = json.loads(row[0]) if row[0] else []
        resume_text = row[1]
        interview_done = row[2]
        return conversation, resume_text, interview_done
    return [], None, False

emotion_queue = queue.Queue()
def save_session():
    if (st.session_state.engine and not st.session_state.interview_done and st.session_state.session_id):
            
            save_interview_session(
                st.session_state.session_id,
                st.session_state.username,
                st.session_state.resume_text,
                st.session_state.messages,
                interview_done=True,
            )
    new_session_id = str(uuid.uuid4())
    st.session_state.session_id = new_session_id
    st.session_state.active_session_id = new_session_id
    st.session_state.messages = []
    st.session_state.engine = None
    st.session_state.interview_done = False
    st.session_state.resume_text = None
    st.session_state.question_emotions = {}
    st.session_state.viewing_session = False
    reset_question_number()
    
    st.rerun()

def signup():
    st.header("Create an Account")
    new_user = st.text_input("Username", key="signup_user")
    new_password = st.text_input("Password", type="password", key="signup_pass")
    signup_btn = st.button("Sign Up", key="signup_btn")
    if signup_btn:
        if new_user and new_password:
            if add_user(new_user, new_password):
                st.success("Account created! Please log in.")
            else:
                st.error("Username already exists.")
        else:
            st.error("Enter both username and password.")

def login():
    st.header("Login")
    username = st.text_input("Username", key="login_user")
    password = st.text_input("Password", type="password", key="login_pass")
    login_btn = st.button("Login", key="login_btn")
    if login_btn:
        if verify_user(username, password):
            st.session_state.logged_in = True
            st.session_state.username = username
            st.success(f"Welcome, {username}!")
            st.rerun()
        else:
            st.error("Invalid username or password.")

def logout():
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.session_state.engine = None
        st.session_state.interview_done = False
        st.session_state.session_id = None
        st.session_state.messages = []
        st.session_state.resume_text = None
        st.session_state.viewing_session = False
        st.rerun()

def feedback():
    summary = []
    for q_num, emotions in st.session_state.question_emotions.items():
        if emotions:
            count = Counter(emotions)
            dominant = count.most_common(1)[0][0]
            summary.append((q_num, dominant, dict(count)))
        else:
            summary.append((q_num, "neutral", {}))
    
    if len(st.session_state.messages)>=2:
        feedback = st.session_state.engine.get_final_feedback(summary)
        st.chat_message("assistant").write("Thank you for your time. The interview is now complete. I'll now generate personalized feedback to help you improve.")
        st.chat_message("assistant").markdown("### Final Interview Feedback:")
        st.chat_message("assistant").write(feedback)
        st.session_state.messages.append({
            "role": "assistant",
            "content": f"### Final Interview Feedback:\n{feedback}"
        })
        with st.spinner("⌛ Please review your feedback here or in your side bar after a minute"):
            time.sleep(60)
    save_interview_session(
        st.session_state.session_id,
        st.session_state.username,
        st.session_state.resume_text,
        st.session_state.messages,
        interview_done=True
    )
    save_session()

def initialize_params():

    if 'webcam_last_active' not in st.session_state:
        st.session_state.webcam_last_active = time.time()
    if "question_emotions" not in st.session_state:
        st.session_state.question_emotions = {}  # {1: [emotions], 2: [emotions], ...}
    if "current_question_number" not in st.session_state:
        st.session_state.current_question_number = 1
    if "interview_started" not in st.session_state:
        st.session_state.interview_started=False
    if "interview_end_time" not in st.session_state:
        st.session_state.interview_end_time=False

    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if "username" not in st.session_state:
        st.session_state.username = ""
    if "engine" not in st.session_state:
        st.session_state.engine = None
    if "interview_done" not in st.session_state:
        st.session_state.interview_done = False
    if "session_id" not in st.session_state:
        st.session_state.session_id = None
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "resume_text" not in st.session_state:
        st.session_state.resume_text = None
    if "viewing_session" not in st.session_state:
        st.session_state.viewing_session = False
    if "active_session_id" not in st.session_state:
        st.session_state.active_session_id = None
    if "mode" not in st.session_state:
        st.session_state.mode = "chat"
    if "ans" not in st.session_state:
        st.session_state.ans = ""
    if "api_key" not in st.session_state:
        st.session_state.api_key=""

initialize_params()


if not st.session_state.logged_in:
    option = st.radio("Choose an option", ("Login", "Sign Up"))
    if option == "Login":
        login()
    else:
        signup()

else:
    st.sidebar.write(f"Logged in as: {st.session_state.username}")
    logout()

    # Sidebar: List all past interview sessions (logs)
    st.sidebar.title("Your Interviews")
    sessions = fetch_interview_sessions(st.session_state.username)
    for session in sessions:
        label = f"Interview on {session.created_at.strftime('%Y-%m-%d %H:%M')}"
        if st.sidebar.button(label, key=f"session_{session.session_id}"):
            conversation, resume_text, interview_done = fetch_interview_conversation(session.session_id)
            st.session_state.session_id = session.session_id
            st.session_state.messages = conversation
            st.session_state.resume_text = resume_text
            st.session_state.interview_done = interview_done
            if session.session_id == st.session_state.active_session_id:
                st.session_state.viewing_session = False
                # Restore engine for interactive chat
                st.session_state.engine = InterviewEngine(resume_text, session_id=session.session_id,username=st.session_state.username,api_key=st.session_state.api_key)
            else:
                st.session_state.viewing_session = True
                st.session_state.engine = None  # disable interaction on past sessions
            st.rerun()

    if st.session_state.active_session_id==st.session_state.session_id and st.session_state.viewing_session:
            st.session_state.session_id = st.session_state.active_session_id
            st.session_state.viewing_session = False
            conversation, resume_text, interview_done = fetch_interview_conversation(st.session_state.active_session_id)
            st.session_state.messages = conversation
            st.session_state.resume_text = resume_text
            st.session_state.interview_done = interview_done
            # Restore engine for interaction
            st.session_state.engine = InterviewEngine(resume_text, session_id=st.session_state.active_session_id,username=st.session_state.username,api_key=st.session_state.api_key)

    if st.sidebar.button("New Interview"):
            save_session()
    if "interview_duration" not in st.session_state:
        st.session_state.interview_duration=900
        


    # === MAIN AREA ===
   
    if st.session_state.viewing_session:
        
        st.info("Viewing a past interview session. Chat is read-only.")
        for msg in st.session_state.messages:
            st.chat_message(msg["role"]).write(msg["content"])

    else:
        
        st.session_state.active_session_id = st.session_state.session_id
        if (st.session_state.engine is None or len(st.session_state.messages) == 0):
            st.markdown("""
            ### 📋 Interview Instructions

            - 🎥 This is a **webcam-based interview**. Your facial expressions and emotions will be analyzed in real time.
            - 💬 You can respond to questions using **typed input** or **voice recordings** (via mic).
            - ⚠️ If your **webcam is inactive for more than 30 seconds**, the interview will end automatically.
            - 🧠 Try to answer naturally and thoughtfully, your responses will be used to generate feedback at the end.

            """)

            api_key = st.text_input("Please enter your Groq API Key", type="password")
            interview_durations = {"30 minutes": 30, "45 minutes": 45, "60 minutes": 60}
            selected_duration = st.selectbox("Choose your interview duration:", list(interview_durations.keys()))
            uploaded_file = st.file_uploader("Upload your resume (PDF)", type=["pdf"])

            start_interview = st.button("Start Interview")
            if start_interview:
                if not uploaded_file:
                    st.error("Please upload a resume PDF before starting.")
                elif not api_key:
                    st.error("Please enter the API key to start the interview")
                else:
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tf:
                            tf.write(uploaded_file.read())
                            resume_text = parse_resume(tf.name)

                        st.session_state.resume_text = resume_text
                        st.session_state.api_key = api_key
                        st.session_state.engine = InterviewEngine(
                            resume_text,
                            session_id=st.session_state.session_id or str(uuid.uuid4()),
                            username=st.session_state.username,
                            api_key=st.session_state.api_key,
                        )
                        st.session_state.session_id = st.session_state.engine.session_id
                        st.session_state.active_session_id = st.session_state.session_id
                        st.session_state.webcam_last_active = time.time()
                        st.session_state.interview_started = True

                        interview_start_time = datetime.now()
                        st.session_state.interview_end_time = interview_start_time + timedelta(minutes=interview_durations[selected_duration])
                        first_question = st.session_state.engine.get_next_question(" ")
                        st.session_state.messages = [{"role": "assistant", "content": first_question}]
                        log_asked_question(st.session_state.username, first_question)
                        st.session_state.interview_done = False
                        
                        st.rerun()
        else:

            AUDIO_SAVE_PATH = "audio_responses"
            os.makedirs(AUDIO_SAVE_PATH, exist_ok=True)

            @st.cache_resource
            def load_model():
                return whisper.load_model("base")

            model = load_model()

            # Checks the left over time for the interview
            if st.session_state.interview_started:
                now=datetime.now()
                print((st.session_state.interview_end_time - now).total_seconds())
                if (st.session_state.interview_end_time - now).total_seconds()<=60:
                    st.warning("Your interview will end within a minute")
                    feedback()


            RTC_CONFIGURATION = {
                "iceServers": [
                    {"urls": ["stun:us-turn1.xirsys.com"]},
                    {
                        "username": st.secrets["xirsys"]["username"],
                        "credential": st.secrets["xirsys"]["credential"],
                        "urls": [
                            "turn:us-turn1.xirsys.com:80?transport=udp",
                            "turn:us-turn1.xirsys.com:3478?transport=udp",
                            "turn:us-turn1.xirsys.com:80?transport=tcp",
                            "turn:us-turn1.xirsys.com:3478?transport=tcp",
                            "turns:us-turn1.xirsys.com:443?transport=tcp",
                            "turns:us-turn1.xirsys.com:5349?transport=tcp"
                        ]
                    }
                ]
            }
            frame_count = 0

            class EmotionProcessor(VideoProcessorBase):
                def recv(self, frame: av.VideoFrame) -> av.VideoFrame:
                    global frame_count
                    img = frame.to_ndarray(format="bgr24")
                    frame_count += 1

                    if frame_count % 10 == 0:  # process every 10th frame
                        results = detector.detect_emotions(img)
                        if results:
                            emotions = results[0]["emotions"]
                            emotion_label = max(emotions, key=emotions.get)
                            save_emotion(emotion_label)

                    return av.VideoFrame.from_ndarray(img, format="bgr24")

            left_col, right_col = st.columns(2)  
        
            with left_col:

                   if st.session_state.interview_started and not st.session_state.interview_done:
                        webrtc_ctx = webrtc_streamer(
                            key="simple",
                            mode=WebRtcMode.SENDRECV,
                            media_stream_constraints={"video": True, "audio": False},
                            video_processor_factory=EmotionProcessor,
                            rtc_configuration=RTC_CONFIGURATION,
                        )
                        # Update last active time
                        if 'webcam_last_active' not in st.session_state:
                            st.session_state.webcam_last_active = time.time()

                        if webrtc_ctx and webrtc_ctx.state and webrtc_ctx.state.playing:
                            st.session_state.webcam_last_active = time.time()
                    

            with right_col:

                if st.session_state.mode == "chat":
                    if st.session_state.engine and not st.session_state.interview_done:
                        for msg in st.session_state.messages:
                            st.chat_message(msg["role"]).write(msg["content"])
                        
                        if webrtc_ctx is None or not (webrtc_ctx.state and webrtc_ctx.state.playing):
                            st.warning("⚠️ Your webcam is off. Please turn it on to continue the interview.")

                        # Also check inactivity timeout, show warning if webcam inactive for too long (non-blocking)
                        inactive_seconds = time.time() - st.session_state.webcam_last_active
                        if inactive_seconds > 30:
                            st.warning("⛔ Interview ended due to inactive webcam.")
                            st.session_state.interview_done = True
                            feedback()
                        
                        # Input section
                        with st._bottom:
                            left_cols, right_cols = st.columns(2)
                            with right_cols:
                                input_col1, input_col2 = st.columns(2)  # Chat input on left, audio on right

                                with input_col1:
                                    typed_input = st.chat_input("💬 Type your answer here...", key="typed_input")   
                                with input_col2:
                                    audio_file=st.audio_input("Audio input", key="audio_input", label_visibility="collapsed")
                        # Handle typed input
                        final_answer = None
                        if typed_input:
                            final_answer = typed_input.strip()

                        # Handle audio input
                        elif audio_file is not None:
                            audio_save_path = os.path.join(AUDIO_SAVE_PATH, "recorded_response.wav")
                            with open(audio_save_path, "wb") as f:
                                f.write(audio_file.getbuffer())

                            try:
                                transcription = model.transcribe(audio_save_path)
                                final_answer = transcription["text"].strip()
                                
                            except Exception as e:
                                st.error(f"❌ Transcription failed: {e}")
                                final_answer = None

                        # Process the final answer
                       
                        if final_answer:
                            st.chat_message("user").write(final_answer)
                            st.session_state.messages.append({"role": "user", "content": final_answer})
                           
                            qnum=st.session_state.current_question_number
                            if qnum not in st.session_state.question_emotions:
                                st.session_state.question_emotions[qnum] = []
                            #Get emotions for each question and store it
                            emotions=read_emotions()
                            reset_emotions()
                            st.session_state.question_emotions[qnum].extend(emotions)
                            st.session_state.current_question_number += 1

                            next_question = st.session_state.engine.get_next_question(final_answer)
                            log_asked_question(st.session_state.username, next_question)

                            if next_question:
                                print(qnum)
                                q_num = st.session_state.current_question_number
                                if q_num not in st.session_state.question_emotions:
                                    st.session_state.question_emotions[q_num] = []
                                st.chat_message("assistant").write(next_question)
                                st.session_state.messages.append({"role": "assistant", "content": next_question})
                            else:
                                st.chat_message("assistant").write("Thank you for your time. The interview is now complete. I'll now generate personalized feedback to help you improve.")
                                st.session_state.messages.append({
                                    "role": "assistant",
                                    "content": "Thank you for your time. The interview is now complete. I'll now generate personalized feedback to help you improve."
                                })
                                st.session_state.interview_done = True

 
                if st.session_state.engine and st.session_state.interview_done:
                    feedback()
                    

            # Save interview state continuously if logged in & session exists
    
