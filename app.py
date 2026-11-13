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

# --- STILIZARE MENIU LATERAL & ELEMENTE PONTAJ ---
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

    section[data-testid="stSidebar"] div.stButton > button::before {
        content: "" !important;
        display: block !important;
        width: 26px !important;
        height: 26px !important;
        background-repeat: no-repeat !important;
        background-position: center !important;
        background-size: contain !important;
        filter: brightness(0) invert(1) !important;
    }

    section[data-testid="stSidebar"] div.stElementContainer:has(.nav-marker-1) + div.stElementContainer button::before {
        background-image: var(--icon-dosare) !important;
    }
    section[data-testid="stSidebar"] div.stElementContainer:has(.nav-marker-2) + div.stElementContainer button::before {
        background-image: var(--icon-clienti) !important;
    }
    section[data-testid="stSidebar"] div.stElementContainer:has(.nav-marker-3) + div.stElementContainer button::before {
        background-image: var(--icon-pontaj) !important;
    }
    section[data-testid="stSidebar"] div.stElementContainer:has(.nav-marker-4) + div.stElementContainer button::before {
        background-image: var(--icon-sarcini) !important;
    }
    section[data-testid="stSidebar"] div.stElementContainer:has(.nav-marker-5) + div.stElementContainer button::before {
        background-image: var(--icon-cautare) !important;
    }

    /* Chenar auriu pronunțat și vizibil pentru toate blocurile marcate cu aur (Pontaj, Clienți, Contracte, AA) */
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.timer-gold-marker),
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.manual-gold-marker),
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.gold-box-marker),
    div[data-testid="stVerticalBlock"]:has(.timer-gold-marker):not(:has(section[data-testid="stSidebar"])),
    div[data-testid="stVerticalBlock"]:has(.manual-gold-marker):not(:has(section[data-testid="stSidebar"])),
    div[data-testid="stVerticalBlock"]:has(.gold-box-marker):not(:has(section[data-testid="stSidebar"])) {
        border: 2.5px solid #D4AF37 !important;
        border-radius: 12px !important;
        background: linear-gradient(180deg, #FFFDF5 0%, #FFFFFF 100%) !important;
        box-shadow: 0 4px 16px rgba(212, 175, 55, 0.28) !important;
        padding: 16px 20px !important;
        margin-bottom: 18px !important;
    }

    /* Eliminăm dublarea bordurii pe containerele interioare */
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.timer-gold-marker) div[data-testid="stVerticalBlock"],
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.manual-gold-marker) div[data-testid="stVerticalBlock"],
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.gold-box-marker) div[data-testid="stVerticalBlock"] {
        border: none !important;
        box-shadow: none !important;
        background: transparent !important;
        padding: 0 !important;
        margin: 0 !important;
    }

    div[data-testid="stVerticalBlockBorderWrapper"]:has(.gold-box-marker) details {
        border: none !important;
        background-color: transparent !important;
    }
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.gold-box-marker) summary {
        font-weight: 700 !important;
        color: #1E3A8A !important;
        font-size: 13px !important;
    }

    /* Aliniere perfectă pe rând a textului și butoanelor ✏️ și 🗑️ în tabelele Clienți și Contracte CAJ */
    div[data-testid="stHorizontalBlock"]:has(.row-action-marker) {
        align-items: center !important;
    }
    div[data-testid="stHorizontalBlock"]:has(.row-action-marker) > div[data-testid="stColumn"] {
        display: flex !important;
        flex-direction: column !important;
        justify-content: center !important;
    }
    div[data-testid="stHorizontalBlock"]:has(.row-action-marker) div[data-testid="stMarkdownContainer"] p {
        margin: 0 !important;
        padding: 0 !important;
        line-height: 1.3 !important;
    }
    div[data-testid="stHorizontalBlock"]:has(.row-action-marker) div.stButton {
        margin: 0 !important;
    }
    div[data-testid="stHorizontalBlock"]:has(.row-action-marker) div.stButton > button {
        height: 32px !important;
        min-height: 32px !important;
        padding: 0 8px !important;
        border-radius: 8px !important;
        margin: 0 !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
    }

    div[data-testid="stVerticalBlockBorderWrapper"]:has(.manual-gold-marker) details {
        border: none !important;
        background-color: transparent !important;
    }
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.manual-gold-marker) summary {
        font-weight: 700 !important;
        color: #1E3A8A !important;
        font-size: 13px !important;
    }

    /* Buton START verde smarald */
    div.stElementContainer:has(.btn-start-marker) + div.stElementContainer button {
        background-color: #00B87C !important;
        border: 1px solid #009E6A !important;
        color: #FFFFFF !important;
        font-weight: 700 !important;
        border-radius: 8px !important;
        height: 40px !important;
        min-height: 40px !important;
        box-shadow: 0 2px 6px rgba(0, 184, 124, 0.3) !important;
    }
    div.stElementContainer:has(.btn-start-marker) + div.stElementContainer button:hover {
        background-color: #009E6A !important;
        color: #FFFFFF !important;
    }

    /* Buton STOP rosu intens + aliniere identica pe inaltime cu butonul X */
    div.stElementContainer:has(.btn-stop-marker) + div.stElementContainer button {
        background-color: #DC2626 !important;
        border: 1px solid #B91C1C !important;
        color: #FFFFFF !important;
        font-weight: 700 !important;
        border-radius: 8px !important;
        height: 40px !important;
        min-height: 40px !important;
        box-shadow: 0 2px 6px rgba(220, 38, 38, 0.3) !important;
    }
    div[data-testid="stHorizontalBlock"]:has(.btn-stop-marker) div.stButton > button {
        height: 40px !important;
        min-height: 40px !important;
        border-radius: 8px !important;
    }
    div.stElementContainer:has(.btn-stop-marker) + div.stElementContainer button:hover {
        background-color: #B91C1C !important;
        color: #FFFFFF !important;
    }

    /* Ascundem complet spatiul ocupat de markerele invizibile ca sa nu decaleze butoanele pe verticala */
    div.stElementContainer:has(.btn-start-marker),
    div.stElementContainer:has(.btn-stop-marker),
    div.stElementContainer:has(.btn-resume-marker),
    div.stElementContainer:has(.timer-gold-marker),
    div.stElementContainer:has(.manual-gold-marker),
    div.stElementContainer:has(.gold-box-marker),
    div.stElementContainer:has(.row-action-marker) {
        display: none !important;
        height: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
    }

    /* Buton Reluare (Start mic) verde discret in lista Activitate incheiata, aliniat identic cu Editare si Stergere */
    div.stElementContainer:has(.btn-resume-marker) + div.stElementContainer button {
        background-color: #ECFDF5 !important;
        border: 1px solid #00B87C !important;
        color: #047857 !important;
        font-weight: 700 !important;
        border-radius: 8px !important;
        min-height: 38px !important;
        height: 38px !important;
        padding: 0 10px !important;
    }
    div.stElementContainer:has(.btn-resume-marker) + div.stElementContainer button:hover {
        background-color: #00B87C !important;
        color: #FFFFFF !important;
    }

    /* Uniformizare inaltime butoane actiuni in lista Activitate incheiata */
    div[data-testid="stHorizontalBlock"]:has(.btn-resume-marker) div.stButton > button {
        min-height: 38px !important;
        height: 38px !important;
        padding: 0 10px !important;
        border-radius: 8px !important;
    }
</style>
""", unsafe_allow_html=True)

# --- 1. CACHE IMAGINI ȘI LOGO ---
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
            ext_mime = "png" if not nume_fisier.lower().endswith(("jpg", "jpeg")) else "jpeg"
            logo_html = (
                f'<div style="background-color:#FFFFFF; padding:8px 6px; text-align:center; margin-bottom:10px;">'
                f'<img src="data:image/{ext_mime};base64,{b64_logo}" style="max-width:100%; height:auto; display:block; margin:0 auto;" />'
                f'</div>'
            )
            break
    return icons, logo_html

# --- 2. VERIFICARE STRUCTURĂ DB O SINGURĂ DATĂ LA PORNIRE ---
@st.cache_resource(show_spinner=False)
def asigura_structura_db_o_data():
    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS clienti (
                id INT AUTO_INCREMENT PRIMARY KEY,
                denumire VARCHAR(255) NOT NULL,
                tip_client VARCHAR(50) DEFAULT 'PJ (Companie)',
                cui_cnp VARCHAR(100) DEFAULT '',
                adresa TEXT,
                reprezentant VARCHAR(255) DEFAULT '',
                telefon VARCHAR(100) DEFAULT '',
                email VARCHAR(150) DEFAULT ''
            )
        """)
        for nume_col, tip_col in [
            ("tip_client", "VARCHAR(50) DEFAULT 'PJ (Companie)'"),
            ("cui_cnp", "VARCHAR(100) DEFAULT ''"),
            ("adresa", "TEXT"),
            ("reprezentant", "VARCHAR(255) DEFAULT ''"),
            ("telefon", "VARCHAR(100) DEFAULT ''"),
            ("email", "VARCHAR(150) DEFAULT ''")
        ]:
            try:
                cur.execute(f"ALTER TABLE clienti ADD COLUMN {nume_col} {tip_col}")
            except Exception:
                pass

        cur.execute("""
            CREATE TABLE IF NOT EXISTS contracte (
                id INT AUTO_INCREMENT PRIMARY KEY,
                serie_numar VARCHAR(100),
                data_contract DATE,
                client_id INT,
                obiect_contract TEXT,
                tip_onorariu VARCHAR(50),
                valoare_onorariu DECIMAL(12,2) DEFAULT 0,
                tarif_depasire DECIMAL(12,2) DEFAULT 0,
                moneda VARCHAR(20) DEFAULT 'RON',
                numar_ore DECIMAL(8,2) DEFAULT 0,
                alerta_80_luna VARCHAR(20) DEFAULT '',
                alerta_100_luna VARCHAR(20) DEFAULT '',
                status VARCHAR(50) DEFAULT 'Activ'
            )
        """)
        for nume_col, tip_col in [
            ("tarif_depasire", "DECIMAL(12,2) DEFAULT 0"),
            ("numar_ore", "DECIMAL(8,2) DEFAULT 0"),
            ("alerta_80_luna", "VARCHAR(20) DEFAULT ''"),
            ("alerta_100_luna", "VARCHAR(20) DEFAULT ''")
        ]:
            try:
                cur.execute(f"ALTER TABLE contracte ADD COLUMN {nume_col} {tip_col}")
            except Exception:
                pass

        cur.execute("""
            CREATE TABLE IF NOT EXISTS pontaj (
                id INT AUTO_INCREMENT PRIMARY KEY,
                data_activitate DATE,
                utilizator_id INT DEFAULT 1,
                client_id INT,
                dosar_id INT NULL,
                tip_referinta VARCHAR(255) DEFAULT 'Consultanță curentă',
                descriere_activitate TEXT,
                ore_lucrate DECIMAL(6,2) DEFAULT 1.0,
                onorariu_orar DECIMAL(10,2) DEFAULT 0.0,
                valoare_totala DECIMAL(12,2) DEFAULT 0.0,
                moneda VARCHAR(20) DEFAULT 'RON',
                ora_start VARCHAR(10) DEFAULT '',
                ora_stop VARCHAR(10) DEFAULT ''
            )
        """)
        for nume_col, tip_col in [
            ("tip_referinta", "VARCHAR(255) DEFAULT 'Consultanță curentă'"),
            ("valoare_totala", "DECIMAL(12,2) DEFAULT 0.0"),
            ("moneda", "VARCHAR(20) DEFAULT 'RON'"),
            ("ora_start", "VARCHAR(10) DEFAULT ''"),
            ("ora_stop", "VARCHAR(10) DEFAULT ''")
        ]:
            try:
                cur.execute(f"ALTER TABLE pontaj ADD COLUMN {nume_col} {tip_col}")
            except Exception:
                pass

        cur.execute("""
            CREATE TABLE IF NOT EXISTS pontaj_activ (
                id INT AUTO_INCREMENT PRIMARY KEY,
                utilizator_id INT NOT NULL,
                client_id INT NOT NULL,
                dosar_id INT NULL,
                tip_referinta VARCHAR(255) DEFAULT 'Consultanță curentă',
                descriere TEXT,
                start_ts BIGINT NOT NULL,
                offset_secunde BIGINT DEFAULT 0,
                pontaj_id_reluat INT NULL,
                alerta_10h_trimisa TINYINT(1) DEFAULT 0
            )
        """)
        for nume_col, tip_col in [
            ("tip_referinta", "VARCHAR(255) DEFAULT 'Consultanță curentă'"),
            ("offset_secunde", "BIGINT DEFAULT 0"),
            ("pontaj_id_reluat", "INT NULL")
        ]:
            try:
                cur.execute(f"ALTER TABLE pontaj_activ ADD COLUMN {nume_col} {tip_col}")
            except Exception:
                pass

        cur.execute("""
            CREATE TABLE IF NOT EXISTS acte_aditionale (
                id INT AUTO_INCREMENT PRIMARY KEY,
                contract_id INT NOT NULL,
                numar_aa VARCHAR(100) NOT NULL,
                data_aa DATE,
                sectiuni_modificate VARCHAR(255) DEFAULT '',
                modificare_onorariu TEXT,
                modificare_obiect TEXT,
                alte_modificari TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

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
                status VARCHAR(50) DEFAULT 'În lucru'
            )
        """)

        try:
            cur.execute("ALTER TABLE dosare ADD COLUMN client_id INT NULL")
        except Exception:
            pass

        conn.commit()
        conn.close()
    except Exception:
        pass
    return True

asigura_structura_db_o_data()

# --- 3. FUNCȚII DE CITIRE CU CACHE ---
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
    cur.execute("""
        SELECT id, denumire, tip_client, cui_cnp, reprezentant, telefon, email, adresa
        FROM clienti ORDER BY denumire ASC
    """)
    rows = cur.fetchall()
    conn.close()
    return rows

@st.cache_data(ttl=60, show_spinner=False)
def get_dosare_cached():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT
            d.id AS ID,
            d.client_id AS client_id,
            d.numar_dosar AS 'Număr Dosar',
            COALESCE(c.denumire, d.client, '-') AS 'Client',
            d.sursa AS 'Sursă',
            d.institutie AS 'Instanță / Autoritate',
            COALESCE(d.complet, '-') AS 'Complet',
            d.obiect AS 'Obiect / Părți',
            d.ultimul_termen AS 'Termen / Decizie',
            d.ultima_solutie AS 'Ultima Soluție',
            d.ultima_verificare AS 'Verificat la'
        FROM dosare d
        LEFT JOIN clienti c ON d.client_id = c.id
        ORDER BY d.id DESC
    """)
    rows = cur.fetchall()
    conn.close()
    return rows

@st.cache_data(ttl=60, show_spinner=False)
def get_acte_aditionale_cached():
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT
                aa.id,
                aa.contract_id,
                k.serie_numar AS contract_serie,
                c.denumire AS client_nume,
                aa.numar_aa,
                aa.data_aa,
                aa.sectiuni_modificate,
                aa.modificare_onorariu,
                aa.modificare_obiect,
                aa.alte_modificari
            FROM acte_aditionale aa
            JOIN contracte k ON aa.contract_id = k.id
            JOIN clienti c ON k.client_id = c.id
            ORDER BY aa.data_aa DESC, aa.id DESC
        """)
        rows = cur.fetchall()
        conn.close()
        return rows
    except Exception:
        return []

