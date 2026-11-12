import os
import re
import ssl
import smtplib
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import streamlit as st
import pandas as pd
from datetime import datetime, date
from zeep import Client
from playwright.sync_api import sync_playwright
from db_config import get_connection

st.set_page_config(page_title="CRM Toca Law", page_icon="⚖️", layout="wide")

# --- STILIZARE MENIU LATERAL ---
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
</style>
""", unsafe_allow_html=True)

# --- 1. CACHE IMAGINI ȘI LOGO (SE ÎNCARCĂ O SINGURĂ DATĂ ÎN RAM) ---
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
                descriere_activitate TEXT,
                ore_lucrate DECIMAL(6,2) DEFAULT 1.0,
                onorariu_orar DECIMAL(10,2) DEFAULT 0.0,
                valoare_totala DECIMAL(12,2) DEFAULT 0.0,
                moneda VARCHAR(20) DEFAULT 'RON'
            )
        """)
        for nume_col, tip_col in [
            ("valoare_totala", "DECIMAL(12,2) DEFAULT 0.0"),
            ("moneda", "VARCHAR(20) DEFAULT 'RON'")
        ]:
            try:
                cur.execute(f"ALTER TABLE pontaj ADD COLUMN {nume_col} {tip_col}")
            except Exception:
                pass

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
def get_pontaj_cached():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT
            p.id AS ID,
            p.data_activitate AS 'Data',
            u.nume AS 'Avocat',
            c.denumire AS 'Client',
            COALESCE(d.numar_dosar, '-') AS 'Dosar',
            p.descriere_activitate AS 'Descriere Activitate',
            p.ore_lucrate AS 'Ore',
            CONCAT(p.onorariu_orar, ' ', COALESCE(p.moneda, 'RON'), '/h') AS 'Tarif Aplicat',
            CONCAT(
                CASE WHEN COALESCE(p.valoare_totala, 0) > 0 THEN p.valoare_totala ELSE ROUND(p.ore_lucrate * p.onorariu_orar, 2) END,
                ' ', COALESCE(p.moneda, 'RON')
            ) AS 'Total Estimativ'
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
    get_pontaj_cached.clear()
    get_sarcini_cached.clear()

# --- CALCUL TARIF AUTOMAT PE ABONAMENT + DEPĂȘIRE ---
def calculeaza_tarif_si_valoare_pontaj(client_id, data_activitate, ore_noi, tarif_manual):
    an_int = data_activitate.year
    luna_int = data_activitate.month

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, tip_onorariu, valoare_onorariu, tarif_depasire, numar_ore, moneda
        FROM contracte
        WHERE client_id = %s AND status = 'Activ'
        ORDER BY id DESC LIMIT 1
    """, (client_id,))
    contract = cur.fetchone()

    cur.execute("""
        SELECT COALESCE(SUM(ore_lucrate), 0) AS ore_anterioare
        FROM pontaj
        WHERE client_id = %s AND YEAR(data_activitate) = %s AND MONTH(data_activitate) = %s
    """, (client_id, an_int, luna_int))
    res_ore = cur.fetchone()
    conn.close()

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

# --- FUNCȚIE TRIMITERE ALERTE ABONAMENT ---
def trimite_alerta_abonament(client_nume, serie_caj, ore_incluse, ore_lucrate, procent, prag_label, luna_curenta, tarif_depasire=0.0, moneda="EUR"):
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
        return False, "Credențialele SMTP sau adresele echipei nu sunt configurate."

    destinatari_lista = list(dict.fromkeys(destinatari_lista))
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

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subiect
    msg["From"] = f"CRM Toca Law <{expeditor}>"
    msg["To"] = ", ".join(destinatari_lista)
    msg.attach(MIMEText(html, "html", "utf-8"))

    try:
        if smtp_port == 465:
            ctx = ssl.create_default_context()
            server = smtplib.SMTP_SSL(smtp_server, smtp_
