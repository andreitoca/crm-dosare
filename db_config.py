import os
import pymysql
import streamlit as st

def get_connection():
    # 1. Citire prioritara din Streamlit Secrets (Cloud)
    if hasattr(st, "secrets") and "mysql" in st.secrets:
        cfg = st.secrets["mysql"]
        return pymysql.connect(
            host=cfg["host"],
            user=cfg["user"],
            password=cfg["password"],
            database=cfg["database"],
            port=int(cfg.get("port", 3306)),
            connect_timeout=20,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
    
    # 2. Conectare locala (fallback pentru rulare de pe PC)
    try:
        from db_config_local import DB_PASS
    except Exception:
        DB_PASS = ""
        
    return pymysql.connect(
        host="toca-law.ro",
        user="tocaladd_actualizari",
        password=DB_PASS,
        database="tocaladd_dosare",
        port=3306,
        connect_timeout=20,
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )
