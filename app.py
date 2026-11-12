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
            server = smtplib.SMTP_SSL(smtp_server, smtp_port, context=ctx, timeout=20)
        else:
            server = smtplib.SMTP(smtp_server, smtp_port, timeout=20)
            server.starttls()
        server.login(expeditor, parola)
        server.sendmail(expeditor, destinatari_lista, msg.as_string())
        server.quit()
        return True, f"Alertă {prag_label} trimisă echipei ({', '.join(destinatari_lista)})!"
    except Exception as e:
        return False, f"Eroare trimitere email alertă: {e}"

def verifica_abonament_dupa_pontaj(client_id, data_activitate):
    luna_str = data_activitate.strftime("%Y-%m")
    an_int = data_activitate.year
    luna_int = data_activitate.month

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT k.id, k.serie_numar, k.numar_ore, k.tarif_depasire, k.moneda, k.alerta_80_luna, k.alerta_100_luna, c.denumire
        FROM contracte k
        JOIN clienti c ON k.client_id = c.id
        WHERE k.client_id = %s AND k.tip_onorariu = 'Abonament' AND k.status = 'Activ' AND k.numar_ore > 0
        ORDER BY k.id DESC LIMIT 1
    """, (client_id,))
    abonament = cur.fetchone()

    if not abonament:
        conn.close()
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
        conn.commit()
        mesaje_ui.append(("error", f"🚨 Plafon 100% atins/depășit pentru {abonament['denumire']} ({total_ore:.2f} / {ore_incluse:.2f} ore în {luna_str})! {msg}"))

    elif procent >= 80.0 and abonament.get("alerta_80_luna") != luna_str:
        ok, msg = trimite_alerta_abonament(
            abonament["denumire"], abonament["serie_numar"],
            ore_incluse, total_ore, procent, "80%", luna_str, tarif_dep, moneda_ab
        )
        cur.execute("UPDATE contracte SET alerta_80_luna = %s WHERE id = %s", (luna_str, abonament["id"]))
        conn.commit()
        mesaje_ui.append(("warning", f"⚠️ Prag 80% atins pentru {abonament['denumire']} ({total_ore:.2f} / {ore_incluse:.2f} ore în {luna_str})! {msg}"))

    conn.close()
    return mesaje_ui

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
        st.dataframe(pd.DataFrame(dosare_list), use_container_width=True, hide_index=True)
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

    with tab_cl:
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

                if st.form_submit_button("Salvează Clientul") and den:
                    conn = get_connection()
                    cur = conn.cursor()
                    cur.execute("""
                        INSERT INTO clienti (denumire, tip_client, cui_cnp, adresa, reprezentant, telefon, email)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (den, tip_c, cui, adr, rep, tel, em))
                    conn.commit()
                    conn.close()
                    goleste_cache_date()
                    st.success(f"Clientul '{den}' a fost adăugat!")
                    st.rerun()

        clienti_raw = get_clienti_cached()

        if clienti_raw:
            clienti_df = [
                {
                    "ID": c["id"],
                    "Denumire Client": c["denumire"],
                    "Tip": c["tip_client"],
                    "CUI/CNP": c["cui_cnp"],
                    "Contact": c["reprezentant"],
                    "Telefon": c["telefon"],
                    "Email": c["email"],
                    "Adresă": c["adresa"],
                }
                for c in clienti_raw
            ]
            st.dataframe(pd.DataFrame(clienti_df), use_container_width=True, hide_index=True)
            with st.expander("🗑️ Șterge un client din baza de date"):
                opt_del_c = [f"{c['ID']} - {c['Denumire Client']}" for c in clienti_df]
                cl_de_sters = st.selectbox("Selectează clientul pe care dorești să-l ștergi:", opt_del_c)
                st.warning("Atenție: Ștergerea clientului va elimina și contractele/pontajele asociate acestuia, iar dosarele îi vor fi deconectate.")
                if st.button("Confirmă Ștergerea Clientului", type="secondary"):
                    c_id_del = int(cl_de_sters.split(" - ")[0])
                    conn = get_connection()
                    cur = conn.cursor()
                    try:
                        cur.execute("UPDATE dosare SET client_id = NULL WHERE client_id = %s", (c_id_del,))
                        cur.execute("DELETE FROM pontaj WHERE client_id = %s", (c_id_del,))
                        cur.execute("DELETE FROM sarcini WHERE client_id = %s", (c_id_del,))
                        cur.execute("DELETE FROM contracte WHERE client_id = %s", (c_id_del,))
                        cur.execute("DELETE FROM clienti WHERE id = %s", (c_id_del,))
                        conn.commit()
                        goleste_cache_date()
                        st.success(f"Clientul '{cl_de_sters}' a fost șters!")
                    except Exception as e:
                        st.error(f"Eroare la ștergere: {e}")
                    conn.close()
                    st.rerun()
        else:
            st.info("Niciun client înregistrat momentan.")

    with tab_caj:
        c_list = get_clienti_cached()
        c_dict = {c['denumire']: c['id'] for c in c_list} if c_list else {}

        with st.expander("➕ Înregistrează Contract Nou (CAJ)", expanded=False):
            if not c_dict:
                st.warning("Adaugă mai întâi un client în tab-ul 'Bază de Date Clienți'.")
            else:
                with st.form("form_add_caj", clear_on_submit=True):
                    c1, c2, c3 = st.columns(3)
                    serie_nr = c1.text_input("Serie și Număr CAJ * (ex: TL/2026/01)")
                    dt_c = c2.date_input("Data Încheierii", value=date.today())
                    client_caj = c3.selectbox("Client", list(c_dict.keys()))

                    c4, c5, c6, c7, c8 = st.columns([1.2, 1, 1, 1, 0.8])
                    tip_onor = c4.selectbox("Tip Onorariu", ["Abonament", "Orar", "Fix", "Succes"])
                    val_onor = c5.number_input("Tarif Orar / Valoare", min_value=0.0, step=10.0)
                    nr_ore_abon = c6.number_input("Număr ore (Abonament)", min_value=0.0, step=1.0, value=0.0)
                    tarif_dep = c7.number_input("Tarif depășire / h", min_value=0.0, step=10.0, value=0.0)
                    moneda = c8.selectbox("Monedă", ["EUR", "RON"])

                    obiect_caj = st.text_area("Obiectul asistenței juridice")

                    if st.form_submit_button("Înregistrează Contractul") and serie_nr:
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

        @st.dialog("⚠️ Confirmare ștergere contract")
        def dialog_confirmare_stergere_caj(caj_id, serie_caj, client_caj):
            st.write(f"Ești sigur că dorești să ștergi definitiv contractul **{serie_caj}** încheiat cu **{client_caj}**?")
            st.caption("Această acțiune va elimina permanent înregistrarea din baza de date.")
            col_da, col_nu = st.columns(2)
            if col_da.button("✅ Da, șterge", type="primary", use_container_width=True):
                conn = get_connection()
                cur = conn.cursor()
                try:
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

        st.markdown("#### 📋 Registru Contracte de Asistență Juridică (CAJ)")

        if contracte_rows:
            widths = [0.5, 1.3, 1.0, 1.5, 1.0, 1.3, 1.1, 1.3, 1.8, 0.8, 0.5]
            headers = [
                "ID", "Serie / Nr.", "Data", "Client", "Tip",
                "Onorariu", "Ore Incl.", "Depășire", "Consum Lună", "Status", ""
            ]
            h_cols = st.columns(widths)
            for col_h, text_h in zip(h_cols, headers):
                col_h.markdown(
                    f"<div style='font-size:12px; font-weight:700; color:#475569; padding-bottom:6px; border-bottom:2px solid #E2E8F0;'>{text_h}</div>",
                    unsafe_allow_html=True
                )

            for r in contracte_rows:
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

                r_cols = st.columns(widths)
                valori_rand = [
                    str(r["id"]),
                    r["serie_numar"],
                    str(r["data_contract"]),
                    r["client_nume"],
                    tip,
                    onorariu_str,
                    ore_str,
                    depasire_str,
                    consum_str,
                    r["status"] or "Activ"
                ]
                for col_r, val_r in zip(r_cols[:-1], valori_rand):
                    col_r.markdown(
                        f"<div style='font-size:13px; color:#0F172A; padding-top:6px;'>{val_r}</div>",
                        unsafe_allow_html=True
                    )

                if r_cols[-1].button("🗑️", key=f"del_row_caj_{r['id']}", help=f"Șterge contractul {r['serie_numar']}"):
                    dialog_confirmare_stergere_caj(r["id"], r["serie_numar"], r["client_nume"])

                st.markdown("<hr style='margin: 4px 0; border: none; border-top: 1px solid #F1F5F9;'>", unsafe_allow_html=True)
        else:
            st.info("Niciun contract înregistrat momentan. Folosește formularul de mai sus pentru a adăuga primul contract.")

