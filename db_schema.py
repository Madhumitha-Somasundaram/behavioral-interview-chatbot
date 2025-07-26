from sqlalchemy import text
from database_connection import engine


def create_asked_questions_table():
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS asked_questions (
                id INT PRIMARY KEY AUTO_INCREMENT,
                username VARCHAR(255) NOT NULL,
                resume_hash VARCHAR(64) NOT NULL,
                question TEXT NOT NULL,
                asked_at DATETIME NOT NULL,
                FOREIGN KEY (username) REFERENCES candidate_details(username)
            )
        """))

def create_users_table():
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS candidate_details (
                id INT PRIMARY KEY AUTO_INCREMENT,
                username VARCHAR(255) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL
            )
        """))

def create_interview_sessions_table():
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS interview_sessions (
                id INT PRIMARY KEY AUTO_INCREMENT,
                session_id VARCHAR(36) UNIQUE NOT NULL,
                username VARCHAR(255) NOT NULL,
                created_at DATETIME NOT NULL,
                resume_text LONGTEXT,
                conversation LONGTEXT,
                interview_done BOOLEAN NOT NULL DEFAULT FALSE,
                FOREIGN KEY (username) REFERENCES candidate_details(username)
            )
        """))

def initialize_tables():
    create_asked_questions_table()
    create_users_table()
    create_interview_sessions_table()