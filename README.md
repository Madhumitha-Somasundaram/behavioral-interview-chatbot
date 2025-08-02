# 🤖 Behavioral Interview Chatbot

An AI-powered interview simulation tool that helps users practice behavioral interviews by generating personalized questions from resumes, analyzing responses (text, voice, facial emotion), and offering constructive feedback.

---

## 🚀 Features

- 🎯 **Resume-based Question Generation**  
  Upload your resume to receive customized behavioral questions.

- 🗣️ **Multimodal Input**  
  Respond via text or speech using integrated Whisper speech-to-text. Emotion detection is done via webcam to analyze facial expressions during answers.

- 🧠 **Answer Evaluation**  
  Llama model evaluates responses for clarity, structure, confidence, and relevance using the STAR format.

- ✍️ **Feedback & Rewriting**  
  Get immediate, AI-powered feedback and improved versions of your responses.

- 💬 **Chat Interface**  
  Streamlit-powered chat UI with integrated microphone and webcam support.

- 🗂️ **Session Tracking**  
  Interview sessions are stored in a Google Cloud MySQL database with performance history.

---

## 🧱 Tech Stack

| Component             | Tools/Frameworks                           |
|----------------------|--------------------------------------------|
| **Frontend**         | Streamlit                                  |
| **Backend**          | Python, LangChain                          |
| **Speech Recognition** | OpenAI Whisper                            |
| **Emotion Detection** | OpenCV + CNN / FER model                  |
| **Database**         | MySQL                                      |
| **Deployment**       | Streamlit Cloud                            |

---

## 📁 Project Structure
```

interview-chatbot/
├── app.py # Main Streamlit app
├── database_connection.py # Connects with Google Cloud MySQL
├── db_schema.py # MySQL database schema
├── interview_engine.py # Uses LLM to generate questions and feedback
├── packages.txt # Import necessary packages
├── requirements.txt # Install the dependencies
├── resume_parser.py # Extracts data from uploaded resumes
├── runtime.txt # Python version
└── README.md
```

## 🔑 Requirements

- Please obtain your Groq API key from:  
  👉 [Get API Key](https://console.groq.com/keys)

- Install dependencies:
  pip install -r requirements.txt

## 🤝 Contributions
Pull requests and feature suggestions are welcome!
Feel free to fork the repo and submit your ideas.

## 📄 License
This project is licensed under the MIT License.
You are free to use, modify, and distribute it.

## 🌐 Live App
👉 [Try the Interview Chatbot](https://madhumitha-somasundaram-behaview.streamlit.app/)

## 👤 Creator
Madhumitha Somasundaram  
Aspiring Data Scientist | AI & NLP Enthusiast | Full-stack Developer

🔗 [LinkedIn](www.linkedin.com/in/madhumitha-somasundaram-033834171)