@st.cache_data(ttl=60, show_spinner=False)
def get_contracte_cached(an_crt, luna_crt):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT
            k.id,
            k.serie_numar,
            k.data_contract,
            c.denumire AS client_nume,
            k.tip_onorariu,
            k.valoare_onorariu,
            k.tarif_depasire,
            k.numar_ore,
            k.moneda,
            k.obiect_contract,
            k.status,
            COALESCE((
                SELECT SUM(p.ore_lucrate)
                FROM pontaj p
                WHERE p.client_id = k.client_id
                  AND YEAR(p.data_activitate) = %s
                  AND MONTH(p.data_activitate) = %s
            ), 0) AS ore_consumate_luna
        FROM contracte k
        JOIN clienti c ON k.client_id = c.id
        ORDER BY k.id DESC
    """, (an_crt, luna_crt))
    rows = cur.fetchall()
    conn.close()
    return rows

@st.cache_data(ttl=60, show_spinner=False)
def get_pontaj_detaliat_cached():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT
            p.id,
            p.data_activitate,
            p.utilizator_id,
            u.nume AS avocat_nume,
            p.client_id,
            c.denumire AS client_nume,
            p.dosar_id,
            COALESCE(d.numar_dosar, '') AS numar_dosar,
            COALESCE(p.tip_referinta, 'Consultanță curentă') AS tip_referinta,
            p.descriere_activitate,
            p.ore_lucrate,
            p.onorariu_orar,
            p.valoare_totala,
            COALESCE(p.moneda, 'RON') AS moneda,
            COALESCE(p.ora_start, '') AS ora_start,
            COALESCE(p.ora_stop, '') AS ora_stop
        FROM pontaj p
        JOIN utilizatori u ON p.utilizator_id = u.id
        JOIN clienti c ON p.client_id = c.id
        LEFT JOIN dosare d ON p.dosar_id = d.id
        ORDER BY p.data_activitate DESC, p.id DESC
    """)
    rows = cur.fetchall()
    conn.close()
    return rows

