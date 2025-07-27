import sqlalchemy
import streamlit as st
import base64
import json
import os

# Decode service account key from base64
service_account_info = json.loads(base64.b64decode(st.secrets["service_account_base64"]))
credentials_path = "/tmp/service_account.json"

# Save to a file
with open(credentials_path, "w") as f:
    json.dump(service_account_info, f)

# Set environment variable for authentication
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path

# Create connection string
db_user = st.secrets["db_user"]
db_pass = st.secrets["db_pass"]
db_name = st.secrets["db_name"]
connection_name = st.secrets["instance_connection_name"]

# Connect using SQLAlchemy + pymysql + Cloud SQL Python Connector
from google.cloud.sql.connector import Connector

connector = Connector()

def getconn():
    conn = connector.connect(
        connection_name,
        "pymysql",
        user=db_user,
        password=db_pass,
        db=db_name
    )
    return conn

# Create SQLAlchemy engine
engine = sqlalchemy.create_engine(
    "mysql+pymysql://",
    creator=getconn,
)

