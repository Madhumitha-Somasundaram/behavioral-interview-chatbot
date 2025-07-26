
from urllib.parse import quote_plus
from sqlalchemy import create_engine
import streamlit as st



user = st.secrets["DB_USER"]
password = st.secrets["DB_PASSWORD"]
host = st.secrets["DB_HOST"]
port = st.secrets["DB_PORT"]
dbname = st.secrets["DB_NAME"]

password_encoded = quote_plus(password)

connection_string = f"mysql+pymysql://{user}:{password_encoded}@{host}:{port}/{dbname}"
engine = create_engine(connection_string)