@st.cache_data(ttl=60, show_spinner=False)
def get_sarcini_cached():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT
            s.id AS ID,
            s.client_id AS client_id,
            s.dosar_id AS dosar_id,
            s.titlu AS 'Titlu Sarcină',
            s.termen_limita AS 'Termen Limită',
            s.ora_limita AS 'Ora',
            s.prioritate AS 'Prioritate',
            u.nume AS 'Responsabil',
            COALESCE(c.denumire, '-') AS 'Client',
            s.status AS 'Status'
        FROM sarcini s
        JOIN utilizatori u ON s.atribuit_lui = u.id
        LEFT JOIN clienti c ON s.client_id = c.id
        ORDER BY s.termen_limita ASC, s.id DESC
    """)
    rows = cur.fetchall()
    conn.close()
    return rows

def goleste_cache_date():
    get_utilizatori_cached.clear()
    get_clienti_cached.clear()
    get_dosare_cached.clear()
    get_contracte_cached.clear()
    get_acte_aditionale_cached.clear()
    get_pontaj_detaliat_cached.clear()
    get_sarcini_cached.clear()

# --- CONSTRUIRE OPȚIUNI ACTIVITATE PER CLIENT ---
def construieste_optiuni_activitate_client(client_id, dosare_list, sarcini_list):
    optiuni = {
        "💼 Consultanță curentă / Activitate generală (Fără dosar)": (None, "Consultanță curentă")
    }
    for d in dosare_list:
        if d.get("client_id") == client_id:
            nr_d = d["Număr Dosar"]
            sursa_d = d.get("Sursă") or ""
            label = f"📁 Dosar {nr_d} ({sursa_d})"
            optiuni[label] = (d["ID"], f"Dosar {nr_d}")

    for s in sarcini_list:
        if s.get("client_id") == client_id and s.get("Status") != "Finalizat":
            titlu_s = s["Titlu Sarcină"]
            label = f"📌 Sarcină: {titlu_s}"
            optiuni[label] = (s.get("dosar_id"), f"Sarcină: {titlu_s}")

    return optiuni

# --- UTILITARE ORE / MINUTE ---
def formateaza_ore_minute(ore_zecimale):
    total_min = int(round(float(ore_zecimale or 0) * 60))
    h = total_min // 60
    m = total_min % 60
    return f"{h}:{m:02d} h ({h}h {m}m)"

def formateaza_hh_mm(ore_zecimale):
    total_min = int(round(float(ore_zecimale or 0) * 60))
    h = total_min // 60
    m = total_min % 60
    return f"{h}:{m:02d}"

# --- GENERARE RAPORT WORD (.DOCX) PENTRU ACTIVITATEA PONTAJ ---
def genereaza_raport_word_pontaj(lista_pontaje, nume_avocat_raport, filtru_client_raport, dt_start, dt_end):
    doc = Document()

    for section in doc.sections:
        section.top_margin = Inches(0.75)
        section.bottom_margin = Inches(0.75)
        section.left_margin = Inches(0.75)
        section.right_margin = Inches(0.75)

    p_brand = doc.add_paragraph()
    p_brand.alignment = WD_ALIGN_PARAGRAPH.LEFT
    run_brand = p_brand.add_run("TOCA LAW • RAPORT ACTIVITATE JURIDICĂ (TIMESHEET)")
    run_brand.bold = True
    run_brand.font.size = Pt(14)
    run_brand.font.color.rgb = RGBColor(0x1E, 0x3A, 0x8A)

    p_meta = doc.add_paragraph()
    p_meta.paragraph_format.space_after = Pt(12)
    r_m1 = p_meta.add_run(f"Avocat / Utilizator: ")
    r_m1.bold = True
    r_m1.font.size = Pt(10)
    r_m2 = p_meta.add_run(f"{nume_avocat_raport}    |    ")
    r_m2.font.size = Pt(10)

    r_m3 = p_meta.add_run(f"Client: ")
    r_m3.bold = True
    r_m3.font.size = Pt(10)
    r_m4 = p_meta.add_run(f"{filtru_client_raport}    |    ")
    r_m4.font.size = Pt(10)

    r_m5 = p_meta.add_run(f"Perioada: ")
    r_m5.bold = True
    r_m5.font.size = Pt(10)
    r_m6 = p_meta.add_run(f"{dt_start.strftime('%d.%m.%Y')} – {dt_end.strftime('%d.%m.%Y')}")
    r_m6.font.size = Pt(10)

    tabel = doc.add_table(rows=1, cols=6)
    tabel.style = "Table Grid"
    antete = ["Nr.", "Data", "Client", "Dosar / Referință", "Descrierea Activității Prestate", "Durată"]
    latimi = [Inches(0.4), Inches(0.95), Inches(1.4), Inches(1.3), Inches(2.2), Inches(0.75)]

    hdr_cells = tabel.rows[0].cells
    for idx_c, text_h in enumerate(antete):
        hdr_cells[idx_c].width = latimi[idx_c]
        p_h = hdr_cells[idx_c].paragraphs[0]
        p_h.alignment = WD_ALIGN_PARAGRAPH.CENTER if idx_c in (0, 1, 5) else WD_ALIGN_PARAGRAPH.LEFT
        run_h = p_h.add_run(text_h)
        run_h.bold = True
        run_h.font.size = Pt(9.5)
        run_h.font.color.rgb = RGBColor(0x1E, 0x3A, 0x8A)

    total_ore_raport = 0.0
    total_val_ron = 0.0
    total_val_eur = 0.0

    for idx_r, row_item in enumerate(lista_pontaje, start=1):
        row_cells = tabel.add_row().cells
        dt_val = row_item["data_activitate"]
        dt_str = dt_val.strftime("%d.%m.%Y") if hasattr(dt_val, "strftime") else str(dt_val)
        ore_dec = float(row_item["ore_lucrate"] or 0)
        total_ore_raport += ore_dec
        durata_str = formateaza_hh_mm(ore_dec)
        tip_ref = row_item.get("tip_referinta") or (f"Dosar {row_item['numar_dosar']}" if row_item.get("numar_dosar") else "Consultanță curentă")

        val_tot = float(row_item["valoare_totala"] or 0)
        mon = row_item.get("moneda") or "RON"
        if mon == "EUR":
            total_val_eur += val_tot
        else:
            total_val_ron += val_tot

        valori = [
            str(idx_r),
            dt_str,
            row_item["client_nume"] or "-",
            tip_ref,
            row_item["descriere_activitate"] or "-",
            f"{durata_str} h"
        ]
        for idx_c, val_str in enumerate(valori):
            row_cells[idx_c].width = latimi[idx_c]
            p_c = row_cells[idx_c].paragraphs[0]
            p_c.alignment = WD_ALIGN_PARAGRAPH.CENTER if idx_c in (0, 1, 5) else WD_ALIGN_PARAGRAPH.LEFT
            r_c = p_c.add_run(val_str)
            r_c.font.size = Pt(9)

    # Rând total la finalul tabelului
    total_row = tabel.add_row().cells
    total_row[4].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r_tot_lbl = total_row[4].paragraphs[0].add_run("TOTAL ORE PRESTATE:")
    r_tot_lbl.bold = True
    r_tot_lbl.font.size = Pt(9.5)

    total_row[5].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_tot_val = total_row[5].paragraphs[0].add_run(f"{formateaza_hh_mm(total_ore_raport)} h")
    r_tot_val.bold = True
    r_tot_val.font.size = Pt(9.5)
    r_tot_val.font.color.rgb = RGBColor(0x1E, 0x3A, 0x8A)

    p_sum = doc.add_paragraph()
    p_sum.paragraph_format.space_before = Pt(12)
    r_s1 = p_sum.add_run(f"Total timp prestat în perioadă: {formateaza_ore_minute(total_ore_raport)}")
    r_s1.bold = True
    r_s1.font.size = Pt(10.5)

    if total_val_eur > 0 or total_val_ron > 0:
        p_val = doc.add_paragraph()
        parti_val = []
        if total_val_eur > 0:
            parti_val.append(f"{total_val_eur:.2f} EUR")
        if total_val_ron > 0:
            parti_val.append(f"{total_val_ron:.2f} RON")
        r_v = p_val.add_run(f"Valoare estimativă conform tarifelor contractuale: {' + '.join(parti_val)}")
        r_v.font.size = Pt(10)

    p_foot = doc.add_paragraph()
    p_foot.paragraph_format.space_before = Pt(14)
    r_f = p_foot.add_run(f"Document generat automat din CRM Toca Law la data de {datetime.now().strftime('%d.%m.%Y %H:%M')}.")
    r_f.italic = True
    r_f.font.size = Pt(8.5)
    r_f.font.color.rgb = RGBColor(0x64, 0x74, 0x8B)

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf.getvalue()

# --- CALCUL TARIF AUTOMAT PE ABONAMENT + DEPĂȘIRE ---
def calculeaza_tarif_si_valoare_pontaj(client_id, data_activitate, ore_noi, tarif_manual, exclude_pontaj_id=None, cur_extern=None):
    an_int = data_activitate.year
    luna_int = data_activitate.month

    conn_local = None
    if cur_extern is None:
        conn_local = get_connection()
        cur = conn_local.cursor()
    else:
        cur = cur_extern

    cur.execute("""
        SELECT id, tip_onorariu, valoare_onorariu, tarif_depasire, numar_ore, moneda
        FROM contracte
        WHERE client_id = %s AND status = 'Activ'
        ORDER BY id DESC LIMIT 1
    """, (client_id,))
    contract = cur.fetchone()

    if exclude_pontaj_id:
        cur.execute("""
            SELECT COALESCE(SUM(ore_lucrate), 0) AS ore_anterioare
            FROM pontaj
            WHERE client_id = %s AND YEAR(data_activitate) = %s AND MONTH(data_activitate) = %s AND id != %s
        """, (client_id, an_int, luna_int, exclude_pontaj_id))
    else:
        cur.execute("""
            SELECT COALESCE(SUM(ore_lucrate), 0) AS ore_anterioare
            FROM pontaj
            WHERE client_id = %s AND YEAR(data_activitate) = %s AND MONTH(data_activitate) = %s
        """, (client_id, an_int, luna_int))
    res_ore = cur.fetchone()
    if conn_local is not None:
        conn_local.close()

    ore_anterioare = float(res_ore["ore_anterioare"]) if res_ore else 0.0
    moneda_crt = contract["moneda"] if contract and contract.get("moneda") else "RON"

    if tarif_manual > 0:
        return round(tarif_manual, 2), round(ore_noi * tarif_manual, 2), moneda_crt, None

    if not contract:
        return 0.0, 0.0, moneda_crt, None

    tip = contract.get("tip_onorariu") or ""
    tarif_baza = float(contract.get("valoare_onorariu") or 0.0)
    tarif_dep = float(contract.get("tarif_depasire") or 0.0)
    plafon_ore = float(contract.get("numar_ore") or 0.0)

    if tip == "Abonament" and plafon_ore > 0:
        if tarif_dep <= 0:
            tarif_dep = tarif_baza

        ore_ramase_in_plafon = max(0.0, plafon_ore - ore_anterioare)

        if ore_noi <= ore_ramase_in_plafon:
            val_tot = ore_noi * tarif_baza
            nota = f"Tarif abonament aplicat: {tarif_baza:.2f} {moneda_crt}/oră."
            return round(tarif_baza, 2), round(val_tot, 2), moneda_crt, nota
        elif ore_ramase_in_plafon > 0:
            ore_in = ore_ramase_in_plafon
            ore_peste = ore_noi - ore_ramase_in_plafon
            val_tot = (ore_in * tarif_baza) + (ore_peste * tarif_dep)
            tarif_mediu = val_tot / ore_noi
            nota = (
                f"Plafon abonament atins: {ore_in:.2f} ore calculate la {tarif_baza:.2f} {moneda_crt}/h "
                f"și {ore_peste:.2f} ore peste plafon calculate la {tarif_dep:.2f} {moneda_crt}/h."
            )
            return round(tarif_mediu, 2), round(val_tot, 2), moneda_crt, nota
        else:
            val_tot = ore_noi * tarif_dep
            nota = f"Plafon lunar depășit: s-a aplicat tariful standard de depășire ({tarif_dep:.2f} {moneda_crt}/oră)."
            return round(tarif_dep, 2), round(val_tot, 2), moneda_crt, nota

    elif tip == "Orar" and tarif_baza > 0:
        val_tot = ore_noi * tarif_baza
        nota = f"Tarif orar contractual aplicat: {tarif_baza:.2f} {moneda_crt}/oră."
        return round(tarif_baza, 2), round(val_tot, 2), moneda_crt, nota

    return 0.0, 0.0, moneda_crt, None

# --- FUNCȚIE TRIMITERE EMAIL GENERALĂ ---
def _worker_trimite_email_async(subiect, html_body):
    try:
        conn = get_connection()
        cur = conn.cursor()
        destinatari_lista = []

        try:
            cur.execute("SELECT email FROM utilizatori WHERE activ = 1 AND email IS NOT NULL AND email != ''")
            for r in cur.fetchall():
                if r.get("email"):
                    destinatari_lista.append(r["email"].strip())
        except Exception:
            pass

        smtp_server = "toca-law.ro"
        smtp_port = 465
        expeditor = ""
        parola = ""

        try:
            cur.execute("SELECT smtp_server, smtp_port, email_expeditor, parola_email, email_destinatar FROM setari_email WHERE id = 1")
            row_mail = cur.fetchone()
            if row_mail:
                smtp_server = row_mail.get("smtp_server") or "toca-law.ro"
                smtp_port = int(row_mail.get("smtp_port") or 465)
                expeditor = row_mail.get("email_expeditor") or ""
                parola = row_mail.get("parola_email") or ""
                if not destinatari_lista and row_mail.get("email_destinatar"):
                    destinatari_lista = [e.strip() for e in re.split(r"[,;]+", row_mail["email_destinatar"]) if e.strip()]
        except Exception:
            pass

        conn.close()

        if not expeditor or not parola or not destinatari_lista:
            return

        destinatari_lista = list(dict.fromkeys(destinatari_lista))

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subiect
        msg["From"] = f"CRM Toca Law <{expeditor}>"
        msg["To"] = ", ".join(destinatari_lista)
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        if smtp_port == 465:
            ctx = ssl.create_default_context()
            server = smtplib.SMTP_SSL(smtp_server, smtp_port, context=ctx, timeout=8)
        else:
            server = smtplib.SMTP(smtp_server, smtp_port, timeout=8)
            server.starttls()
        server.login(expeditor, parola)
        server.sendmail(expeditor, destinatari_lista, msg.as_string())
        server.quit()
    except Exception:
        pass

def trimite_email_echipa(subiect, html_body):
    t = threading.Thread(target=_worker_trimite_email_async, args=(subiect, html_body), daemon=True)
    t.start()
    return True, "Notificarea pe email se trimite în fundal către echipă."

def trimite_alerta_abonament(client_nume, serie_caj, ore_incluse, ore_lucrate, procent, prag_label, luna_curenta, tarif_depasire=0.0, moneda="EUR"):
    culoare_banner = "#D97706" if prag_label == "80%" else "#DC2626"
    subiect = f"[Alertă Abonament {prag_label}] {client_nume} - {ore_lucrate:.2f} / {ore_incluse:.2f} ore ({luna_curenta})"
    info_tarif_nou = ""
    if prag_label == "100%" and tarif_depasire > 0:
        info_tarif_nou = f"<p style='color: #DC2626; font-weight: bold;'>Notă facturare: Pentru restul lunii {luna_curenta}, orele suplimentare se tarifează la {tarif_depasire:.2f} {moneda}/oră.</p>"

    html = f"""<!DOCTYPE html>
    <html><head><meta http-equiv="Content-Type" content="text/html; charset=utf-8"></head>
    <body style="font-family: Arial, sans-serif; color: #1E293B; padding: 15px;">
        <div style="background-color: {culoare_banner}; color: white; padding: 14px 18px; border-radius: 8px;">
            <h3 style="margin: 0; color: white;">Alertă Consum Abonament ({prag_label}) &bull; Luna {luna_curenta}</h3>
        </div>
        <div style="padding: 16px; border: 1px solid #E2E8F0; border-radius: 8px; margin-top: 10px; background-color: #F8FAFC;">
            <p><strong>Client:</strong> {client_nume}</p>
            <p><strong>Contract CAJ:</strong> {serie_caj}</p>
            <p><strong>Ore incluse în abonament lunar:</strong> {ore_incluse:.2f} ore</p>
            <p><strong>Total ore lucrate în {luna_curenta}:</strong> <span style="font-size: 16px; font-weight: bold; color: {culoare_banner};">{ore_lucrate:.2f} ore ({procent:.0f}%)</span></p>
            {info_tarif_nou}
            <hr style="border: none; border-top: 1px solid #CBD5E1; margin: 14px 0;">
            <p style="font-size: 12px; color: #64748B;">Notificare generată automat de sistemul CRM Toca Law la înregistrarea pontajului.</p>
        </div>
    </body></html>"""
    return trimite_email_echipa(subiect, html)

def trimite_alerta_cronometru_10h(avocat_nume, client_nume, descriere_act, ore_scurse, ora_start_str):
    h = int(ore_scurse)
    m = int(round((ore_scurse - h) * 60))
    subiect = f"[Alertă Cronometru > 10 ore] {avocat_nume} - {client_nume} ({h}h {m}m)"
    html = f"""<!DOCTYPE html>
    <html><head><meta http-equiv="Content-Type" content="text/html; charset=utf-8"></head>
    <body style="font-family: Arial, sans-serif; color: #1E293B; padding: 15px;">
        <div style="background-color: #DC2626; color: white; padding: 14px 18px; border-radius: 8px;">
            <h3 style="margin: 0; color: white;">⏰ Alertă Cronometru Pontaj Activ peste 10 Ore</h3>
        </div>
        <div style="padding: 16px; border: 1px solid #E2E8F0; border-radius: 8px; margin-top: 10px; background-color: #F8FAFC;">
            <p><strong>Avocat:</strong> {avocat_nume}</p>
            <p><strong>Client:</strong> {client_nume}</p>
            <p><strong>Activitate:</strong> {descriere_act or '-'}</p>
            <p><strong>Pornit la:</strong> {ora_start_str}</p>
            <p><strong>Durată continuă atinsă:</strong> <span style="font-size: 16px; font-weight: bold; color: #DC2626;">{h} ore și {m} minute</span></p>
            <hr style="border: none; border-top: 1px solid #CBD5E1; margin: 14px 0;">
            <p style="font-size: 12px; color: #64748B;">Vă rugăm să verificați dacă cronometrul a fost lăsat pornit din greșeală și să îl opriți / ajustați durata din modulul Pontaj.</p>
        </div>
    </body></html>"""
    return trimite_email_echipa(subiect, html)

def verifica_abonament_dupa_pontaj(client_id, data_activitate, conn_extern=None, cur_extern=None):
    luna_str = data_activitate.strftime("%Y-%m")
    an_int = data_activitate.year
    luna_int = data_activitate.month

    conn_local = None
    if cur_extern is None:
        conn_local = get_connection()
        cur = conn_local.cursor()
        conn_ref = conn_local
    else:
        cur = cur_extern
        conn_ref = conn_extern

    cur.execute("""
        SELECT k.id, k.serie_numar, k.numar_ore, k.tarif_depasire, k.moneda, k.alerta_80_luna, k.alerta_100_luna, c.denumire
        FROM contracte k
        JOIN clienti c ON k.client_id = c.id
        WHERE k.client_id = %s AND k.tip_onorariu = 'Abonament' AND k.status = 'Activ' AND k.numar_ore > 0
        ORDER BY k.id DESC LIMIT 1
    """, (client_id,))
    abonament = cur.fetchone()

    if not abonament:
        if conn_local is not None:
            conn_local.close()
        return []

    cur.execute("""
        SELECT COALESCE(SUM(ore_lucrate), 0) AS total_ore
        FROM pontaj
        WHERE client_id = %s AND YEAR(data_activitate) = %s AND MONTH(data_activitate) = %s
    """, (client_id, an_int, luna_int))
    res_ore = cur.fetchone()
    total_ore = float(res_ore["total_ore"]) if res_ore else 0.0
    ore_incluse = float(abonament["numar_ore"])
    tarif_dep = float(abonament.get("tarif_depasire") or 0.0)
    moneda_ab = abonament.get("moneda") or "EUR"
    procent = (total_ore / ore_incluse) * 100.0 if ore_incluse > 0 else 0.0

    mesaje_ui = []

    if procent >= 100.0 and abonament.get("alerta_100_luna") != luna_str:
        ok, msg = trimite_alerta_abonament(
            abonament["denumire"], abonament["serie_numar"],
            ore_incluse, total_ore, procent, "100%", luna_str, tarif_dep, moneda_ab
        )
        cur.execute("UPDATE contracte SET alerta_100_luna = %s, alerta_80_luna = %s WHERE id = %s", (luna_str, luna_str, abonament["id"]))
        if conn_ref is not None:
            conn_ref.commit()
        mesaje_ui.append(("error", f"🚨 Plafon 100% atins/depășit pentru {abonament['denumire']} ({total_ore:.2f} / {ore_incluse:.2f} ore în {luna_str})! {msg}"))

    elif procent >= 80.0 and abonament.get("alerta_80_luna") != luna_str:
        ok, msg = trimite_alerta_abonament(
            abonament["denumire"], abonament["serie_numar"],
            ore_incluse, total_ore, procent, "80%", luna_str, tarif_dep, moneda_ab
        )
        cur.execute("UPDATE contracte SET alerta_80_luna = %s WHERE id = %s", (luna_str, abonament["id"]))
        if conn_ref is not None:
            conn_ref.commit()
        mesaje_ui.append(("warning", f"⚠️ Prag 80% atins pentru {abonament['denumire']} ({total_ore:.2f} / {ore_incluse:.2f} ore în {luna_str})! {msg}"))

    if conn_local is not None:
        conn_local.close()
    return mesaje_ui


TZ_RO = ZoneInfo("Europe/Bucharest")

def acum_ro():
    return datetime.now(TZ_RO)

@st.cache_resource(show_spinner=False)
def repara_coloane_pontaj_daca_lipsesc():
    try:
        conn = get_connection()
        cur = conn.cursor()
        # Ne asigurăm că există cel puțin un utilizator în tabela utilizatori
        try:
            cur.execute("SELECT COUNT(*) AS cnt FROM utilizatori")
            res_u = cur.fetchone()
            if res_u and res_u["cnt"] == 0:
                cur.execute("INSERT INTO utilizatori (nume, rol, activ) VALUES ('Avocat Coordonator', 'Admin', 1)")
        except Exception:
            pass

        # Eliminăm eventuale constrângeri FOREIGN KEY vechi de pe pontaj (ex. dosar_id NOT NULL sau FK pe dosar_id/utilizator_id)
        try:
            cur.execute("""
                SELECT CONSTRAINT_NAME
                FROM information_schema.KEY_COLUMN_USAGE
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = 'pontaj'
                  AND REFERENCED_TABLE_NAME IS NOT NULL
            """)
            for fk_row in cur.fetchall():
                fk_name = fk_row.get("CONSTRAINT_NAME")
                if fk_name:
                    try:
                        cur.execute(f"ALTER TABLE pontaj DROP FOREIGN KEY `{fk_name}`")
                    except Exception:
                        pass
        except Exception:
            pass

        for stmt in [
            "ALTER TABLE pontaj ADD COLUMN tip_referinta VARCHAR(255) DEFAULT 'Consultanță curentă'",
            "ALTER TABLE pontaj ADD COLUMN valoare_totala DECIMAL(12,2) DEFAULT 0.0",
            "ALTER TABLE pontaj ADD COLUMN moneda VARCHAR(20) DEFAULT 'RON'",
            "ALTER TABLE pontaj ADD COLUMN ora_start VARCHAR(10) DEFAULT ''",
            "ALTER TABLE pontaj ADD COLUMN ora_stop VARCHAR(10) DEFAULT ''",
            "ALTER TABLE pontaj MODIFY COLUMN dosar_id INT NULL DEFAULT NULL",
            "ALTER TABLE pontaj MODIFY COLUMN utilizator_id INT NULL DEFAULT 1",
            "ALTER TABLE pontaj MODIFY COLUMN client_id INT NULL",
            "ALTER TABLE pontaj_activ ADD COLUMN tip_referinta VARCHAR(255) DEFAULT 'Consultanță curentă'",
            "ALTER TABLE pontaj_activ ADD COLUMN offset_secunde BIGINT DEFAULT 0",
            "ALTER TABLE pontaj_activ ADD COLUMN pontaj_id_reluat INT NULL",
        ]:
            try:
                cur.execute(stmt)
            except Exception:
                pass
        conn.commit()
        conn.close()
    except Exception:
        pass

@st.cache_data(ttl=300, show_spinner=False)
def get_coloane_pontaj_cached():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SHOW COLUMNS FROM pontaj")
    cols = {r["Field"]: r for r in cur.fetchall()}
    conn.close()
    return cols

def insereaza_pontaj_sigur(cur, data_act, uid, cl_id, ds_id, tip_ref, desc_act, ore_luc, onor_orar, val_tot, mon, ora_st="", ora_sp=""):
    cols_db = get_coloane_pontaj_cached()

    # Dacă dosar_id nu acceptă NULL în schema veche, punem 0 în loc de None
    ds_val = ds_id
    if ds_val is None and "dosar_id" in cols_db and cols_db["dosar_id"].get("Null") == "NO":
        ds_val = 0

    cand_data = {
        "data_activitate": data_act,
        "utilizator_id": uid,
        "client_id": cl_id,
        "dosar_id": ds_val,
        "tip_referinta": tip_ref,
        "descriere_activitate": desc_act,
        "ore_lucrate": ore_luc,
        "onorariu_orar": onor_orar,
        "valoare_totala": val_tot,
        "moneda": mon,
        "ora_start": ora_st,
        "ora_stop": ora_sp,
    }
    cols_prezente = [k for k in cand_data.keys() if k in cols_db]
    placeholders = ", ".join(["%s"] * len(cols_prezente))
    cols_sql = ", ".join(cols_prezente)
    vals = [cand_data[k] for k in cols_prezente]
    cur.execute(f"INSERT INTO pontaj ({cols_sql}) VALUES ({placeholders})", tuple(vals))

WSDL_URL = "http://portalquery.just.ro/Query.asmx?WSDL"

def interogheaza_portal_just(numar_dosar):
    try:
        client = Client(WSDL_URL)
        rezultate = client.service.CautareDosare(numarDosar=numar_dosar.strip())
        if not rezultate:
            return None
        d = rezultate[0]
        institutie = str(d.institutie) if hasattr(d, 'institutie') else "-"
        obiect = str(d.obiect) if hasattr(d, 'obiect') else "-"
        stadiu = str(d.stadiuProcesualNume) if hasattr(d, 'stadiuProcesualNume') else ""
        complet = "-"
        ultimul_termen = "-"
        ultima_solutie = f"Stadiu: {stadiu}"
        sedinte_list = []
        parti_list = []

        if hasattr(d, 'parti') and d.parti and hasattr(d.parti, 'DosarParte'):
            for p in d.parti.DosarParte:
                parti_list.append({"Nume": p.nume, "Calitate": p.calitateParte})

        if hasattr(d, 'sedinte') and d.sedinte and hasattr(d.sedinte, 'DosarSedinta'):
            sedinte = d.sedinte.DosarSedinta
            for s in sedinte:
                dt_str = s.data.strftime("%d.%m.%Y") if hasattr(s.data, 'strftime') else str(s.data)
                sol = s.solutieSumar or "În așteptare"
                comp = s.complet or "-"
                sedinte_list.append({
                    "Data": dt_str,
                    "Ora": s.ora or "-",
                    "Complet": comp,
                    "Soluție": sol,
                    "Document": s.documentSedinta or "-"
                })
            if sedinte_list:
                ultimul_termen = f"{sedinte_list[0]['Data']} ({sedinte_list[0]['Ora']})"
                ultima_solutie = sedinte_list[0]['Soluție']
                complet = sedinte_list[0]['Complet']

        return {
            "numar_formatat": str(d.numar),
            "institutie": institutie,
            "complet": complet,
            "obiect": f"{obiect} ({stadiu})",
            "ultimul_termen": ultimul_termen,
            "ultima_solutie": ultima_solutie,
            "parti": parti_list,
            "sedinte": sedinte_list
        }
    except Exception:
        return None

def interogheaza_cnsc(input_dosar):
    parti = input_dosar.strip().split("/")
    nr_dosar = parti[0]
    an_dosar = parti[-1] if len(parti) > 1 else str(date.today().year)
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(ignore_https_errors=True)
            page = context.new_page()
            page.goto("http://portal.cnsc.ro/istoricdosare.html", timeout=30000)
            page.wait_for_timeout(2500)
            page.fill("#ctl00_ctl04_ctl01_ctl02_ctl02_ctrl2", nr_dosar)
            page.fill("#ctl00_ctl04_ctl01_ctl02_ctl03_ctrl3", an_dosar)
            page.press("#ctl00_ctl04_ctl01_ctl02_ctl02_ctrl2", "Enter")
            page.wait_for_timeout(3500)

            rows = page.locator("tbody tr").all()
            celule_gasite = None
            for r in rows:
                c = [td.inner_text().strip() for td in r.locator("td").all()]
                if len(c) >= 6 and c[0] == nr_dosar:
                    celule_gasite = c
                    break
            if not celule_gasite:
                browser.close()
                return None

            contestator = celule_gasite[2]
            autoritate = celule_gasite[3]
            complet_cnsc = celule_gasite[4]
            status_dosar = celule_gasite[5]

            detalii_text = status_dosar
            termen_decizie = "-"
            sedinte_istoric = []

            butoane = page.locator("tbody tr td a, tbody tr td input, tbody tr td button").all()
            if butoane:
                try:
                    butoane[0].click()
                    page.wait_for_timeout(2500)
                    body_txt = page.locator("body").inner_text()
                    for line in body_txt.splitlines():
                        l_curat = line.strip()
                        if "Solutie:" in l_curat or "Soluție:" in l_curat or "Decizie" in l_curat:
                            detalii_text = l_curat
                        if "Data decizie" in l_curat:
                            termen_decizie = l_curat
                except Exception:
                    pass

            browser.close()
            return {
                "numar_formatat": f"{nr_dosar}/{complet_cnsc}/{an_dosar}",
                "institutie": "CNSC",
                "complet": complet_cnsc,
                "obiect": f"{contestator} vs. {autoritate}",
                "ultimul_termen": termen_decizie,
                "ultima_solutie": detalii_text,
                "parti": [
                    {"Nume": contestator, "Calitate": "Contestator"},
                    {"Nume": autoritate, "Calitate": "Autoritate Contractantă"}
                ],
                "sedinte": sedinte_istoric
            }
    except Exception:
        return None

def interogheaza_iccj(numar_dosar):
    return interogheaza_portal_just(numar_dosar)

def executa_interogare(numar_dosar, sursa):
    if sursa == "CNSC":
        return interogheaza_cnsc(numar_dosar)
    elif sursa == "ICCJ (scj.ro)":
        return interogheaza_iccj(numar_dosar)
    else:
        return interogheaza_portal_just(numar_dosar)

# --- VERIFICARE GLOBALĂ CRONOMETRU > 10 ORE LA ORICE ACCESARE ---
@st.cache_data(ttl=30, show_spinner=False)
def verifica_cronometre_peste_10_ore():
    try:
        acum_ts = int(acum_ro().timestamp())
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT pa.id, pa.start_ts, COALESCE(pa.offset_secunde, 0) AS offset_secunde,
                   pa.descriere, pa.alerta_10h_trimisa, u.nume AS avocat_nume, c.denumire AS client_nume
            FROM pontaj_activ pa
            JOIN utilizatori u ON pa.utilizator_id = u.id
            JOIN clienti c ON pa.client_id = c.id
        """)
        active_rows = cur.fetchall()
        alerte_active_ui = []

        for r in active_rows:
            secunde_scurse = max(0, acum_ts - int(r["start_ts"])) + int(r.get("offset_secunde") or 0)
            ore_scurse = secunde_scurse / 3600.0
            if ore_scurse >= 10.0:
                ora_start_str = datetime.fromtimestamp(int(r["start_ts"]), tz=TZ_RO).strftime("%d.%m.%Y %H:%M")
                h_sc = int(ore_scurse)
                m_sc = int(round((ore_scurse - h_sc) * 60))
                alerte_active_ui.append(
                    f"⏰ Atenție: Cronometrul lui **{r['avocat_nume']}** pentru **{r['client_nume']}** merge continuu de **{h_sc}h {m_sc}m** (pornit la {ora_start_str})!"
                )
                if int(r.get("alerta_10h_trimisa") or 0) == 0:
                    trimite_alerta_cronometru_10h(
                        r["avocat_nume"], r["client_nume"], r.get("descriere") or "-", ore_scurse, ora_start_str
                    )
                    cur.execute("UPDATE pontaj_activ SET alerta_10h_trimisa = 1 WHERE id = %s", (r["id"],))
                    conn.commit()
        conn.close()
        return alerte_active_ui
    except Exception:
        return []