# === 3. PONTAJ & TIMESHEET ===
elif modul_ales == "Pontaj":
    st.markdown("""
        <div style="background: linear-gradient(135deg, #1E3A8A 0%, #4169E1 100%); padding: 18px 22px; border-radius: 10px; border: 1px solid #D4AF37; color: white; margin-bottom: 20px;">
            <h2 style="margin: 0; font-size: 22px; color: white;">⏱️ Pontaj & Timesheet Ore Lucrate</h2>
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

    c_map = {c['denumire']: c['id'] for c in c_list}
    d_map = {d['Număr Dosar']: d['ID'] for d in d_list}

    with st.expander("➕ Adaugă Pontaj Nou", expanded=True):
        if not c_map:
            st.warning("Adaugă mai întâi cel puțin un client în sistem.")
        else:
            with st.form("form_add_timesheet", clear_on_submit=True):
                c1, c2, c3 = st.columns([1, 1.5, 1.5])
                dt_p = c1.date_input("Data Activității", value=date.today())
                cl_p = c2.selectbox("Client *", list(c_map.keys()))
                ds_p = c3.selectbox("Dosar asociat (opțional)", ["(Niciun dosar)"] + list(d_map.keys()))

                c4, c5 = st.columns([1, 1])
                ore = c4.number_input("Număr Ore (ex: 1.5 = 1h30m)", min_value=0.1, max_value=24.0, step=0.25, value=1.0)
                tarif = c5.number_input("Tarif Orar (lasă 0 pentru calcul automat din CAJ/Abonament)", min_value=0.0, step=10.0, value=0.0)

                act = st.text_area("Descrierea activității prestate *")

                if st.form_submit_button("Înregistrează Orele") and act:
                    dosar_id_val = d_map.get(ds_p, None) if ds_p != "(Niciun dosar)" else None
                    cl_id_val = c_map[cl_p]

                    tarif_aplicat, val_totala_calc, moneda_calc, nota_tarif = calculeaza_tarif_si_valoare_pontaj(
                        cl_id_val, dt_p, ore, tarif
                    )

                    conn = get_connection()
                    cur = conn.cursor()
                    cur.execute("""
                        INSERT INTO pontaj (data_activitate, utilizator_id, client_id, dosar_id, descriere_activitate, ore_lucrate, onorariu_orar, valoare_totala, moneda)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (dt_p, id_utilizator_curent, cl_id_val, dosar_id_val, act, ore, tarif_aplicat, val_totala_calc, moneda_calc))
                    conn.commit()
                    conn.close()

                    mesaje_rez = []
                    if nota_tarif:
                        mesaje_rez.append(("info", f"💶 {nota_tarif}"))

                    alerte_noi = verifica_abonament_dupa_pontaj(cl_id_val, dt_p)
                    if alerte_noi:
                        mesaje_rez.extend(alerte_noi)

                    if mesaje_rez:
                        st.session_state.alerte_pontaj_recente = mesaje_rez

                    goleste_cache_date()
                    st.success("Activitatea a fost pontată cu succes!")
                    st.rerun()

    st.subheader(f"Istoric Pontaj ({utilizator_selectat})")
    pontaj_df = get_pontaj_cached()

    if pontaj_df:
        st.dataframe(pd.DataFrame(pontaj_df), use_container_width=True, hide_index=True)
    else:
        st.info("Nu există înregistrări de pontaj.")

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
        st.dataframe(pd.DataFrame(tasks_df), use_container_width=True, hide_index=True)
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
