from dotenv import load_dotenv
from urllib.parse import quote_plus
from sqlalchemy import create_engine
import os


load_dotenv()

user = os.getenv("DB_USER")
password = os.getenv("DB_PASSWORD")
host = os.getenv("DB_HOST")
port = os.getenv("DB_PORT")
dbname = os.getenv("DB_NAME")

password_encoded = quote_plus(password)

connection_string = f"mysql+pymysql://{user}:{password_encoded}@{host}:{port}/{dbname}"
engine = create_engine(connection_string)