alerte_10h_globale = verifica_cronometre_peste_10_ore()

# --- BARA LATERALĂ & NAVIGARE ---
icons_css, logo_html = incarca_resurse_vizuale()

st.markdown(f"""
<style>
    :root {{
        --icon-dosare: {icons_css['dosare']};
        --icon-clienti: {icons_css['clienti']};
        --icon-pontaj: {icons_css['pontaj']};
        --icon-sarcini: {icons_css['sarcini']};
        --icon-cautare: {icons_css['cautare']};
    }}
</style>
""", unsafe_allow_html=True)

if logo_html:
    st.sidebar.markdown(logo_html, unsafe_allow_html=True)

useri_db = get_utilizatori_cached()
user_dict = {u['nume']: u['id'] for u in useri_db} if useri_db else {"Avocat Coordonator": 1}
utilizator_selectat = st.sidebar.selectbox(
    "Utilizator",
    list(user_dict.keys()),
    key="sel_user_sidebar",
    label_visibility="collapsed"
)
id_utilizator_curent = user_dict[utilizator_selectat]

if "modul_ales" not in st.session_state:
    st.session_state.modul_ales = "Dosare"

optiuni_meniu = ["Dosare", "Clienți", "Pontaj", "Sarcini", "Căutare"]
for idx_m, nume_modul in enumerate(optiuni_meniu, start=1):
    st.sidebar.markdown(
        f'<span class="nav-marker-{idx_m}" style="display:none;"></span>',
        unsafe_allow_html=True
    )
    este_activ = (st.session_state.modul_ales == nume_modul)
    if st.sidebar.button(
        nume_modul,
        key=f"nav_{idx_m}",
        type="primary" if este_activ else "secondary",
        use_container_width=True
    ):
        st.session_state.modul_ales = nume_modul
        st.rerun()

modul_ales = st.session_state.modul_ales

for msg_10h in alerte_10h_globale:
    st.error(msg_10h)

# === 1. PORTOFOLIU DOSARE ===
if modul_ales == "Dosare":
    st.markdown("""
        <div style="background: linear-gradient(135deg, #1E3A8A 0%, #4169E1 100%); padding: 18px 22px; border-radius: 10px; border: 1px solid #D4AF37; color: white; margin-bottom: 20px;">
            <h2 style="margin: 0; font-size: 22px; color: white;">📋 Portofoliu Dosare Monitorizate</h2>
        </div>
    """, unsafe_allow_html=True)

    lista_clienti = get_clienti_cached()
    client_map = {c['denumire']: c['id'] for c in lista_clienti} if lista_clienti else {}

    with st.expander("➕ Adaugă un Dosar Nou în Monitorizare", expanded=False):
        with st.form("form_add_dosar", clear_on_submit=True):
            c1, c2, c3 = st.columns([1.5, 1, 1.5])
            nr_nou = c1.text_input("Număr Dosar * (ex: 1234/2/2026 sau 3504/C5/2026)")
            sursa_noua = c2.selectbox("Sursă Portal", ["Portal.just.ro", "ICCJ (scj.ro)", "CNSC"])
            opt_clienti = ["(Fără client / Adaugă manual)"] + list(client_map.keys())
            client_selectat = c3.selectbox("Client din Baza de Date", opt_clienti)
            client_manual = st.text_input("Sau scrie nume client rapid (dacă nu e în listă):")

            if st.form_submit_button("Salvează și Interoghează Portalul") and nr_nou:
                with st.spinner("Se caută datele pe portal..."):
                    info = executa_interogare(nr_nou, sursa_noua)
                    nr_salvat = info["numar_formatat"] if info and info.get("numar_formatat") else nr_nou.strip()
                    inst = info["institutie"] if info else "-"
                    comp = info["complet"] if info else "-"
                    ob = info["obiect"] if info else "-"
                    term = info["ultimul_termen"] if info else "-"
                    sol = info["ultima_solutie"] if info else "În așteptare"
                    now_str = datetime.now().strftime("%d.%m.%Y %H:%M")

                    c_id_val = client_map.get(client_selectat) if client_selectat != "(Fără client / Adaugă manual)" else None
                    c_nume_val = client_selectat if c_id_val else (client_manual.strip() or "-")

                    conn = get_connection()
                    cur = conn.cursor()
                    cur.execute("""
                        INSERT INTO dosare (numar_dosar, sursa, client, client_id, institutie, complet, obiect, ultimul_termen, ultima_solutie, ultima_verificare)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE
                            client=VALUES(client), client_id=VALUES(client_id), institutie=VALUES(institutie),
                            complet=VALUES(complet), obiect=VALUES(obiect), ultimul_termen=VALUES(ultimul_termen),
                            ultima_solutie=VALUES(ultima_solutie), ultima_verificare=VALUES(ultima_verificare)
                    """, (nr_salvat, sursa_noua, c_nume_val, c_id_val, inst, comp, ob, term, sol, now_str))
                    conn.commit()
                    conn.close()
                    goleste_cache_date()
                    st.success(f"Dosarul {nr_salvat} a fost salvat!")
                    st.rerun()

    if st.button("🔄 Verifică TOATE dosarele acum"):
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, numar_dosar, sursa FROM dosare")
        toate = cur.fetchall()
        bar = st.progress(0)
        for idx, d_row in enumerate(toate):
            info = executa_interogare(d_row['numar_dosar'], d_row['sursa'])
            if info:
                now_str = datetime.now().strftime("%d.%m.%Y %H:%M")
                cur.execute("""
                    UPDATE dosare
                    SET institutie=%s, complet=%s, obiect=%s, ultimul_termen=%s, ultima_solutie=%s, ultima_verificare=%s
                    WHERE id=%s
                """, (info['institutie'], info['complet'], info['obiect'], info['ultimul_termen'], info['ultima_solutie'], now_str, d_row['id']))
                conn.commit()
            bar.progress((idx + 1) / max(len(toate), 1))
        conn.close()
        goleste_cache_date()
        st.success("Toate dosarele au fost actualizate!")
        st.rerun()

    dosare_list = get_dosare_cached()

    if dosare_list:
        df_dos_view = pd.DataFrame(dosare_list).drop(columns=["client_id"], errors="ignore")
        st.dataframe(df_dos_view, use_container_width=True, hide_index=True)
        with st.expander("🗑️ Șterge un dosar din monitorizare"):
            opt_del_d = [f"{d['ID']} - {d['Număr Dosar']} ({d['Client']})" for d in dosare_list]
            d_selectat = st.selectbox("Selectează dosarul de șters:", opt_del_d)
            if st.button("Confirmă Ștergerea Dosarului"):
                d_id = int(d_selectat.split(" - ")[0])
                conn = get_connection()
                cur = conn.cursor()
                cur.execute("DELETE FROM pontaj WHERE dosar_id = %s", (d_id,))
                cur.execute("DELETE FROM sarcini WHERE dosar_id = %s", (d_id,))
                cur.execute("DELETE FROM dosare WHERE id = %s", (d_id,))
                conn.commit()
                conn.close()
                goleste_cache_date()
                st.success("Dosarul a fost șters!")
                st.rerun()
    else:
        st.info("Niciun dosar înregistrat în monitorizare.")

