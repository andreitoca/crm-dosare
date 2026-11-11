import os
import pymysql

# Daca ruleaza pe Streamlit Cloud, citeste datele securizate din st.secrets
# Daca ruleaza local, foloseste valorile configurate
try:
    import streamlit as st
    if hasattr(st, "secrets") and "mysql" in st.secrets:
        DB_HOST = st.secrets["mysql"]["host"]
        DB_USER = st.secrets["mysql"]["user"]
        DB_NAME = st.secrets["mysql"]["database"]
        DB_PASS = st.secrets["mysql"]["password"]
        DB_PORT = int(st.secrets["mysql"].get("port", 3306))
    else:
        raise Exception("Local fallback")
except Exception:
    DB_HOST = "toca-law.ro"
    DB_USER = "tocaladd_actualizari"
    DB_NAME = "tocaladd_dosare"
    # Citim parola din fisierul local existent
    try:
        from db_config_local import DB_PASS
    except Exception:
        DB_PASS = ""
    DB_PORT = 3306

def get_connection():
    return pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME,
        port=DB_PORT,
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )
