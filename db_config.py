import os
import pymysql
import streamlit as st

def get_connection():
    # 1. Conectare prioritara din Streamlit Secrets (Cloud)
    if hasattr(st, "secrets") and "mysql" in st.secrets:
        cfg = st.secrets["mysql"]
        return pymysql.connect(
            host=cfg["host"],
            user=cfg["user"],
            password=cfg["password"],
            database=cfg.get("database", "sys"),
            port=int(cfg.get("port", 4000)),
            connect_timeout=25,
            ssl={"reject_unauthorized": False},
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
    
    # 2. Conectare locala (fallback pentru calculator)
    try:
        from db_config_local import DB_HOST, DB_USER, DB_PASS, DB_PORT, DB_NAME
        return pymysql.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASS,
            database=DB_NAME,
            port=DB_PORT,
            connect_timeout=25,
            ssl={"reject_unauthorized": False},
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
    except Exception as e:
        raise Exception(f"Eroare configurare baza de date: {e}")