# === 2. CLIENȚI & CONTRACTE (CAJ) ===
elif modul_ales == "Clienți":
    st.markdown("""
        <div style="background: linear-gradient(135deg, #1E3A8A 0%, #4169E1 100%); padding: 18px 22px; border-radius: 10px; border: 1px solid #D4AF37; color: white; margin-bottom: 20px;">
            <h2 style="margin: 0; font-size: 22px; color: white;">👥 Gestiune Clienți & Contracte de Asistență Juridică (CAJ)</h2>
        </div>
    """, unsafe_allow_html=True)

    tab_cl, tab_caj = st.tabs(["🏢 Bază de Date Clienți", "📄 Contracte de Asistență (CAJ)"])

    # ---------------------------------------------------------
    # TAB 1: BAZĂ DE DATE CLIENȚI
    # ---------------------------------------------------------
    with tab_cl:
        with st.container(border=True):
            st.markdown("<span class='gold-box-marker' style='display:none;'></span>", unsafe_allow_html=True)
            with st.expander("➕ Adaugă Client Nou", expanded=False):
                with st.form("form_add_client", clear_on_submit=True):
                    c1, c2, c3 = st.columns([2, 1, 1])
                    den = c1.text_input("Denumire Client / Nume Complet *")
                    tip_c = c2.selectbox("Tip", ["PJ (Companie)", "PF (Persoană Fizică)"])
                    cui = c3.text_input("CUI / CNP")

                    c4, c5, c6 = st.columns([1.5, 1, 1.5])
                    rep = c4.text_input("Reprezentant Legal / Contact")
                    tel = c5.text_input("Telefon")
                    em = c6.text_input("Email")

                    adr = st.text_input("Adresă / Sediu Social")

                    if st.form_submit_button("💾 Salvează Clientul", type="primary") and den:
                        conn = get_connection()
                        cur = conn.cursor()
                        cur.execute("""
                            INSERT INTO clienti (denumire, tip_client, cui_cnp, adresa, reprezentant, telefon, email)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """, (den.strip(), tip_c, cui.strip(), adr.strip(), rep.strip(), tel.strip(), em.strip()))
                        conn.commit()
                        conn.close()
                        goleste_cache_date()
                        st.success(f"Clientul '{den.strip()}' a fost adăugat!")
                        st.rerun()

        # Pop-up Modificare Date Client (cu mesaj de atenționare)
        @st.dialog("✏️ Modificare Date Client")
        def dialog_modifica_client(cl_row):
            st.warning(f"⚠️ Atenție: Modificarea datelor clientului **{cl_row['denumire']}** va actualiza automat informațiile în toate contractele, dosarele și pontajele asociate acestuia.")
            with st.form(f"form_edit_client_{cl_row['id']}"):
                ec1, ec2 = st.columns([2, 1])
                den_nou = ec1.text_input("Denumire Client *", value=cl_row["denumire"] or "")
                tip_opt = ["PJ (Companie)", "PF (Persoană Fizică)"]
                idx_tip = tip_opt.index(cl_row["tip_client"]) if cl_row.get("tip_client") in tip_opt else 0
                tip_nou = ec2.selectbox("Tip", tip_opt, index=idx_tip)

                ec3, ec4 = st.columns(2)
                cui_nou = ec3.text_input("CUI / CNP", value=cl_row["cui_cnp"] or "")
                rep_nou = ec4.text_input("Reprezentant Legal / Contact", value=cl_row["reprezentant"] or "")

                ec5, ec6 = st.columns(2)
                tel_nou = ec5.text_input("Telefon", value=cl_row["telefon"] or "")
                em_nou = ec6.text_input("Email", value=cl_row["email"] or "")

                adr_nou = st.text_input("Adresă / Sediu Social", value=cl_row["adresa"] or "")

                col_s1, col_s2 = st.columns(2)
                salveaza_cl = col_s1.form_submit_button("✅ Confirmă și Salvează", type="primary", use_container_width=True)
                anuleaza_cl = col_s2.form_submit_button("❌ Anulează", use_container_width=True)

                if salveaza_cl and den_nou.strip():
                    conn = get_connection()
                    cur = conn.cursor()
                    try:
                        cur.execute("""
                            UPDATE clienti
                            SET denumire = %s, tip_client = %s, cui_cnp = %s,
                                reprezentant = %s, telefon = %s, email = %s, adresa = %s
                            WHERE id = %s
                        """, (
                            den_nou.strip(), tip_nou, cui_nou.strip(),
                            rep_nou.strip(), tel_nou.strip(), em_nou.strip(), adr_nou.strip(),
                            cl_row["id"]
                        ))
                        conn.commit()
                        goleste_cache_date()
                    except Exception as e:
                        st.error(f"Eroare la actualizare: {e}")
                    conn.close()
                    st.rerun()
                if anuleaza_cl:
                    st.rerun()

        # Pop-up Ștergere Client (cu mesaj de atenționare)
        @st.dialog("⚠️ Atenționare: Ștergere Client")
        def dialog_sterge_client(cl_row):
            st.error(
                f"🚨 Atenție! Ești pe cale să ștergi definitiv clientul **{cl_row['denumire']}**.\n\n"
                "Această acțiune va șterge permanent și **toate contractele (CAJ), actele adiționale, pontajele și sarcinile** asociate acestui client, iar dosarele îi vor fi deconectate!"
            )
            col_da, col_nu = st.columns(2)
            if col_da.button("✅ Da, șterge definitiv", type="primary", use_container_width=True):
                c_id_del = cl_row["id"]
                conn = get_connection()
                cur = conn.cursor()
                try:
                    cur.execute("UPDATE dosare SET client_id = NULL WHERE client_id = %s", (c_id_del,))
                    cur.execute("DELETE FROM pontaj WHERE client_id = %s", (c_id_del,))
                    cur.execute("DELETE FROM sarcini WHERE client_id = %s", (c_id_del,))
                    cur.execute("DELETE FROM acte_aditionale WHERE contract_id IN (SELECT id FROM contracte WHERE client_id = %s)", (c_id_del,))
                    cur.execute("DELETE FROM contracte WHERE client_id = %s", (c_id_del,))
                    cur.execute("DELETE FROM clienti WHERE id = %s", (c_id_del,))
                    conn.commit()
                    goleste_cache_date()
                except Exception as e:
                    st.error(f"Eroare la ștergere: {e}")
                conn.close()
                st.rerun()
            if col_nu.button("❌ Nu, păstrează clientul", use_container_width=True):
                st.rerun()

        clienti_raw = get_clienti_cached()

        if clienti_raw:
            with st.container(border=True):
                st.markdown("<span class='gold-box-marker' style='display:none;'></span>", unsafe_allow_html=True)
                st.markdown("#### 🏢 Registru Clienți")

                cl_widths = [0.45, 1.7, 1.0, 1.0, 1.2, 1.0, 1.4, 1.8, 0.45, 0.45]
                cl_headers = ["Nr.", "Denumire Client", "Tip", "CUI / CNP", "Contact", "Telefon", "Email", "Adresă", "", ""]
                h_cl_cols = st.columns(cl_widths)
                for col_h, txt_h in zip(h_cl_cols, cl_headers):
                    col_h.markdown(
                        f"<div style='font-size:12px; font-weight:700; color:#475569; padding-bottom:6px; border-bottom:2px solid #E2E8F0;'>{txt_h if txt_h else '&nbsp;'}</div>",
                        unsafe_allow_html=True
                    )

                for idx_c, c in enumerate(clienti_raw, start=1):
                    r_cl_cols = st.columns(cl_widths, vertical_alignment="center")
                    vals_cl = [
                        str(idx_c),
                        c["denumire"] or "-",
                        c["tip_client"] or "-",
                        c["cui_cnp"] or "-",
                        c["reprezentant"] or "-",
                        c["telefon"] or "-",
                        c["email"] or "-",
                        c["adresa"] or "-"
                    ]
                    for col_r, val_r in zip(r_cl_cols[:-2], vals_cl):
                        col_r.markdown(
                            f"<div style='font-size:13px; color:#0F172A; display:flex; align-items:center; min-height:32px; line-height:1.3;'>{val_r}</div>",
                            unsafe_allow_html=True
                        )

                    with r_cl_cols[-2]:
                        st.markdown("<span class='row-action-marker' style='display:none;'></span>", unsafe_allow_html=True)
                        if st.button("✏️", key=f"ed_cl_row_{c['id']}", help=f"Modifică datele clientului {c['denumire']}"):
                            dialog_modifica_client(c)

                    with r_cl_cols[-1]:
                        st.markdown("<span class='row-action-marker' style='display:none;'></span>", unsafe_allow_html=True)
                        if st.button("🗑️", key=f"del_cl_row_{c['id']}", help=f"Șterge clientul {c['denumire']}"):
                            dialog_sterge_client(c)

                    st.markdown("<hr style='margin: 4px 0; border: none; border-top: 1px solid #F1F5F9;'>", unsafe_allow_html=True)
        else:
            st.info("Niciun client înregistrat momentan. Folosește formularul de mai sus pentru a adăuga primul client.")

    # ---------------------------------------------------------
    # TAB 2: CONTRACTE DE ASISTENȚĂ JURIDICĂ (CAJ) + ACTE ADIȚIONALE (AA)
    # ---------------------------------------------------------
    with tab_caj:
        c_list = get_clienti_cached()
        c_dict = {c['denumire']: c['id'] for c in c_list} if c_list else {}

        with st.container(border=True):
            st.markdown("<span class='gold-box-marker' style='display:none;'></span>", unsafe_allow_html=True)
            with st.expander("➕ Înregistrează Contract Nou (CAJ)", expanded=False):
                if not c_dict:
                    st.warning("Adaugă mai întâi un client în tab-ul 'Bază de Date Clienți'.")
                else:
                    with st.form("form_add_caj", clear_on_submit=True):
                        c1, c2, c3 = st.columns(3)
                        serie_nr = c1.text_input("Serie și Număr CAJ * (ex: Seria B nr. 596874)")
                        dt_c = c2.date_input("Data Încheierii", value=date.today())
                        client_caj = c3.selectbox("Client", list(c_dict.keys()))

                        c4, c5, c6, c7, c8 = st.columns([1.2, 1, 1, 1, 0.8])
                        tip_onor = c4.selectbox("Tip Onorariu", ["Abonament", "Orar", "Fix", "Succes"])
                        val_onor = c5.number_input("Tarif Orar / Valoare", min_value=0.0, step=10.0)
                        nr_ore_abon = c6.number_input("Număr ore (Abonament)", min_value=0.0, step=1.0, value=0.0)
                        tarif_dep = c7.number_input("Tarif depășire / h", min_value=0.0, step=10.0, value=0.0)
                        moneda = c8.selectbox("Monedă", ["EUR", "RON"])

                        obiect_caj = st.text_area("Obiectul asistenței juridice")

                        if st.form_submit_button("💾 Înregistrează Contractul", type="primary") and serie_nr:
                            conn = get_connection()
                            cur = conn.cursor()
                            try:
                                cur.execute("""
                                    INSERT INTO contracte (
                                        serie_numar, data_contract, client_id, obiect_contract,
                                        tip_onorariu, valoare_onorariu, tarif_depasire, moneda, numar_ore, status
                                    )
                                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'Activ')
                                """, (
                                    serie_nr.strip(), dt_c, c_dict[client_caj], obiect_caj,
                                    tip_onor, val_onor, tarif_dep, moneda, nr_ore_abon
                                ))
                                conn.commit()
                                goleste_cache_date()
                                st.success(f"Contractul {serie_nr.strip()} a fost salvat!")
                            except Exception as e:
                                st.error(f"Eroare la salvare: {e}")
                            conn.close()
                            st.rerun()

        # Pop-up Modificare Contract + Opțiune Modificare prin Act Adițional (AA)
        @st.dialog("✏️ Modificare Contract / Act Adițional (AA)")
        def dialog_modifica_contract_sau_aa(caj_row):
            st.info(f"Contract selectat: **{caj_row['serie_numar']}** • Client: **{caj_row['client_nume']}** • Data: **{caj_row['data_contract']}**")

            mod_prin_aa = st.checkbox(
                "📜 Modifică prin Act Adițional (AA)",
                value=True,
                key=f"chk_aa_{caj_row['id']}"
            )

            if mod_prin_aa:
                st.markdown("""
                    <div style="background:#FFFDF5; border:1.5px solid #D4AF37; border-radius:8px; padding:10px 14px; margin-bottom:10px;">
                        <strong style="color:#1E3A8A;">📜 Detalii Act Adițional (AA)</strong><br/>
                        <span style="font-size:12px; color:#475569;">Selectează secțiunile modificate prin Act Adițional. Modificările vor fi salvate în registrul AA și aplicate contractului.</span>
                    </div>
                """, unsafe_allow_html=True)

                aa_c1, aa_c2 = st.columns([1.3, 1])
                nr_aa = aa_c1.text_input("Număr / Serie Act Adițional *", placeholder="ex: AA nr. 1 / 2026", key=f"nr_aa_{caj_row['id']}")
                dt_aa = aa_c2.date_input("Data Actului Adițional", value=date.today(), key=f"dt_aa_{caj_row['id']}")

                st.markdown("**Secțiuni ale contractului modificate prin AA:**")
                sc1, sc2, sc3 = st.columns(3)
                bifa_onorariu = sc1.checkbox("💶 Onorariu / Tarife", value=True, key=f"aa_sec_onor_{caj_row['id']}")
                bifa_obiect = sc2.checkbox("📋 Obiectul contractului", value=False, key=f"aa_sec_ob_{caj_row['id']}")
                bifa_alte = sc3.checkbox("📌 Durată / Alte clauze", value=False, key=f"aa_sec_alte_{caj_row['id']}")

                tip_opt = ["Abonament", "Orar", "Fix", "Succes"]
                idx_t = tip_opt.index(caj_row["tip_onorariu"]) if caj_row.get("tip_onorariu") in tip_opt else 0
                mon_opt = ["EUR", "RON"]
                idx_m = mon_opt.index(caj_row["moneda"]) if caj_row.get("moneda") in mon_opt else 0

                tip_nou = caj_row["tip_onorariu"]
                val_noua = float(caj_row["valoare_onorariu"] or 0)
                ore_noi = float(caj_row["numar_ore"] or 0)
                dep_nou = float(caj_row["tarif_depasire"] or 0)
                mon_noua = caj_row["moneda"] or "EUR"
                desc_mod_onor = ""

                if bifa_onorariu:
                    st.markdown("---")
                    st.markdown("**1. Modificare Onorariu prin AA:**")
                    oc1, oc2, oc3 = st.columns(3)
                    tip_nou = oc1.selectbox("Tip Onorariu Nou", tip_opt, index=idx_t, key=f"aa_tip_{caj_row['id']}")
                    val_noua = oc2.number_input("Valoare / Tarif Nou", min_value=0.0, step=10.0, value=val_noua, key=f"aa_val_{caj_row['id']}")
                    mon_noua = oc3.selectbox("Monedă", mon_opt, index=idx_m, key=f"aa_mon_{caj_row['id']}")

                    oc4, oc5 = st.columns(2)
                    ore_noi = oc4.number_input("Ore incluse / lună", min_value=0.0, step=1.0, value=ore_noi, key=f"aa_ore_{caj_row['id']}")
                    dep_nou = oc5.number_input("Tarif depășire / h", min_value=0.0, step=10.0, value=dep_nou, key=f"aa_dep_{caj_row['id']}")
                    desc_mod_onor = st.text_input(
                        "Descriere clauză onorariu AA",
                        value=f"Onorariu {tip_nou}: {val_noua:.2f} {mon_noua}" + (f" ({ore_noi:.1f}h incl., depășire {dep_nou:.2f} {mon_noua}/h)" if tip_nou == "Abonament" else ""),
                        key=f"aa_desc_onor_{caj_row['id']}"
                    )

                obiect_nou = caj_row.get("obiect_contract") or ""
                desc_mod_obiect = ""
                if bifa_obiect:
                    st.markdown("---")
                    st.markdown("**2. Modificare / Extindere Obiect prin AA:**")
                    obiect_nou = st.text_area("Obiectul actualizat al contractului", value=obiect_nou, key=f"aa_ob_{caj_row['id']}")
                    desc_mod_obiect = st.text_input("Rezumat modificare obiect (pentru tabel AA)", placeholder="ex: Extindere asistență pentru dosar nou...", key=f"aa_desc_ob_{caj_row['id']}")

                desc_alte_clauze = ""
                status_opt = ["Activ", "Suspendat", "Încetat"]
                idx_st = status_opt.index(caj_row["status"]) if caj_row.get("status") in status_opt else 0
                status_nou = caj_row.get("status") or "Activ"
                if bifa_alte:
                    st.markdown("---")
                    st.markdown("**3. Durată / Status / Alte Clauze prin AA:**")
                    status_nou = st.selectbox("Status Contract", status_opt, index=idx_st, key=f"aa_st_{caj_row['id']}")
                    desc_alte_clauze = st.text_area("Alte modificări convenite prin AA", placeholder="ex: Prelungire durată contract cu 12 luni...", key=f"aa_alte_{caj_row['id']}")

                col_b1, col_b2 = st.columns(2)
                if col_b1.button("✅ Salvează Actul Adițional", type="primary", use_container_width=True):
                    if not nr_aa.strip():
                        st.error("Te rog să introduci numărul Actului Adițional (ex: AA nr. 1/2026).")
                    else:
                        sectiuni_list = []
                        if bifa_onorariu:
                            sectiuni_list.append("Onorariu")
                        if bifa_obiect:
                            sectiuni_list.append("Obiect")
                        if bifa_alte:
                            sectiuni_list.append("Alte clauze")
                        sectiuni_str = ", ".join(sectiuni_list) if sectiuni_list else "Modificare generală"

                        conn = get_connection()
                        cur = conn.cursor()
                        try:
                            cur.execute("""
                                INSERT INTO acte_aditionale (
                                    contract_id, numar_aa, data_aa, sectiuni_modificate,
                                    modificare_onorariu, modificare_obiect, alte_modificari
                                )
                                VALUES (%s, %s, %s, %s, %s, %s, %s)
                            """, (
                                caj_row["id"], nr_aa.strip(), dt_aa, sectiuni_str,
                                desc_mod_onor.strip(), desc_mod_obiect.strip() or (obiect_nou.strip() if bifa_obiect else ""),
                                desc_alte_clauze.strip()
                            ))
                            cur.execute("""
                                UPDATE contracte
                                SET tip_onorariu = %s, valoare_onorariu = %s, tarif_depasire = %s,
                                    numar_ore = %s, moneda = %s, obiect_contract = %s, status = %s
                                WHERE id = %s
                            """, (
                                tip_nou, val_noua, dep_nou, ore_noi, mon_noua,
                                obiect_nou.strip(), status_nou, caj_row["id"]
                            ))
                            conn.commit()
                            goleste_cache_date()
                        except Exception as e:
                            st.error(f"Eroare la salvarea Actului Adițional: {e}")
                        conn.close()
                        st.rerun()

                if col_b2.button("❌ Anulează", use_container_width=True):
                    st.rerun()

            else:
                # Editare directă a contractului (fără Act Adițional - corectare date)
                st.warning("⚠️ Atenție: Modifici direct datele de bază ale contractului (corectare). Pentru modificări contractuale ulterioare, bifează opțiunea **Modifică prin Act Adițional (AA)** de mai sus.")
                ec1, ec2 = st.columns(2)
                serie_ed = ec1.text_input("Serie și Număr CAJ *", value=caj_row["serie_numar"] or "", key=f"ed_caj_ser_{caj_row['id']}")
                dt_val_init = caj_row["data_contract"]
                if isinstance(dt_val_init, str):
                    dt_val_init = datetime.strptime(dt_val_init, "%Y-%m-%d").date()
                dt_ed = ec2.date_input("Data Încheierii", value=dt_val_init or date.today(), key=f"ed_caj_dt_{caj_row['id']}")

                tip_opt = ["Abonament", "Orar", "Fix", "Succes"]
                idx_t = tip_opt.index(caj_row["tip_onorariu"]) if caj_row.get("tip_onorariu") in tip_opt else 0
                mon_opt = ["EUR", "RON"]
                idx_m = mon_opt.index(caj_row["moneda"]) if caj_row.get("moneda") in mon_opt else 0
                status_opt = ["Activ", "Suspendat", "Încetat"]
                idx_st = status_opt.index(caj_row["status"]) if caj_row.get("status") in status_opt else 0

                ec3, ec4, ec5 = st.columns(3)
                tip_ed = ec3.selectbox("Tip Onorariu", tip_opt, index=idx_t, key=f"ed_caj_tip_{caj_row['id']}")
                val_ed = ec4.number_input("Valoare / Tarif", min_value=0.0, step=10.0, value=float(caj_row["valoare_onorariu"] or 0), key=f"ed_caj_val_{caj_row['id']}")
                mon_ed = ec5.selectbox("Monedă", mon_opt, index=idx_m, key=f"ed_caj_mon_{caj_row['id']}")

                ec6, ec7, ec8 = st.columns(3)
                ore_ed = ec6.number_input("Ore incluse", min_value=0.0, step=1.0, value=float(caj_row["numar_ore"] or 0), key=f"ed_caj_ore_{caj_row['id']}")
                dep_ed = ec7.number_input("Tarif depășire / h", min_value=0.0, step=10.0, value=float(caj_row["tarif_depasire"] or 0), key=f"ed_caj_dep_{caj_row['id']}")
                st_ed = ec8.selectbox("Status", status_opt, index=idx_st, key=f"ed_caj_st_{caj_row['id']}")

                ob_ed = st.text_area("Obiectul asistenței juridice", value=caj_row.get("obiect_contract") or "", key=f"ed_caj_ob_{caj_row['id']}")

                col_d1, col_d2 = st.columns(2)
                if col_d1.button("✅ Salvează Modificările", type="primary", use_container_width=True):
                    conn = get_connection()
                    cur = conn.cursor()
                    try:
                        cur.execute("""
                            UPDATE contracte
                            SET serie_numar = %s, data_contract = %s, tip_onorariu = %s,
                                valoare_onorariu = %s, tarif_depasire = %s, numar_ore = %s,
                                moneda = %s, obiect_contract = %s, status = %s
                            WHERE id = %s
                        """, (
                            serie_ed.strip(), dt_ed, tip_ed, val_ed, dep_ed, ore_ed,
                            mon_ed, ob_ed.strip(), st_ed, caj_row["id"]
                        ))
                        conn.commit()
                        goleste_cache_date()
                    except Exception as e:
                        st.error(f"Eroare la actualizare: {e}")
                    conn.close()
                    st.rerun()
                if col_d2.button("❌ Anulează", use_container_width=True):
                    st.rerun()

        @st.dialog("⚠️ Confirmare ștergere contract")
        def dialog_confirmare_stergere_caj(caj_id, serie_caj, client_caj):
            st.error(f"🚨 Atenție! Ești sigur că dorești să ștergi definitiv contractul **{serie_caj}** încheiat cu **{client_caj}** (inclusiv eventualele Acte Adiționale asociate)?")
            col_da, col_nu = st.columns(2)
            if col_da.button("✅ Da, șterge definitiv", type="primary", use_container_width=True):
                conn = get_connection()
                cur = conn.cursor()
                try:
                    cur.execute("DELETE FROM acte_aditionale WHERE contract_id = %s", (caj_id,))
                    cur.execute("DELETE FROM contracte WHERE id = %s", (caj_id,))
                    conn.commit()
                    goleste_cache_date()
                except Exception as e:
                    st.error(f"Eroare la ștergere: {e}")
                conn.close()
                st.rerun()
            if col_nu.button("❌ Nu, păstrează", use_container_width=True):
                st.rerun()

        an_crt = date.today().year
        luna_crt = date.today().month
        contracte_rows = get_contracte_cached(an_crt, luna_crt)
        aa_rows = get_acte_aditionale_cached()

        # Grupăm actele adiționale per contract_id pentru afișare rapidă în coloana dedicată
        aa_per_contract = {}
        for aa in aa_rows:
            aa_per_contract.setdefault(aa["contract_id"], []).append(aa)

        with st.container(border=True):
            st.markdown("<span class='gold-box-marker' style='display:none;'></span>", unsafe_allow_html=True)
            st.markdown("#### 📋 Registru Contracte de Asistență Juridică (CAJ)")

            if contracte_rows:
                widths = [0.45, 1.35, 0.95, 1.4, 0.9, 1.2, 0.95, 1.15, 1.4, 1.5, 0.75, 0.42, 0.42]
                headers = [
                    "Nr.", "Serie / Nr.", "Data", "Client", "Tip",
                    "Onorariu", "Ore Incl.", "Depășire", "Consum Lună", "Modificări AA", "Status", "", ""
                ]
                h_cols = st.columns(widths)
                for col_h, text_h in zip(h_cols, headers):
                    col_h.markdown(
                        f"<div style='font-size:12px; font-weight:700; color:#475569; padding-bottom:6px; border-bottom:2px solid #E2E8F0;'>{text_h if text_h else '&nbsp;'}</div>",
                        unsafe_allow_html=True
                    )

                for idx_k, r in enumerate(contracte_rows, start=1):
                    tip = r["tip_onorariu"] or "-"
                    mon = r["moneda"] or "EUR"
                    val_baza = float(r["valoare_onorariu"] or 0)
                    t_dep = float(r["tarif_depasire"] or 0)
                    ore_ab = float(r["numar_ore"] or 0)
                    ore_cons = float(r["ore_consumate_luna"] or 0)

                    if tip == "Abonament":
                        onorariu_str = f"{val_baza:.2f} {mon}/h"
                        ore_str = f"{ore_ab:.1f} h" if ore_ab > 0 else "Nelimitat"
                        depasire_str = f"{t_dep:.2f} {mon}/h" if t_dep > 0 else f"{val_baza:.2f} {mon}/h"
                        if ore_ab > 0:
                            proc = (ore_cons / ore_ab) * 100
                            consum_str = f"{ore_cons:.1f}/{ore_ab:.1f}h ({proc:.0f}%)"
                        else:
                            consum_str = f"{ore_cons:.1f} h"
                    elif tip == "Orar":
                        onorariu_str = f"{val_baza:.2f} {mon}/h"
                        ore_str = "-"
                        depasire_str = "-"
                        consum_str = f"{ore_cons:.1f} h"
                    else:
                        onorariu_str = f"{val_baza:.2f} {mon}"
                        ore_str = "-"
                        depasire_str = "-"
                        consum_str = "-"

                    lista_aa_c = aa_per_contract.get(r["id"], [])
                    if lista_aa_c:
                        ultimul_aa = lista_aa_c[0]
                        aa_summary = f"📜 {len(lista_aa_c)} AA ({ultimul_aa['numar_aa']}: {ultimul_aa['sectiuni_modificate']})"
                    else:
                        aa_summary = "-"

                    r_cols = st.columns(widths, vertical_alignment="center")
                    valori_rand = [
                        str(idx_k),
                        r["serie_numar"],
                        str(r["data_contract"]),
                        r["client_nume"],
                        tip,
                        onorariu_str,
                        ore_str,
                        depasire_str,
                        consum_str,
                        aa_summary,
                        r["status"] or "Activ"
                    ]
                    for col_r, val_r in zip(r_cols[:-2], valori_rand):
                        col_r.markdown(
                            f"<div style='font-size:13px; color:#0F172A; display:flex; align-items:center; min-height:32px; line-height:1.3;'>{val_r}</div>",
                            unsafe_allow_html=True
                        )

                    with r_cols[-2]:
                        st.markdown("<span class='row-action-marker' style='display:none;'></span>", unsafe_allow_html=True)
                        if st.button("✏️", key=f"ed_row_caj_{r['id']}", help=f"Modifică contractul {r['serie_numar']} sau adaugă Act Adițional"):
                            dialog_modifica_contract_sau_aa(r)

                    with r_cols[-1]:
                        st.markdown("<span class='row-action-marker' style='display:none;'></span>", unsafe_allow_html=True)
                        if st.button("🗑️", key=f"del_row_caj_{r['id']}", help=f"Șterge contractul {r['serie_numar']}"):
                            dialog_confirmare_stergere_caj(r["id"], r["serie_numar"], r["client_nume"])

                    st.markdown("<hr style='margin: 4px 0; border: none; border-top: 1px solid #F1F5F9;'>", unsafe_allow_html=True)
            else:
                st.info("Niciun contract înregistrat momentan. Folosește formularul de mai sus pentru a adăuga primul contract.")

        # Tabel dedicat tuturor modificărilor prin Acte Adiționale (AA)
        if aa_rows:
            with st.container(border=True):
                st.markdown("<span class='gold-box-marker' style='display:none;'></span>", unsafe_allow_html=True)
                st.markdown("#### 📜 Registru Modificări prin Acte Adiționale (AA)")
                aa_df_list = [
                    {
                        "Nr.": idx_a,
                        "Act Adițional": a["numar_aa"],
                        "Data AA": str(a["data_aa"]),
                        "Contract CAJ": a["contract_serie"],
                        "Client": a["client_nume"],
                        "Secțiuni Modificate": a["sectiuni_modificate"] or "-",
                        "Modificare Onorariu": a["modificare_onorariu"] or "-",
                        "Modificare Obiect": a["modificare_obiect"] or "-",
                        "Alte Clauze": a["alte_modificari"] or "-"
                    }
                    for idx_a, a in enumerate(aa_rows, start=1)
                ]
                st.dataframe(pd.DataFrame(aa_df_list), use_container_width=True, hide_index=True)

