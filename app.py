import os
import io
import threading
import re
import ssl
import smtplib
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from zoneinfo import ZoneInfo
from datetime import datetime, date
from zeep import Client
from playwright.sync_api import sync_playwright
from db_config import get_connection

try:
    from docx import Document
    from docx.shared import Inches, Pt, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    DOCX_DISPONIBIL = True
except ImportError:
    DOCX_DISPONIBIL = False

st.set_page_config(page_title="CRM Toca Law", page_icon="⚖️", layout="wide")

# --- STILIZARE MENIU LATERAL & ELEMENTE ---
st.markdown("""
<style>
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #FFFFFF 0px, #FFFFFF 185px, #1E3A8A 185px, #1E3A8A 100%) !important;
        border-right: 1px solid #CBD5E1 !important;
        min-width: 215px !important;
        max-width: 235px !important;
    }
    section[data-testid="stSidebar"] > div:first-child {
        padding: 16px 14px !important;
        background: transparent !important;
    }
    section[data-testid="stSidebar"] div[data-baseweb="select"] > div {
        background-color: #F8FAFC !important;
        border: 1px solid #CBD5E1 !important;
        border-radius: 8px !important;
        color: #0F172A !important;
        font-size: 13px !important;
        font-weight: 600 !important;
        margin-bottom: 18px !important;
    }
    section[data-testid="stSidebar"] div.stButton > button {
        width: 100% !important;
        border-radius: 10px !important;
        padding: 12px 10px !important;
        font-weight: 600 !important;
        font-size: 13px !important;
        transition: all 0.2s ease !important;
        display: flex !important;
        flex-direction: column !important;
        align-items: center !important;
        justify-content: center !important;
        gap: 6px !important;
    }
    section[data-testid="stSidebar"] div.stButton > button[kind="secondary"] {
        background-color: rgba(255, 255, 255, 0.08) !important;
        border: 1px solid rgba(255, 255, 255, 0.28) !important;
        color: #FFFFFF !important;
    }
    section[data-testid="stSidebar"] div.stButton > button[kind="secondary"]:hover {
        background-color: rgba(255, 255, 255, 0.18) !important;
        border-color: rgba(255, 255, 255, 0.55) !important;
        color: #FFFFFF !important;
    }
    section[data-testid="stSidebar"] div.stButton > button[kind="primary"] {
        background-color: #00B87C !important;
        border: 1px solid #00B87C !important;
        color: #FFFFFF !important;
        box-shadow: 0 3px 10px rgba(0, 184, 124, 0.35) !important;
    }
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.gold-box-marker) {
        border: 2.5px solid #D4AF37 !important;
        border-radius: 12px !important;
        background: linear-gradient(180deg, #FFFDF5 0%, #FFFFFF 100%) !important;
        box-shadow: 0 4px 16px rgba(212, 175, 55, 0.28) !important;
        padding: 16px 20px !important;
        margin-bottom: 18px !important;
    }
    div.stElementContainer:has(.gold-box-marker) {
        display: none !important;
        height: 0 !important;
    }
    .kanban-col {
        background-color: #F8FAFC;
        border-radius: 10px;
        padding: 10px;
        min-height: 400px;
        border: 1px solid #E2E8F0;
    }
    .kanban-card {
        background-color: #FFFFFF;
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        border: 1px solid #CBD5E1;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data(show_spinner=False)
def incarca_resurse_vizuale():
    def to_css_url(filename):
        if os.path.exists(filename):
            with open(filename, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            return f'url("data:image/png;base64,{b64}")'
        return "none"
    icons = {
        "dosare": to_css_url("File.png"),
        "clienti": to_css_url("Mood Dollar.png"),
        "pontaj": to_css_url("Alarm.png"),
        "sarcini": to_css_url("Clipboard.png"),
        "cautare": to_css_url("Zoom Check.png"),
    }
    logo_html = ""
    for ext in ["", ".png", ".jpg", ".jpeg", ".webp"]:
        nume_fisier = f"220420_[1000xpx]_LOGO_AT{ext}"
        if os.path.exists(nume_fisier):
            with open(nume_fisier, "rb") as img_f:
                b64_logo = base64.b64encode(img_f.read()).decode()
            logo_html = f'<div style="background-color:#FFFFFF; padding:8px 6px; text-align:center; margin-bottom:10px;"><img src="data:image/png;base64,{b64_logo}" style="max-width:100%; height:auto; display:block; margin:0 auto;" /></div>'
            break
    return icons, logo_html

@st.cache_resource(show_spinner=False)
def asigura_structura_db():
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sarcini (
                id INT AUTO_INCREMENT PRIMARY KEY,
                titlu VARCHAR(255),
                descriere TEXT,
                termen_limita DATE,
                ora_limita VARCHAR(20) DEFAULT '16:00',
                atribuit_lui INT DEFAULT 1,
                creat_de INT DEFAULT 1,
                client_id INT NULL,
                dosar_id INT NULL,
                prioritate VARCHAR(50) DEFAULT 'Normală',
                status VARCHAR(50) DEFAULT 'Nou'
            )
        """)
        conn.commit()
        conn.close()
    except Exception:
        pass
    return True

asigura_structura_db()

@st.cache_data(ttl=60, show_spinner=False)
def get_utilizatori_cached():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, nume, rol FROM utilizatori WHERE activ = 1 ORDER BY id ASC")
    rows = cur.fetchall()
    conn.close()
    return rows

@st.cache_data(ttl=60, show_spinner=False)
def get_clienti_cached():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, denumire FROM clienti ORDER BY denumire ASC