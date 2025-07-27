from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.prompts import PromptTemplate
from langchain_groq import ChatGroq
from sqlalchemy import text
from database_connection import engine
import hashlib


interview_prompt = PromptTemplate(
    input_variables=["resume_summary", "chat_history", "recent_answer","previous_questions"],
    template="""
        You are a professional behavioral interviewer who evaluates candidates using the STAR method (Situation, Task, Action, Result).

        You have the following information:

        Resume Summary:
        {resume_summary}

        Conversation So Far In This Session:
        {chat_history}

        Most Recent Candidate Response:
        {recent_answer}

        Previously Asked Questions for This User:
        {previous_questions}        

        Instructions:

        1. If this is the beginning of the interview (i.e., no previous conversation or candidate response exists), start by warmly greeting the candidate by their first name, extracted from the resume summary, for example: "Hi, [Name]!" Then generate the first interview question to begin. You may start with either a **general behavioral** or a **resume-based behavioral** question.

        2. Otherwise, carefully review the most recent candidate response along with the corresponding question.

        3. Evaluate whether the response is:
            - Clear and specific  
            - Complete according to the STAR framework  
            - Directly aligned with the intent of the question  

        4. Based on your evaluation:
            - If the response is incomplete, vague, or lacks STAR structure:
                - Ask a concise **follow-up** question to clarify or explore further.
                - If a follow-up has already been asked once for the same main question and the second response is still unclear or insufficient, do not follow up again. Move on to a new main question instead.
            - If the response is clear and complete, proceed directly to the next main question.

        5. Guidelines for Main Questions:
            - Alternate between **general behavioral** and **resume-based behavioral** questions.
            - Use the `previous_questions` list to track all questions already asked.
            - Before generating a new question, ensure it is not semantically similar or closely overlapping in intent or keywords to any previous question.
            - Phrase each question in a warm, professional, and encouraging manner.
            - **Never repeat** any question listed in the `previous_questions` list.

        6. Always ask **only one question at a time**.

        7. Each question must be **open-ended** and encourage detailed, reflective responses.

        8. Always address the candidate directly using either “you” or "your" or their first name if it's available in the resume summary. Do not refer to them in the third person. Questions should feel like they are being spoken aloud during a live conversation.

        Return only the next question (either a follow-up or a new main question). Do not include any additional commentary or evaluation.
        """
)


feedback_prompt = PromptTemplate(
    input_variables=["resume_summary", "interview_log", "emotions"],
    template="""
        You are an expert interviewer providing a detailed evaluation of a candidate based on their resume and interview performance.

        Candidate Resume Summary:
        {resume_summary}

        Complete Interview Transcript:
        {interview_log}

        Average Emotions per Question:
        {emotions}

        Please provide a detailed, clear, and professional evaluation addressing the candidate directly using “you” and “your.” Use plain text without formatting as a letter or email. Support your feedback with examples wherever possible from the transcript.

        Structure your output as follows:

        1. STAR Method Adherence, Communication Quality, Alignment with Resume, Strengths, and Areas for Improvement
            - Write a concise paragraph combining all five aspects. List 1 to 5 specific observations about how the candidate performed. Include clear examples from the interview to highlight how well they structured their answers using the STAR method, how clearly they communicated, whether their answers aligned with their resume, and where they excelled or need improvement. Provide constructive suggestions for better responses.

        2. Resume Improvement Suggestions
            - Offer actionable and specific feedback on how the candidate can enhance their resume. Modify their original resume content to improve clarity, structure, and presentation of skills. Suggest ways to rephrase achievements by including quantifiable metrics, clearer impact statements, and stronger alignment with the target role. Provide examples by rewriting portions of their original resume content to illustrate these improvements.
        3. Emotional Expression During Interview
            - Analyze the average emotional expression per question. State whether the tone was mostly positive, neutral, or mixed. Offer 1 to 2 insights into how their emotions affected the impression they gave and how they could improve emotional presence, such as by appearing more enthusiastic or calm under pressure.

        4. Sample Answers for the Questions Asked
            - The goal is to generate improved versions of the candidate’s original answers by maintaining the core content they provided but enhancing clarity, coherence, and STAR structure. Use relevant work experiences or projects from their resume to make the responses more detailed, structured, and aligned with the interview questions. Provide 3 to 4 sample answers that reflect this improvement while staying true to the candidate’s initial input.
        5. Overall Score (1 to 10)
            - Give a final score and a one-line justification summarizing the candidate’s overall performance in terms of content, communication, and emotional engagement.

    """
)

resume_prompt = PromptTemplate(
    input_variables=["resume_text"],
    template="Summarize the following resume by briefly highlighting the candidate’s name,key skills, notable projects, job roles, and relevant experience:\n\n{resume_text}"
)

class InterviewEngine:
    def __init__(self, resume_text: str, session_id: str, username: str, api_key: str):
        self.llm = ChatGroq(
            model_name="llama3-70b-8192",
            temperature=0,
            groq_api_key=api_key
        )
        
        self.session_id = session_id
        self.resume_text = resume_text
        self.username = username
        self.histories = {}  # Persist chat histories by session_id

        base_chain = interview_prompt | self.llm

        def get_session_history(session_id: str):
            if session_id not in self.histories:
                self.histories[session_id] = InMemoryChatMessageHistory()
            return self.histories[session_id]

        self.chain = RunnableWithMessageHistory(
            base_chain,
            get_session_history,
            input_messages_key="recent_answer",
            history_messages_key="chat_history"
        )

        self.summary_chain = resume_prompt | self.llm
        self.feedback_chain = feedback_prompt | self.llm

        self.resume_summary = self.summarize_resume(resume_text)
        print(self.resume_summary)
        self.interview_log = []
        self.questions_asked = 0
        self.max_questions = 20

    def get_resume_hash(self):
        return hashlib.sha256(self.resume_text.encode()).hexdigest()

    def get_previously_asked_questions(self):
        resume_hash = self.get_resume_hash()
        with engine.connect() as conn:
            rows = conn.execute(
                text("""
                    SELECT question FROM asked_questions
                    WHERE username = :username AND resume_hash = :resume_hash
                """),
                {"username": self.username, "resume_hash": resume_hash}
            ).fetchall()
        return set(row[0] for row in rows)

    def summarize_resume(self, text: str) -> str:
        return self.summary_chain.invoke({"resume_text": text}).content.strip()

    def get_conversation(self):
        conversation = []
        for role, msg in self.interview_log:
            if role == "Question":
                conversation.append(("AI", msg))
            elif role == "Answer":
                conversation.append(("User", msg))
        return conversation

    def get_next_question(self, answer: str) -> str | None:
        if answer.strip():
            self.interview_log.append(("Answer", answer.strip()))

        if self.questions_asked >= self.max_questions:
            return None

        previous_questions = self.get_previously_asked_questions()
        previous_questions_str = "\n".join(previous_questions)

        result = self.chain.invoke(
            {
                "resume_summary": self.resume_summary,
                "recent_answer": answer,
                "previous_questions": previous_questions_str
            },
            config={"configurable": {"session_id": self.session_id}}
        )

        question = result.content.strip()
        self.questions_asked += 1
        self.interview_log.append(("Question", question))
        return question

    def get_final_feedback(self, emotions_summary) -> str:
        transcript = "\n".join(f"{role}: {text}" for role, text in self.interview_log)
        feedback = self.feedback_chain.invoke(
            {
                "resume_summary": self.resume_summary,
                "interview_log": transcript,
                "emotions": emotions_summary
            }
        )
        return feedback.content.strip()