# === 3. PONTAJ & TIMESHEET ===
elif modul_ales == "Pontaj":
    st.markdown("""
        <div style="background: linear-gradient(135deg, #1E3A8A 0%, #4169E1 100%); padding: 18px 22px; border-radius: 10px; border: 1px solid #D4AF37; color: white; margin-bottom: 20px;">
            <h2 style="margin: 0; font-size: 22px; color: white;">⏱️ Pontaj & Timesheet în Timp Real</h2>
        </div>
    """, unsafe_allow_html=True)

    if "alerte_pontaj_recente" in st.session_state and st.session_state.alerte_pontaj_recente:
        for tip_al, text_al in st.session_state.alerte_pontaj_recente:
            if tip_al == "error":
                st.error(text_al)
            elif tip_al == "warning":
                st.warning(text_al)
            else:
                st.info(text_al)
        st.session_state.alerte_pontaj_recente = []

    c_list = get_clienti_cached()
    d_list = get_dosare_cached()
    s_list = get_sarcini_cached()

    c_map = {c['denumire']: c['id'] for c in c_list}
    c_rev_map = {c['id']: c['denumire'] for c in c_list}

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, client_id, dosar_id, tip_referinta, descriere, start_ts,
               COALESCE(offset_secunde, 0) AS offset_secunde, pontaj_id_reluat
        FROM pontaj_activ
        WHERE utilizator_id = %s
        ORDER BY id DESC LIMIT 1
    """, (id_utilizator_curent,))
    cronometru_activ = cur.fetchone()
    conn.close()

    if not c_map:
        st.warning("Adaugă mai întâi cel puțin un client în modulul 'Clienți' pentru a putea ponta.")
    else:
        # 1. CHENAR AURIU PENTRU CRONOMETRUL LIVE (PARTEA DE SUS)
        with st.container(border=True):
            st.markdown(
                "<span class='timer-gold-marker' style='display:none;'></span>"
                "<div style='font-size:12px; font-weight:700; color:#1E3A8A; text-transform:uppercase; letter-spacing:0.5px; margin-bottom:10px;'>"
                "▶️ Cronometru Activitate în Timp Real"
                "</div>",
                unsafe_allow_html=True
            )

            if cronometru_activ:
                dt_acum_ro = acum_ro()
                acum_ts = int(dt_acum_ro.timestamp())
                start_ts_val = int(cronometru_activ["start_ts"])
                offset_sec = int(cronometru_activ.get("offset_secunde") or 0)
                sec_scurse_total = max(0, acum_ts - start_ts_val) + offset_sec
                h_live = sec_scurse_total // 3600

                dt_start_ro = datetime.fromtimestamp(start_ts_val, tz=TZ_RO)
                data_pornire_fmt = dt_start_ro.strftime("%d.%m.%Y")
                ora_pornire_fmt = dt_start_ro.strftime("%H:%M")
                nume_cl_activ = c_rev_map.get(cronometru_activ["client_id"], "Client")
                tip_ref_activ = cronometru_activ.get("tip_referinta") or "Consultanță curentă"
                id_reluat = cronometru_activ.get("pontaj_id_reluat")

                c_dt, c_info, c_ceas, c_stop, c_cancel = st.columns([1.2, 3.1, 1.4, 1.1, 0.55])
                with c_dt:
                    st.markdown("<div style='font-size:11px; font-weight:600; color:#64748B; margin-bottom:3px;'>Data activității</div>", unsafe_allow_html=True)
                    st.markdown(
                        f"<div style='background:#F8FAFC; border:1px solid #CBD5E1; border-radius:8px; padding:7px 10px; font-size:13px; font-weight:600; color:#475569; text-align:center;'>"
                        f"📅 {data_pornire_fmt}"
                        f"</div>",
                        unsafe_allow_html=True
                    )

                with c_info:
                    st.markdown("<div style='font-size:11px; font-weight:600; color:#64748B; margin-bottom:3px;'>Activitate în curs</div>", unsafe_allow_html=True)
                    descriere_live = st.text_input(
                        "Activitate în curs",
                        value=cronometru_activ.get("descriere") or "",
                        placeholder="Descrie activitatea la care lucrezi...",
                        key="live_desc_edit",
                        label_visibility="collapsed"
                    )
                    nota_reluare = f" • Reluat de la **{formateaza_hh_mm(offset_sec / 3600.0)} h**" if offset_sec > 0 else ""
                    st.caption(f"🏢 **{nume_cl_activ}** • {tip_ref_activ} • Pornit la **{ora_pornire_fmt}**{nota_reluare}")

                with c_ceas:
                    st.markdown("<div style='font-size:11px; font-weight:600; color:#64748B; margin-bottom:3px; text-align:center;'>Durată în timp real</div>", unsafe_allow_html=True)
                    # Ceas live coroborat direct cu ceasul calculatorului (Date.now())
                    start_ms = start_ts_val * 1000
                    offset_ms = offset_sec * 1000
                    components.html(f"""
                    <div id="live-clock-box" style="
                        background:#F8FAFC; border:1.5px solid #D4AF37; border-radius:8px;
                        padding:5px 8px; text-align:center; font-family: 'Segoe UI', Arial, sans-serif;
                        font-size:18px; font-weight:800; color:#0F172A; line-height:1.25;">
                        0:00:00
                    </div>
                    <script>
                        const startMs = {start_ms};
                        const offsetMs = {offset_ms};
                        const box = document.getElementById("live-clock-box");
                        function updateClock() {{
                            const nowMs = Date.now();
                            const elapsedSec = Math.max(0, Math.floor((nowMs - startMs + offsetMs) / 1000));
                            const h = Math.floor(elapsedSec / 3600);
                            const m = Math.floor((elapsedSec % 3600) / 60);
                            const s = elapsedSec % 60;
                            const mm = String(m).padStart(2, '0');
                            const ss = String(s).padStart(2, '0');
                            box.textContent = h + ":" + mm + ":" + ss;
                            if (h >= 10) {{
                                box.style.color = "#DC2626";
                                box.style.borderColor = "#DC2626";
                            }}
                        }}
                        updateClock();
                        setInterval(updateClock, 1000);
                    </script>
                    """, height=44)

                with c_stop:
                    st.markdown("<div style='font-size:11px; color:transparent; margin-bottom:3px;'>.</div>", unsafe_allow_html=True)
                    st.markdown("<span class='btn-stop-marker' style='display:none;'></span>", unsafe_allow_html=True)
                    if st.button("⏹️ STOP", use_container_width=True, help="Oprește ceasul și salvează activitatea"):
                        repara_coloane_pontaj_daca_lipsesc()
                        dt_stop_ro = acum_ro()
                        sec_finale = max(0, int(dt_stop_ro.timestamp()) - start_ts_val) + offset_sec
                        total_minute = max(1, int(round(sec_finale / 60.0)))
                        ore_salvate = round(total_minute / 60.0, 2)
                        dt_azi = dt_stop_ro.date()
                        ora_stop_fmt = dt_stop_ro.strftime("%H:%M")
                        cl_id_s = int(cronometru_activ["client_id"])
                        ds_id_s = cronometru_activ.get("dosar_id")
                        ds_id_s = int(ds_id_s) if ds_id_s is not None else None
                        desc_finala = descriere_live.strip() or tip_ref_activ

                        conn = get_connection()
                        cur = conn.cursor()

                        # Folosim direct ID-ul utilizatorului selectat (deja validat din cache)
                        uid_save = id_utilizator_curent if id_utilizator_curent else 1

                        if id_reluat:
                            tarif_ap, val_tot, mon_c, nota_t = calculeaza_tarif_si_valoare_pontaj(
                                cl_id_s, dt_azi, ore_salvate, 0.0, exclude_pontaj_id=id_reluat, cur_extern=cur
                            )
                            cur.execute("""
                                UPDATE pontaj
                                SET descriere_activitate = %s, ore_lucrate = %s, onorariu_orar = %s,
                                    valoare_totala = %s, moneda = %s, ora_stop = %s
                                WHERE id = %s
                            """, (desc_finala, ore_salvate, tarif_ap, val_tot, mon_c, ora_stop_fmt, id_reluat))
                        else:
                            tarif_ap, val_tot, mon_c, nota_t = calculeaza_tarif_si_valoare_pontaj(
                                cl_id_s, dt_azi, ore_salvate, 0.0, cur_extern=cur
                            )
                            insereaza_pontaj_sigur(
                                cur, dt_azi, uid_save, cl_id_s, ds_id_s, tip_ref_activ,
                                desc_finala, ore_salvate, tarif_ap, val_tot, mon_c, ora_pornire_fmt, ora_stop_fmt
                            )

                        cur.execute("DELETE FROM pontaj_activ WHERE id = %s", (cronometru_activ["id"],))
                        conn.commit()

                        mesaje_rez = []
                        if nota_t:
                            mesaje_rez.append(("info", f"💶 {nota_t}"))
                        alerte_ab = verifica_abonament_dupa_pontaj(cl_id_s, dt_azi, conn_extern=conn, cur_extern=cur)
                        if alerte_ab:
                            mesaje_rez.extend(alerte_ab)
                        conn.close()

                        if mesaje_rez:
                            st.session_state.alerte_pontaj_recente = mesaje_rez

                        # Invalidăm selectiv doar cache-ul de pontaj și contracte
                        get_pontaj_detaliat_cached.clear()
                        get_contracte_cached.clear()
                        st.rerun()

                with c_cancel:
                    st.markdown("<div style='font-size:11px; color:transparent; margin-bottom:3px;'>.</div>", unsafe_allow_html=True)
                    if st.button("✖️", use_container_width=True, help="Anulează cronometrul fără a salva"):
                        conn = get_connection()
                        cur = conn.cursor()
                        cur.execute("DELETE FROM pontaj_activ WHERE id = %s", (cronometru_activ["id"],))
                        conn.commit()
                        conn.close()
                        st.rerun()

            else:
                c_dt, c_txt, c_cl, c_asoc, c_timp, c_start = st.columns([1.15, 2.1, 1.35, 1.75, 0.75, 0.95])

                with c_dt:
                    st.markdown("<div style='font-size:11px; font-weight:600; color:#475569; margin-bottom:3px;'>Data activității</div>", unsafe_allow_html=True)
                    st.markdown(
                        f"<div style='background:#F8FAFC; border:1px solid #CBD5E1; border-radius:8px; padding:7px 8px; font-size:13px; font-weight:600; color:#475569; text-align:center;'>"
                        f"📅 {acum_ro().strftime('%d.%m.%Y')}"
                        f"</div>",
                        unsafe_allow_html=True
                    )

                with c_txt:
                    st.markdown("<div style='font-size:11px; font-weight:600; color:#475569; margin-bottom:3px;'>La ce lucrezi acum?</div>", unsafe_allow_html=True)
                    desc_noua = st.text_input(
                        "La ce lucrezi acum?",
                        placeholder="Ex: Consultanță / Redactare...",
                        key="timer_desc_input",
                        label_visibility="collapsed"
                    )

                with c_cl:
                    st.markdown("<div style='font-size:11px; font-weight:600; color:#475569; margin-bottom:3px;'>Clientul</div>", unsafe_allow_html=True)
                    cl_timer = st.selectbox(
                        "Clientul",
                        list(c_map.keys()),
                        key="timer_client_sel",
                        label_visibility="collapsed"
                    )

                cl_id_selectat_live = c_map[cl_timer]
                optiuni_asoc_live = construieste_optiuni_activitate_client(cl_id_selectat_live, d_list, s_list)

                with c_asoc:
                    st.markdown("<div style='font-size:11px; font-weight:600; color:#475569; margin-bottom:3px;'>Asociat cu (Dosar / Sarcină / General)</div>", unsafe_allow_html=True)
                    asoc_aleasa_live = st.selectbox(
                        "Asociat cu",
                        list(optiuni_asoc_live.keys()),
                        key=f"timer_asoc_sel_{cl_id_selectat_live}",
                        label_visibility="collapsed"
                    )

                with c_timp:
                    st.markdown("<div style='font-size:11px; color:transparent; margin-bottom:3px;'>.</div>", unsafe_allow_html=True)
                    st.markdown(
                        "<div style='padding-top:6px; text-align:center; font-size:18px; font-weight:800; color:#0F172A;'>0:00</div>",
                        unsafe_allow_html=True
                    )

                with c_start:
                    st.markdown("<div style='font-size:11px; color:transparent; margin-bottom:3px;'>.</div>", unsafe_allow_html=True)
                    st.markdown("<span class='btn-start-marker' style='display:none;'></span>", unsafe_allow_html=True)
                    if st.button("▶️ START", use_container_width=True):
                        ds_id_start, tip_ref_start = optiuni_asoc_live[asoc_aleasa_live]
                        now_ts = int(acum_ro().timestamp())

                        conn = get_connection()
                        cur = conn.cursor()
                        cur.execute("""
                            INSERT INTO pontaj_activ (utilizator_id, client_id, dosar_id, tip_referinta, descriere, start_ts, offset_secunde, pontaj_id_reluat, alerta_10h_trimisa)
                            VALUES (%s, %s, %s, %s, %s, %s, 0, NULL, 0)
                        """, (id_utilizator_curent, cl_id_selectat_live, ds_id_start, tip_ref_start, desc_noua.strip(), now_ts))
                        conn.commit()
                        conn.close()
                        st.rerun()

            st.caption(f"👤 **{utilizator_selectat}** • Poți opri activitatea (**STOP**), ajusta orele/minutele (**✏️**), iar dacă apeși **▶️** pe activitatea încheiată, ceasul continuă exact de la durata modificată.")

    # --- POP-UP EDITARE ORE / MINUTE / DESCRIERE ---
    @st.dialog("✏️ Modifică Înregistrarea de Pontaj")
    def dialog_editeaza_pontaj(row_p):
        st.caption(f"Client: **{row_p['client_nume']}** • Data: **{row_p['data_activitate']}** • {row_p.get('tip_referinta', 'Consultanță curentă')}")
        ore_vechi_dec = float(row_p["ore_lucrate"] or 0)
        tot_min_v = int(round(ore_vechi_dec * 60))
        h_init = tot_min_v // 60
        m_init = tot_min_v % 60

        col_eh, col_em = st.columns(2)
        h_nou = col_eh.number_input("Ore", min_value=0, max_value=24, step=1, value=h_init, key=f"ed_h_{row_p['id']}")
        m_nou = col_em.number_input("Minute", min_value=0, max_value=59, step=1, value=m_init, key=f"ed_m_{row_p['id']}")
        desc_noua_ed = st.text_area("Descriere activitate", value=row_p["descriere_activitate"] or "", key=f"ed_d_{row_p['id']}")

        col_save, col_cancel_ed = st.columns(2)
        if col_save.button("💾 Salvează Modificările", type="primary", use_container_width=True):
            ore_noi_dec = round(h_nou + (m_nou / 60.0), 2)
            if ore_noi_dec <= 0:
                st.error("Durata trebuie să fie mai mare de 0 minute.")
            else:
                dt_obj = row_p["data_activitate"]
                if isinstance(dt_obj, str):
                    dt_obj = datetime.strptime(dt_obj, "%Y-%m-%d").date()

                tarif_ap, val_tot, mon_c, _ = calculeaza_tarif_si_valoare_pontaj(
                    row_p["client_id"], dt_obj, ore_noi_dec, 0.0, exclude_pontaj_id=row_p["id"]
                )
                conn = get_connection()
                cur = conn.cursor()
                cur.execute("""
                    UPDATE pontaj
                    SET ore_lucrate = %s, descriere_activitate = %s, onorariu_orar = %s, valoare_totala = %s, moneda = %s
                    WHERE id = %s
                """, (ore_noi_dec, desc_noua_ed.strip(), tarif_ap, val_tot, mon_c, row_p["id"]))
                conn.commit()
                conn.close()
                verifica_abonament_dupa_pontaj(row_p["client_id"], dt_obj)
                get_pontaj_detaliat_cached.clear()
                get_contracte_cached.clear()
                st.rerun()

        if col_cancel_ed.button("❌ Anulează", use_container_width=True):
            st.rerun()

    # --- POP-UP CONFIRMARE ȘTERGERE PONTAJ ---
    @st.dialog("⚠️ Confirmare ștergere pontaj")
    def dialog_sterge_pontaj(p_id, client_n, desc_n, durata_str):
        st.write(f"Ești sigur că dorești să ștergi definitiv această activitate pontată (**{durata_str}**) pentru **{client_n}**?")
        st.caption(f"Activitate: {desc_n}")
        col_da, col_nu = st.columns(2)
        if col_da.button("✅ Da, șterge", type="primary", use_container_width=True):
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("DELETE FROM pontaj WHERE id = %s", (p_id,))
            conn.commit()
            conn.close()
            get_pontaj_detaliat_cached.clear()
            get_contracte_cached.clear()
            st.rerun()
        if col_nu.button("❌ Nu, păstrează", use_container_width=True):
            st.rerun()

    # --- 2. SECȚIUNEA DEDICATĂ: ACTIVITATE ÎNCHEIATĂ (MIJLOC) ---
    st.markdown("""
        <div style="display:flex; align-items:center; gap:8px; margin-top:6px; margin-bottom:10px;">
            <span style="font-size:18px; font-weight:800; color:#1E3A8A;">✅ Activitate încheiată</span>
        </div>
    """, unsafe_allow_html=True)

    toate_pontajele = get_pontaj_detaliat_cached()

    col_f1, col_f2 = st.columns([2, 1])
    filtru_avocat = col_f1.selectbox(
        "Filtrează activitățile încheiate după avocat:",
        ["Toată echipa", utilizator_selectat] + [u for u in user_dict.keys() if u != utilizator_selectat],
        key="filtru_avocat_pontaj"
    )

    if filtru_avocat != "Toată echipa":
        pontaje_afisate = [p for p in toate_pontajele if p["avocat_nume"] == filtru_avocat]
    else:
        pontaje_afisate = toate_pontajele

    azi_dt = date.today()
    start_sapt = azi_dt.toordinal() - azi_dt.weekday()
    ore_azi = sum(float(p["ore_lucrate"] or 0) for p in pontaje_afisate if str(p["data_activitate"]) == str(azi_dt))
    ore_sapt = sum(
        float(p["ore_lucrate"] or 0) for p in pontaje_afisate
        if (p["data_activitate"].toordinal() if hasattr(p["data_activitate"], "toordinal") else datetime.strptime(str(p["data_activitate"]), "%Y-%m-%d").date().toordinal()) >= start_sapt
    )

    with col_f2:
        st.markdown(
            f"<div style='background:#F8FAFC; border:1px solid #E2E8F0; border-radius:8px; padding:8px 12px; text-align:right; margin-top:24px;'>"
            f"<span style='font-size:12px; color:#64748B;'>AZI:</span> <strong style='color:#0F172A;'>{formateaza_hh_mm(ore_azi)} h</strong> &nbsp;|&nbsp; "
            f"<span style='font-size:12px; color:#64748B;'>SĂPTĂMÂNA:</span> <strong style='color:#1E3A8A;'>{formateaza_hh_mm(ore_sapt)} h</strong>"
            f"</div>",
            unsafe_allow_html=True
        )

    # --- PANOU EXPORT RAPORT WORD (.DOCX) PER UTILIZATOR ---
    with st.expander("📄 Generează Raport Activitate (Format Word .docx)", expanded=False):
        if not DOCX_DISPONIBIL:
            st.warning("Adaugă `python-docx` în fișierul `requirements.txt` de pe GitHub pentru a activa exportul Word.")
        else:
            cr1, cr2, cr3, cr4 = st.columns([1.4, 1.4, 1.0, 1.0])
            avocat_raport = cr1.selectbox(
                "Utilizator / Avocat",
                [utilizator_selectat] + [u for u in user_dict.keys() if u != utilizator_selectat] + ["Toată echipa"],
                key="rap_avocat_sel"
            )
            client_raport = cr2.selectbox(
                "Client",
                ["Toți clienții"] + list(c_map.keys()),
                key="rap_client_sel"
            )
            prima_zi_luna = date.today().replace(day=1)
            dt_rap_start = cr3.date_input("De la data", value=prima_zi_luna, key="rap_dt_start")
            dt_rap_end = cr4.date_input("Până la data", value=date.today(), key="rap_dt_end")

            lista_filtrata_raport = []
            for p_row in toate_pontajele:
                p_dt = p_row["data_activitate"]
                if isinstance(p_dt, str):
                    p_dt = datetime.strptime(p_dt, "%Y-%m-%d").date()
                if not (dt_rap_start <= p_dt <= dt_rap_end):
                    continue
                if avocat_raport != "Toată echipa" and p_row["avocat_nume"] != avocat_raport:
                    continue
                if client_raport != "Toți clienții" and p_row["client_nume"] != client_raport:
                    continue
                lista_filtrata_raport.append(p_row)

            lista_filtrata_raport.sort(key=lambda x: str(x["data_activitate"]))

            if lista_filtrata_raport:
                doc_bytes = genereaza_raport_word_pontaj(
                    lista_filtrata_raport, avocat_raport, client_raport, dt_rap_start, dt_rap_end
                )
                nume_fisier_word = f"Raport_Activitate_{avocat_raport.replace(' ', '_')}_{dt_rap_start.strftime('%Y%m%d')}_{dt_rap_end.strftime('%Y%m%d')}.docx"
                st.download_button(
                    label=f"⬇️ Descarcă Raportul Word ({len(lista_filtrata_raport)} activități)",
                    data=doc_bytes,
                    file_name=nume_fisier_word,
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    type="primary"
                )
            else:
                st.info("Nu există activități pontate în intervalul și filtrele selectate.")

    if pontaje_afisate:
        zile_grupate = {}
        for p in pontaje_afisate:
            zi_cheie = str(p["data_activitate"])
            zile_grupate.setdefault(zi_cheie, []).append(p)

        for zi_str, lista_zi in zile_grupate.items():
            total_ore_zi = sum(float(x["ore_lucrate"] or 0) for x in lista_zi)
            eticheta_zi = "Astăzi" if zi_str == str(azi_dt) else zi_str

            st.markdown(
                f"<div style='background-color:#F1F5F9; padding:8px 14px; border-radius:6px; margin-top:12px; margin-bottom:6px; display:flex; justify-content:space-between; align-items:center;'>"
                f"<span style='font-weight:700; color:#334155; font-size:13px;'>📅 {eticheta_zi}</span>"
                f"<span style='font-weight:700; color:#1E3A8A; font-size:13px;'>Total zi: {formateaza_ore_minute(total_ore_zi)}</span>"
                f"</div>",
                unsafe_allow_html=True
            )

            for item in lista_zi:
                durata_fmt = formateaza_hh_mm(item["ore_lucrate"])
                val_est = float(item["valoare_totala"] or 0)
                mon_i = item["moneda"] or "RON"
                interval_str = f"{item['ora_start']} - {item['ora_stop']}" if (item["ora_start"] and item["ora_stop"]) else "Manual"
                tip_ref_afis = item.get("tip_referinta") or (f"Dosar {item['numar_dosar']}" if item["numar_dosar"] else "Consultanță curentă")

                c_desc, c_int, c_dur, c_val, c_resume, c_ed, c_del = st.columns([3.9, 1.15, 0.85, 1.05, 0.55, 0.45, 0.45])
                with c_desc:
                    st.markdown(
                        f"<div style='font-size:14px; font-weight:600; color:#0F172A;'>{item['descriere_activitate']}</div>"
                        f"<div style='font-size:12px; color:#64748B;'>🏢 <strong>{item['client_nume']}</strong> • 🏷️ {tip_ref_afis} • 👤 {item['avocat_nume']}</div>",
                        unsafe_allow_html=True
                    )
                with c_int:
                    st.markdown(f"<div style='font-size:12px; color:#64748B; padding-top:8px;'>{interval_str}</div>", unsafe_allow_html=True)
                with c_dur:
                    st.markdown(f"<div style='font-size:14px; font-weight:700; color:#0F172A; padding-top:6px;'>{durata_fmt} h</div>", unsafe_allow_html=True)
                with c_val:
                    val_txt = f"{val_est:.2f} {mon_i}" if val_est > 0 else "-"
                    st.markdown(f"<div style='font-size:13px; font-weight:600; color:#059669; padding-top:7px;'>{val_txt}</div>", unsafe_allow_html=True)
                with c_resume:
                    st.markdown("<span class='btn-resume-marker' style='display:none;'></span>", unsafe_allow_html=True)
                    if st.button("▶️", key=f"resume_p_{item['id']}", help="Continuă această activitate pornind de la durata afișată"):
                        if cronometru_activ is not None:
                            st.warning("⚠️ Ai deja un cronometru pornit în partea de sus! Oprește-l mai întâi înainte de a relua o altă activitate.")
                        else:
                            now_ts = int(acum_ro().timestamp())
                            # Pornim ceasul cu offset egal cu durata deja salvată/ajustată a activității
                            offset_sec_reluare = int(round(float(item["ore_lucrate"] or 0) * 3600))
                            conn = get_connection()
                            cur = conn.cursor()
                            cur.execute("""
                                INSERT INTO pontaj_activ (
                                    utilizator_id, client_id, dosar_id, tip_referinta, descriere,
                                    start_ts, offset_secunde, pontaj_id_reluat, alerta_10h_trimisa
                                )
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 0)
                            """, (
                                id_utilizator_curent,
                                item["client_id"],
                                item.get("dosar_id"),
                                tip_ref_afis,
                                item["descriere_activitate"],
                                now_ts,
                                offset_sec_reluare,
                                item["id"]
                            ))
                            conn.commit()
                            conn.close()
                            st.rerun()
                with c_ed:
                    if st.button("✏️", key=f"ed_p_{item['id']}", help="Modifică orele, minutele sau descrierea"):
                        dialog_editeaza_pontaj(item)
                with c_del:
                    if st.button("🗑️", key=f"del_p_{item['id']}", help="Șterge definitiv această activitate"):
                        dialog_sterge_pontaj(item["id"], item["client_nume"], item["descriere_activitate"], f"{durata_fmt} h")

                st.markdown("<hr style='margin: 4px 0; border: none; border-top: 1px solid #F1F5F9;'>", unsafe_allow_html=True)
    else:
        st.info("Nu există încă activități încheiate. Apasă ▶️ START mai sus pentru a porni prima activitate sau adaugă una manual mai jos!")

    # --- 3. CHENAR AURIU LA FINAL PENTRU INTRODUCEREA PONTAJULUI MANUAL ---
    if c_map:
        st.markdown("<div style='margin-top: 18px;'></div>", unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown("<span class='manual-gold-marker' style='display:none;'></span>", unsafe_allow_html=True)
            with st.expander("➕ Adaugă Pontaj Manual (Alege Data, Clientul, Tipul Activității, Ore și Minute)", expanded=False):
                cm1, cm2 = st.columns([1.2, 2])
                dt_p = cm1.date_input("📅 Data Activității (poți alege orice zi)", value=date.today(), key="manual_dt_input")
                cl_p = cm2.selectbox("🏢 Client *", list(c_map.keys()), key="manual_cl_input")

                cl_id_manual = c_map[cl_p]
                optiuni_asoc_manual = construieste_optiuni_activitate_client(cl_id_manual, d_list, s_list)
                asoc_aleasa_manual = st.selectbox(
                    "📂 Asociat cu (Dosar / Sarcină / Consultanță curentă)",
                    list(optiuni_asoc_manual.keys()),
                    key=f"manual_asoc_sel_{cl_id_manual}"
                )

                cm3, cm4, cm5 = st.columns([1, 1, 1.3])
                ore_m = cm3.number_input("Ore", min_value=0, max_value=24, step=1, value=1, key="manual_ore_in")
                min_m = cm4.number_input("Minute", min_value=0, max_value=59, step=5, value=0, key="manual_min_in")
                tarif_m = cm5.number_input("Tarif Orar (0 = automat din CAJ)", min_value=0.0, step=10.0, value=0.0, key="manual_tarif_in")

                act_m = st.text_area("Descrierea activității prestate *", key="manual_desc_in")

                if st.button("💾 Salvează Pontajul Manual", type="primary"):
                    if not act_m.strip():
                        st.warning("Te rog să completezi descrierea activității prestate.")
                    else:
                        total_ore_dec = round(ore_m + (min_m / 60.0), 2)
                        if total_ore_dec <= 0:
                            st.warning("Introdu cel puțin 1 minut de activitate.")
                        else:
                            dosar_id_val, tip_ref_val = optiuni_asoc_manual[asoc_aleasa_manual]
                            repara_coloane_pontaj_daca_lipsesc()
                            conn = get_connection()
                            cur = conn.cursor()
                            tarif_aplicat, val_totala_calc, moneda_calc, nota_tarif = calculeaza_tarif_si_valoare_pontaj(
                                cl_id_manual, dt_p, total_ore_dec, tarif_m, cur_extern=cur
                            )
                            uid_m = id_utilizator_curent if id_utilizator_curent else 1
                            insereaza_pontaj_sigur(
                                cur, dt_p, uid_m, cl_id_manual, dosar_id_val, tip_ref_val,
                                act_m.strip(), total_ore_dec, tarif_aplicat, val_totala_calc, moneda_calc
                            )
                            conn.commit()

                            mesaje_rez = []
                            if nota_tarif:
                                mesaje_rez.append(("info", f"💶 {nota_tarif}"))
                            alerte_noi = verifica_abonament_dupa_pontaj(cl_id_manual, dt_p, conn_extern=conn, cur_extern=cur)
                            if alerte_noi:
                                mesaje_rez.extend(alerte_noi)
                            conn.close()

                            if mesaje_rez:
                                st.session_state.alerte_pontaj_recente = mesaje_rez

                            get_pontaj_detaliat_cached.clear()
                            get_contracte_cached.clear()
                            st.success("Activitatea a fost pontată cu succes!")
                            st.rerun()

# === 4. SARCINI DE LUCRU (TASKS) ===
elif modul_ales == "Sarcini":
    st.markdown("""
        <div style="background: linear-gradient(135deg, #1E3A8A 0%, #4169E1 100%); padding: 18px 22px; border-radius: 10px; border: 1px solid #D4AF37; color: white; margin-bottom: 20px;">
            <h2 style="margin: 0; font-size: 22px; color: white;">📌 Sarcini de Lucru & Termene Echipă</h2>
        </div>
    """, unsafe_allow_html=True)

    cl_t = get_clienti_cached()
    cl_t_map = {c['denumire']: c['id'] for c in cl_t}

    with st.expander("➕ Creează o Sarcină Nouă", expanded=False):
        with st.form("form_task", clear_on_submit=True):
            col1, col2 = st.columns([2, 1])
            titlu = col1.text_input("Titlu Sarcină *")
            prioritate = col2.selectbox("Prioritate", ["Normală", "Ridicată", "Urgentă"])

            col3, col4, col5 = st.columns([1.5, 1, 1.5])
            termen = col3.date_input("Termen Limită", value=date.today())
            ora = col4.text_input("Ora Limită", value="16:00")
            atribuit = col5.selectbox("Atribuit către", list(user_dict.keys()))

            client_asoc = st.selectbox("Client asociat (opțional)", ["(Niciunul)"] + list(cl_t_map.keys()))
            detalii = st.text_area("Instrucțiuni / Detalii sarcină")

            if st.form_submit_button("Salvează Sarcina") and titlu:
                c_id_t = cl_t_map.get(client_asoc, None) if client_asoc != "(Niciunul)" else None
                conn = get_connection()
                cur = conn.cursor()
                cur.execute("""
                    INSERT INTO sarcini (titlu, descriere, termen_limita, ora_limita, atribuit_lui, creat_de, client_id, prioritate, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'În lucru')
                """, (titlu, detalii, termen, ora, user_dict[atribuit], id_utilizator_curent, c_id_t, prioritate))
                conn.commit()
                conn.close()
                goleste_cache_date()
                st.success("Sarcina a fost adăugată!")
                st.rerun()

    tasks_df = get_sarcini_cached()

    if tasks_df:
        df_tasks_view = pd.DataFrame(tasks_df).drop(columns=["client_id", "dosar_id"], errors="ignore")
        st.dataframe(df_tasks_view, use_container_width=True, hide_index=True)
        with st.expander("Marchează Sarcină Finalizată"):
            id_task_fin = st.selectbox("Selectează sarcina", [f"{t['ID']} - {t['Titlu Sarcină']}" for t in tasks_df])
            if st.button("Marchează ca Finalizată"):
                tid = int(id_task_fin.split(" - ")[0])
                conn = get_connection()
                cur = conn.cursor()
                cur.execute("UPDATE sarcini SET status = 'Finalizat' WHERE id = %s", (tid,))
                conn.commit()
                conn.close()
                goleste_cache_date()
                st.success("Sarcina a fost marcată ca finalizată!")
                st.rerun()
    else:
        st.info("Nu există sarcini active.")

# === 5. CĂUTARE PORTAL & ISTORIC ===
elif modul_ales == "Căutare":
    st.markdown("""
        <div style="background: linear-gradient(135deg, #1E3A8A 0%, #4169E1 100%); padding: 18px 22px; border-radius: 10px; border: 1px solid #D4AF37; color: white; margin-bottom: 20px;">
            <h2 style="margin: 0; font-size: 22px; color: white;">🔍 Căutare Rapidă Dosar & Inspectare Istoric</h2>
        </div>
    """, unsafe_allow_html=True)

    c1, c2 = st.columns([2, 1])
    nr_q = c1.text_input("Număr dosar:", "112/2/2026")
    sursa_q = c2.selectbox("Sursă:", ["ICCJ (scj.ro)", "Portal.just.ro", "CNSC"])

    if st.button("Caută Detalii"):
        with st.spinner(f"Se interoghează {sursa_q}..."):
            info = executa_interogare(nr_q, sursa_q)
            if not info:
                st.warning(f"Dosarul nu a fost găsit pe {sursa_q}.")
            else:
                st.markdown(f"**Număr:** `{info.get('numar_formatat', nr_q)}` | **Instanță:** {info['institutie']} | **Complet:** `{info['complet']}`")
                st.info(f"**Soluție / Stadiu actual:** {info['ultima_solutie']}")
                if info.get('parti'):
                    st.write("**Părți în dosar:**")
                    st.dataframe(pd.DataFrame(info['parti']), use_container_width=True, hide_index=True)
                if info.get('sedinte'):
                    st.write("**Istoric Ședințe / Înregistrări:**")
                    st.dataframe(pd.DataFrame(info['sedinte']), use_container_width=True, hide_index=True)
