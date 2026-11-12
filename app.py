import streamlit as st
import pandas as pd
from datetime import datetime, date
from zeep import Client
import subprocess
import sys
import json
import re
import requests
from bs4 import BeautifulSoup
from db_config import get_connection

st.set_page_config(
    page_title="TOCA SCA CRM - Dosare, Clienți & Pontaj",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

WSDL_URL = "http://portalquery.just.ro/Query.asmx?WSDL"

import os
import base64

# --- STILIZARE MENIU LATERAL (ZONA SUS ALBĂ + MENIU ALBASTRU ROYAL CU ICONURI OUTLINE) ---
st.markdown("""
<style>
    /* Bara laterală rămâne albă pentru logo și utilizator */
    section[data-testid="stSidebar"] {
        background-color: #FFFFFF !important;
        border-right: 1px solid #E2E8F0 !important;
        min-width: 220px !important;
        max-width: 240px !important;
    }

    section[data-testid="stSidebar"] > div:first-child {
        padding: 18px 14px !important;
        background-color: #FFFFFF !important;
    }

    /* Ascunde eticheta "Navigare:" și cerculețul radio */
    section[data-testid="stSidebar"] div[data-testid="stWidgetLabel"],
    section[data-testid="stSidebar"] div[role="radiogroup"] label > div:first-child,
    section[data-testid="stSidebar"] div[role="radiogroup"] [data-baseweb="radio"] > div:first-child {
        display: none !important;
        width: 0 !important;
        height: 0 !important;
    }

    /* Doar zona meniului de navigare primește fundal Albastru Royal */
    section[data-testid="stSidebar"] div[role="radiogroup"] {
        background-color: #1E3A8A !important;
        padding: 10px 8px !important;
        border-radius: 12px !important;
        gap: 6px !important;
        width: 100% !important;
        box-shadow: 0 4px 12px rgba(30, 58, 138, 0.15) !important;
    }

    /* Elementele de meniu pe fundalul Albastru Royal */
    section[data-testid="stSidebar"] div[role="radiogroup"] label {
        background-color: transparent !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 12px 8px !important;
        width: 100% !important;
        display: flex !important;
        flex-direction: column !important;
        align-items: center !important;
        justify-content: center !important;
        text-align: center !important;
        cursor: pointer !important;
        transition: all 0.2s ease !important;
    }

    /* Icon-ul vectorial minimalist (outline alb) generat înaintea textului */
    section[data-testid="stSidebar"] div[role="radiogroup"] label::before {
        content: "" !important;
        display: block !important;
        width: 28px !important;
        height: 28px !important;
        margin-bottom: 6px !important;
        background-repeat: no-repeat !important;
        background-position: center !important;
        background-size: contain !important;
        opacity: 0.78 !important;
    }

    /* 1. Icon Dosare (Portofoliu) */
    section[data-testid="stSidebar"] div[role="radiogroup"] label:nth-of-type(1)::before {
        background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23FFFFFF' stroke-width='1.6' stroke-linecap='round' stroke-linejoin='round'%3E%3Crect x='3' y='3' width='18' height='18' rx='4'/%3E%3Cpath d='M8 7v10M12 7v7M16 7v4'/%3E%3C/svg%3E") !important;
    }

    /* 2. Icon Clienți (exact ca în model) */
    section[data-testid="stSidebar"] div[role="radiogroup"] label:nth-of-type(2)::before {
        background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23FFFFFF' stroke-width='1.6' stroke-linecap='round' stroke-linejoin='round'%3E%3Crect x='3' y='3' width='18' height='18' rx='4'/%3E%3Ccircle cx='12' cy='10' r='3'/%3E%3Cpath d='M7 18c1.2-2.2 3.1-3.2 5-3.2s3.8 1 5 3.2'/%3E%3C/svg%3E") !important;
    }

    /* 3. Icon Pontaj (Activități / Calendar cu bifă ca în model) */
    section[data-testid="stSidebar"] div[role="radiogroup"] label:nth-of-type(3)::before {
        background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23FFFFFF' stroke-width='1.6' stroke-linecap='round' stroke-linejoin='round'%3E%3Crect x='3' y='4' width='18' height='17' rx='4'/%3E%3Cpath d='M8 2v3M16 2v3M9 13l2 2 4-4'/%3E%3C/svg%3E") !important;
    }

    /* 4. Icon Sarcini (Pachet / Dosar lucru ca în model) */
    section[data-testid="stSidebar"] div[role="radiogroup"] label:nth-of-type(4)::before {
        background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23FFFFFF' stroke-width='1.6' stroke-linecap='round' stroke-linejoin='round'%3E%3Crect x='3' y='3' width='18' height='18' rx='4'/%3E%3Cpath d='M9 3v5l3-1.5L15 8V3M9 15h6'/%3E%3C/svg%3E") !important;
    }

    /* 5. Icon Căutare / Statistici (exact ca în model) */
    section[data-testid="stSidebar"] div[role="radiogroup"] label:nth-of-type(5)::before {
        background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23FFFFFF' stroke-width='1.6' stroke-linecap='round' stroke-linejoin='round'%3E%3Crect x='3' y='3' width='18' height='18' rx='4'/%3E%3Cpath d='M8 16v-2M12 16v-4M16 16v-6M7 11c3 0 6-2 9-5'/%3E%3C/svg%3E") !important;
    }

    /* Textul din meniu */
    section[data-testid="stSidebar"] div[role="radiogroup"] label p {
        color: #CBD5E1 !important;
        font-size: 13px !important;
        font-weight: 500 !important;
        line-height: 1.2 !important;
        text-align: center !important;
        margin: 0 !important;
    }

    /* Efect Hover */
    section[data-testid="stSidebar"] div[role="radiogroup"] label:hover {
        background-color: rgba(255, 255, 255, 0.1) !important;
    }
    section[data-testid="stSidebar"] div[role="radiogroup"] label:hover p,
    section[data-testid="stSidebar"] div[role="radiogroup"] label:hover::before {
        color: #FFFFFF !important;
        opacity: 1 !important;
    }

    /* Elementul Activ - Verde Smarald */
    section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) {
        background-color: #00B87C !important;
    }
    section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) p,
    section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked)::before {
        color: #FFFFFF !important;
        font-weight: 700 !important;
        opacity: 1 !important;
    }

    /* Selectorul de utilizator pe zona albă */
    section[data-testid="stSidebar"] div[data-baseweb="select"] > div {
        background-color: #F8FAFC !important;
        border: 1px solid #CBD5E1 !important;
        border-radius: 8px !important;
        color: #0F172A !important;
        font-size: 13px !important;
        font-weight: 600 !important;
    }
</style>
""", unsafe_allow_html=True)
# --- 1. INTEROGARE PORTAL.JUST.RO ---
def interogheaza_instanta(numar_dosar):
    try:
        client = Client(WSDL_URL)
        rezultate = client.service.CautareDosare(numarDosar=numar_dosar.strip())
        if not rezultate:
            return None
        
        dosar = rezultate[0]
        institutie = str(dosar.institutie)
        obiect = str(dosar.obiect or "-")
        complet_actual = "-"
        ultimul_termen = "-"
        ultima_solutie = "Fără soluție consemnată încă"
        lista_sedinte = []

        if hasattr(dosar, 'sedinte') and dosar.sedinte and hasattr(dosar.sedinte, 'DosarSedinta'):
            sedinte = dosar.sedinte.DosarSedinta
            for s in sedinte:
                data_dt = s.data
                data_str = data_dt.strftime("%d.%m.%Y") if hasattr(data_dt, 'strftime') else str(data_dt)
                sol = s.solutieSumar or "Fără soluție consemnată încă"
                comp = s.complet or "-"
                lista_sedinte.append({
                    "Data": data_str,
                    "Ora": s.ora or "-",
                    "Complet": comp,
                    "Document": s.documentSedinta or "-",
                    "Soluție pe scurt": sol
                })
            if lista_sedinte:
                complet_actual = lista_sedinte[0]['Complet']
                ultimul_termen = f"{lista_sedinte[0]['Data']} ({lista_sedinte[0]['Ora']})"
                ultima_solutie = f"[{lista_sedinte[0]['Data']}] {lista_sedinte[0]['Soluție pe scurt']}"

        parti_list = []
        if hasattr(dosar, 'parti') and dosar.parti and hasattr(dosar.parti, 'DosarParte'):
            parti_list = [{"Nume Parte": p.nume, "Calitate": p.calitateParte} for p in dosar.parti.DosarParte]

        return {
            "numar_formatat": numar_dosar.strip(),
            "institutie": institutie,
            "complet": complet_actual,
            "obiect": obiect,
            "ultimul_termen": ultimul_termen,
            "ultima_solutie": ultima_solutie,
            "sedinte": lista_sedinte,
            "parti": parti_list
        }
    except Exception:
        return None

# --- 2. INTEROGARE PORTAL CNSC ---
def interogheaza_cnsc(input_dosar):
    script_code = """
import sys, json
from playwright.sync_api import sync_playwright

input_dosar = sys.argv[1]
parti = [p.strip() for p in input_dosar.strip().split("/") if p.strip()]

if len(parti) == 3:
    nr_dosar, complet_introdus, an_dosar = parti[0], parti[1].upper(), parti[2]
elif len(parti) == 2:
    nr_dosar, complet_introdus, an_dosar = parti[0], "", parti[1]
else:
    nr_dosar, complet_introdus, an_dosar = parti[0], "", "2026"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(ignore_https_errors=True)
    page = context.new_page()
    page.goto("http://portal.cnsc.ro/istoricdosare.html", timeout=30000)
    page.wait_for_timeout(3000)
    
    page.fill("#ctl00_ctl04_ctl01_ctl02_ctl02_ctrl2", nr_dosar)
    page.fill("#ctl00_ctl04_ctl01_ctl02_ctl03_ctrl3", an_dosar)
    page.press("#ctl00_ctl04_ctl01_ctl02_ctl02_ctrl2", "Enter")
    page.wait_for_timeout(4000)
    
    rows = page.locator("tbody tr").all()
    if not rows:
        print("REZULTAT_JSON:" + json.dumps({"found": False}))
        browser.close()
        sys.exit(0)
        
    celule = [c.inner_text().strip() for c in rows[0].locator("td").all()]
    if len(celule) < 6:
        print("REZULTAT_JSON:" + json.dumps({"found": False}))
        browser.close()
        sys.exit(0)
        
    contestator = celule[2]
    autoritate = celule[3]
    complet_gasit = celule[4] or complet_introdus or "-"
    status_dosar = celule[5]
    
    butoane = rows[0].locator("a, input, button").all()
    text_detalii = ""
    if butoane:
        butoane[0].click()
        page.wait_for_timeout(3000)
        text_detalii = page.locator("body").inner_text()
        
    lines = [l.strip() for l in text_detalii.split("\\n") if l.strip()]
    data_decizie = "-"
    nr_decizie = "-"
    solutie = status_dosar
    inregistrari = []
    
    for i, line in enumerate(lines):
        if line == "Dată decizie fond" and i + 1 < len(lines):
            if lines[i+1] not in ["Nr. decizie fond", "Soluție"]:
                data_decizie = lines[i+1]
        elif line == "Nr. decizie fond" and i + 1 < len(lines):
            if lines[i+1] not in ["Soluție", "NUMĂR ÎNREGISTRARE"]:
                nr_decizie = lines[i+1]
        elif line == "Soluție" and i + 1 < len(lines):
            if not lines[i+1].startswith("NUMĂR ÎNREGISTRARE"):
                solutie = lines[i+1]
        elif "\\t" in line and line[0].isdigit():
            seg = [s.strip() for s in line.split("\\t") if s.strip()]
            if len(seg) >= 4:
                inregistrari.append({
                    "Nr. Înreg.": seg[0],
                    "Data": seg[1],
                    "Tip": seg[2],
                    "Document": seg[3],
                    "Emitent / Destinatar": " / ".join(seg[4:])
                })
                
    rezultat_solutie = f"[{status_dosar}] "
    if solutie and solutie != status_dosar:
        rezultat_solutie += f"{solutie} (Decizia nr. {nr_decizie} / {data_decizie})"
    elif inregistrari:
        rezultat_solutie += f"Ultima înreg: {inregistrari[0]['Document']} ({inregistrari[0]['Data']})"
        
    numar_oficial = f"{nr_dosar}/{complet_gasit}/{an_dosar}"
    out = {
        "found": True,
        "numar_formatat": numar_oficial,
        "institutie": "CNSC",
        "complet": complet_gasit,
        "obiect": f"{contestator} vs. {autoritate}",
        "ultimul_termen": data_decizie if data_decizie != "-" else (inregistrari[0]["Data"] if inregistrari else status_dosar),
        "ultima_solutie": rezultat_solutie,
        "sedinte": inregistrari,
        "parti": [
            {"Nume Parte": contestator, "Calitate": "Contestator"},
            {"Nume Parte": autoritate, "Calitate": "Autoritate Contractantă"}
        ]
    }
    print("REZULTAT_JSON:" + json.dumps(out))
    browser.close()
"""
    try:
        proc = subprocess.run(
            [sys.executable, "-c", script_code, input_dosar],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60
        )
        for line in proc.stdout.splitlines():
            if line.startswith("REZULTAT_JSON:"):
                data = json.loads(line.replace("REZULTAT_JSON:", "", 1))
                if data.get("found"):
                    return data
        return None
    except Exception:
        return None

# --- 3. INTEROGARE ÎNALTA CURTE DE CASAȚIE ȘI JUSTIȚIE (scj.ro) ---
def interogheaza_iccj(numar_dosar):
    clean_nr = numar_dosar.strip()
    script_iccj = """
import sys, json
from playwright.sync_api import sync_playwright

nr_cautat = sys.argv[1].strip()

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    page = context.new_page()
    page.goto("https://www.scj.ro/738/Cautare-dosare-si-parti", timeout=35000)
    page.wait_for_timeout(2000)
    
    page.fill("input[name*='NumarDosar'], #NumarDosar, input[type='text']", nr_cautat)
    page.press("input[name*='NumarDosar'], #NumarDosar, input[type='text']", "Enter")
    page.wait_for_timeout(3500)
    
    rows = page.locator("table tr").all()
    if len(rows) <= 1:
        print("REZULTAT_JSON:" + json.dumps({"found": False}))
        browser.close()
        sys.exit(0)
        
    links = page.locator("table tr td a").all()
    if links:
        links[0].click()
        page.wait_for_timeout(3000)
        
    text_page = page.locator("body").inner_text()
    lines = [l.strip() for l in text_page.split("\\n") if l.strip()]
    
    sectie = "Înalta Curte de Casație și Justiție"
    obiect = "-"
    complet = "-"
    termen = "-"
    solutie = "Fără soluție consemnată încă"
    parti = []
    sedinte = []
    
    for i, line in enumerate(lines):
        if "Secţia" in line or "Secția" in line:
            sectie = f"ICCJ - {line}"
        elif "Obiect:" in line and i + 1 < len(lines):
            obiect = lines[i+1]
        elif "Complet:" in line and i + 1 < len(lines):
            complet = lines[i+1]
        elif "Termen:" in line and i + 1 < len(lines):
            termen = lines[i+1]
        elif ("Soluţie:" in line or "Soluție:" in line) and i + 1 < len(lines):
            solutie = lines[i+1]
            
    out = {
        "found": True,
        "numar_formatat": nr_cautat,
        "institutie": sectie,
        "complet": complet,
        "obiect": obiect if obiect != "-" else f"Dosar recurs {nr_cautat}",
        "ultimul_termen": termen,
        "ultima_solutie": solutie,
        "sedinte": sedinte,
        "parti": parti
    }
    print("REZULTAT_JSON:" + json.dumps(out))
    browser.close()
"""
    try:
        proc = subprocess.run(
            [sys.executable, "-c", script_iccj, clean_nr],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=50
        )
        for line in proc.stdout.splitlines():
            if line.startswith("REZULTAT_JSON:"):
                d = json.loads(line.replace("REZULTAT_JSON:", "", 1))
                if d.get("found"):
                    return d
        
        url = f"https://www.scj.ro/738/Cautare-dosare-si-parti?NumarDosar={clean_nr}"
        resp = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        if resp.status_code == 200 and clean_nr in resp.text:
            return {
                "numar_formatat": clean_nr,
                "institutie": "Înalta Curte de Casație și Justiție",
                "complet": "Complet filtru",
                "obiect": "Recurs",
                "ultimul_termen": "În procedură de filtru",
                "ultima_solutie": "[Pe rol] În procedură de filtru / Raport admisibilitate",
                "sedinte": [],
                "parti": []
            }
        return None
    except Exception:
        return None

def executa_interogare(numar, sursa):
    if sursa == "Portal.just.ro":
        return interogheaza_instanta(numar)
    elif sursa == "CNSC":
        return interogheaza_cnsc(numar)
    elif sursa == "ICCJ (scj.ro)":
        return interogheaza_iccj(numar)
    return None

# --- BARA LATERALĂ & NAVIGARE ---
logo_gasit = None
for ext in ["", ".png", ".jpg", ".jpeg", ".webp"]:
    nume_fisier = f"220420_[1000xpx]_LOGO_AT{ext}"
    if os.path.exists(nume_fisier):
        logo_gasit = nume_fisier
        break

if logo_gasit:
    with open(logo_gasit, "rb") as img_f:
        b64_logo = base64.b64encode(img_f.read()).decode()
    ext_mime = "png" if not logo_gasit.lower().endswith(("jpg", "jpeg")) else "jpeg"
    st.sidebar.markdown(f"""
        <div style="
            background-color: #FFFFFF;
            padding: 8px 6px;
            text-align: center;
            margin-bottom: 12px;
        ">
            <img src="data:image/{ext_mime};base64,{b64_logo}" style="max-width: 100%; height: auto; display: block; margin: 0 auto;" />
        </div>
    """, unsafe_allow_html=True)

conn = get_connection()
cur = conn.cursor()
cur.execute("SELECT id, nume, rol FROM utilizatori WHERE activ = 1 ORDER BY id ASC")
useri_db = cur.fetchall()
conn.close()

user_dict = {u['nume']: u['id'] for u in useri_db} if useri_db else {"Avocat Coordonator": 1}
utilizator_selectat = st.sidebar.selectbox("Utilizator", list(user_dict.keys()), label_visibility="collapsed")
id_utilizator_curent = user_dict[utilizator_selectat]

st.sidebar.markdown("---")
modul_ales = st.sidebar.radio(
    "Navigare:",
    [
        "📁\nDosare",
        "👤\nClienți",
        "⏱️\nPontaj",
        "☑️\nSarcini",
        "🔍\nCăutare"
    ]
)
# === 1. PORTOFOLIU DOSARE ===
if modul_ales == "📁\nDosare":
    st.markdown("""
        <div style="
            background: linear-gradient(135deg, #1E3A8A 0%, #4169E1 100%);
            padding: 22px 26px;
            border-radius: 10px;
            border: 1px solid #D4AF37;
            color: white;
            margin-bottom: 25px;
            box-shadow: 0 4px 15px rgba(30, 58, 138, 0.3);
        ">
            <h1 style="margin: 0; font-size: 26px; font-weight: 700; color: #FFFFFF;">Evidența și monitorizarea litigiilor</h1>
            <p style="margin: 5px 0 0 0; font-size: 14px; color: #E0E7FF;">Instanțe judecătorești (portal.just.ro), CNSC & Înalta Curte de Casație și Justiție (ICCJ)</p>
        </div>
    """, unsafe_allow_html=True)
    
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, denumire FROM clienti ORDER BY denumire ASC")
    clienti_list = cur.fetchall()
    conn.close()
    
    dict_clienti = {c['denumire']: c['id'] for c in clienti_list}
    optiuni_clienti = ["(Fără client asociat)"] + list(dict_clienti.keys())

    with st.expander("➕ Adaugă un dosar nou în monitorizare", expanded=False):
        with st.form("form_add_dosar", clear_on_submit=True):
            c1, c2, c3 = st.columns([2, 1.2, 2])
            nr_nou = c1.text_input("Număr Dosar (ex: 112/2/2026, 3504/C5/2026 sau 33730/197/2026)")
            sursa_noua = c2.selectbox("Sursă", ["Portal.just.ro", "CNSC", "ICCJ (scj.ro)"])
            client_selectat = c3.selectbox("Client asociat", optiuni_clienti)
            btn_salveaza = st.form_submit_button("Salvează Dosar în CRM")
            
            if btn_salveaza and nr_nou:
                with st.spinner(f"Se interoghează baza de date {sursa_noua}..."):
                    info = executa_interogare(nr_nou, sursa_noua)
                    
                    if not info:
                        st.error(f"Dosarul nu a fost găsit pe {sursa_noua}. Verifică numărul introdus.")
                    else:
                        c_id = dict_clienti.get(client_selectat, None)
                        c_nume = client_selectat if client_selectat != "(Fără client asociat)" else "-"
                        acum = datetime.now().strftime("%d.%m.%Y %H:%M")
                        nr_fmt = info.get('numar_formatat', nr_nou.strip())
                        
                        conn = get_connection()
                        cur = conn.cursor()
                        try:
                            cur.execute("""
                                INSERT INTO dosare (numar_dosar, sursa, client, institutie, complet, obiect, ultimul_termen, ultima_solutie, ultima_verificare, client_id)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            """, (nr_fmt, sursa_noua, c_nume, info['institutie'], info['complet'], info['obiect'], info['ultimul_termen'], info['ultima_solutie'], acum, c_id))
                            conn.commit()
                            st.success(f"Dosarul {nr_fmt} a fost salvat cu succes!")
                        except Exception as e:
                            st.error(f"Eroare la salvare (posibil număr duplicat): {e}")
                        conn.close()
                        st.rerun()

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT 
            d.id AS ID,
            d.numar_dosar AS 'Număr Dosar',
            COALESCE(c.denumire, d.client) AS 'Client',
            d.sursa AS 'Sursă',
            d.institutie AS 'Instanță / Autoritate',
            d.complet AS 'Complet',
            d.obiect AS 'Obiect',
            d.ultimul_termen AS 'Termen / Decizie',
            d.ultima_solutie AS 'Ultima Soluție consemnată',
            d.ultima_verificare AS 'Ultima Verificare'
        FROM dosare d
        LEFT JOIN clienti c ON d.client_id = c.id
        ORDER BY d.id DESC
    """)
    rows = cur.fetchall()
    conn.close()

    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        with st.expander("🗑️ Șterge un dosar din monitorizare"):
            dosar_del = st.selectbox("Alege dosarul", [r['Număr Dosar'] for r in rows])
            if st.button("Confirmă Ștergerea"):
                conn = get_connection()
                cur = conn.cursor()
                cur.execute("DELETE FROM dosare WHERE numar_dosar = %s", (dosar_del,))
                conn.commit()
                conn.close()
                st.success("Dosarul a fost șters.")
                st.rerun()
    else:
        st.info("Nu există dosare monitorizate în acest moment.")

# === 2. CLIENȚI & CONTRACTE (CAJ) ===
elif modul_ales == "👤\nClienți":
    st.markdown("""
        <div style="background: linear-gradient(135deg, #1E3A8A 0%, #4169E1 100%); padding: 18px 22px; border-radius: 10px; border: 1px solid #D4AF37; color: white; margin-bottom: 20px;">
            <h2 style="margin: 0; font-size: 22px; color: white;">👥 Gestiune Clienți & Contracte de Asistență (CAJ)</h2>
        </div>
    """, unsafe_allow_html=True)
    
    tab_cl, tab_caj = st.tabs(["📁 Bază de Date Clienți", "📄 Contracte de Asistență (CAJ)"])
    
    with tab_cl:
        with st.expander("➕ Adaugă Client Nou", expanded=False):
            with st.form("form_add_client", clear_on_submit=True):
                col1, col2 = st.columns(2)
                den = col1.text_input("Denumire / Nume Client *")
                tip = col2.selectbox("Tip Persoană", ["Persoană Juridică", "Persoană Fizică"])
                cui = col1.text_input("CUI / CNP")
                reg = col2.text_input("Nr. Reg. Comerțului (J)")
                adresa = col1.text_area("Adresă Sediu Social / Domiciliu")
                obs = col2.text_area("Observații")
                email = col1.text_input("Email Contact")
                tel = col2.text_input("Telefon Contact")
                
                if st.form_submit_button("Salvează Clientul") and den:
                    conn = get_connection()
                    cur = conn.cursor()
                    try:
                        cur.execute("""
                            INSERT INTO clienti (denumire, tip_persoana, cui_cnp, reg_com, sediu_adresa, email_contact, telefon_contact, observatii)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """, (den, tip, cui, reg, adresa, email, tel, obs))
                        conn.commit()
                        st.success(f"Clientul '{den}' a fost înregistrat cu succes!")
                    except Exception as e:
                        st.error(f"Eroare: {e}")
                    conn.close()
                    st.rerun()
                    
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT 
                c.id AS ID, 
                c.denumire AS 'Denumire', 
                c.tip_persoana AS 'Tip', 
                c.cui_cnp AS 'CUI / CNP', 
                COALESCE(
                    GROUP_CONCAT(DISTINCT CONCAT(k.serie_numar, ' (', k.tip_onorariu, ': ', k.valoare_onorariu, ' ', k.moneda, ')') SEPARATOR ' | '), 
                    '-'
                ) AS 'Contracte Asistență (CAJ)',
                c.email_contact AS 'Email', 
                c.telefon_contact AS 'Telefon' 
            FROM clienti c
            LEFT JOIN contracte k ON c.id = k.client_id
            GROUP BY c.id, c.denumire, c.tip_persoana, c.cui_cnp, c.email_contact, c.telefon_contact
            ORDER BY c.denumire ASC
        """)
        clienti_df = cur.fetchall()
        conn.close()

        if clienti_df:
            st.dataframe(pd.DataFrame(clienti_df), use_container_width=True, hide_index=True)

            with st.expander("🗑️ Șterge un client din baza de date"):
                optiuni_del_client = [f"{c['ID']} - {c['Denumire']}" for c in clienti_df]
                client_de_sters = st.selectbox("Selectează clientul pe care dorești să-l elimini:", optiuni_del_client)
                st.warning("Atenție: Ștergerea clientului va elimina și contractele de asistență (CAJ) asociate acestuia, iar dosarele aferente vor rămâne în portofoliu fără client asociat.")

                if st.button("Confirmă Ștergerea Clientului", type="secondary"):
                    c_id_del = int(client_de_sters.split(" - ")[0])
                    conn = get_connection()
                    cur = conn.cursor()
                    try:
                        cur.execute("UPDATE dosare SET client_id = NULL WHERE client_id = %s", (c_id_del,))
                        cur.execute("DELETE FROM pontaj WHERE client_id = %s", (c_id_del,))
                        cur.execute("DELETE FROM sarcini WHERE client_id = %s", (c_id_del,))
                        cur.execute("DELETE FROM contracte WHERE client_id = %s", (c_id_del,))
                        cur.execute("DELETE FROM clienti WHERE id = %s", (c_id_del,))
                        conn.commit()
                        st.success(f"Clientul '{client_de_sters}' a fost șters cu succes!")
                    except Exception as e:
                        st.error(f"Eroare la ștergerea clientului: {e}")
                    conn.close()
                    st.rerun()
        else:
            st.info("Niciun client înregistrat încă.")

    with tab_caj:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, denumire FROM clienti ORDER BY denumire ASC")
        c_list = cur.fetchall()
        conn.close()
        
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
                    
                    c4, c5, c6 = st.columns(3)
                    tip_onor = c4.selectbox("Tip Onorariu", ["Orar", "Fix", "Succes"])
                    val_onor = c5.number_input("Valoare Onorariu", min_value=0.0, step=50.0)
                    moneda = c6.selectbox("Monedă", ["RON", "EUR"])
                    
                    obiect_caj = st.text_area("Obiectul asistenței juridice")
                    
                    if st.form_submit_button("Înregistrează Contractul") and serie_nr:
                        conn = get_connection()
                        cur = conn.cursor()
                        try:
                            cur.execute("""
                                INSERT INTO contracte (serie_numar, data_contract, client_id, obiect_contract, tip_onorariu, valoare_onorariu, moneda, status)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, 'Activ')
                            """, (serie_nr, dt_c, c_dict[client_caj], obiect_caj, tip_onor, val_onor, moneda))
                            conn.commit()
                            st.success(f"Contractul {serie_nr} a fost salvat!")
                        except Exception as e:
                            st.error(f"Eroare: {e}")
                        conn.close()
                        st.rerun()
                        
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT 
                k.id AS ID,
                k.serie_numar AS 'Serie/Număr CAJ',
                k.data_contract AS 'Data',
                c.denumire AS 'Client',
                k.tip_onorariu AS 'Tip Onorariu',
                CONCAT(k.valoare_onorariu, ' ', k.moneda) AS 'Valoare',
                k.obiect_contract AS 'Obiect',
                k.status AS 'Status'
            FROM contracte k
            JOIN clienti c ON k.client_id = c.id
            ORDER BY k.id DESC
        """)
        caj_df = cur.fetchall()
        conn.close()
        
        if caj_df:
            st.dataframe(pd.DataFrame(caj_df), use_container_width=True, hide_index=True)

            with st.expander("🗑️ Șterge un contract de asistență (CAJ)"):
                optiuni_del_caj = [f"{k['ID']} - {k['Serie/Număr CAJ']} ({k['Client']})" for k in caj_df]
                contract_de_sters = st.selectbox("Selectează contractul pe care dorești să-l elimini:", optiuni_del_caj)
                st.warning("Atenție: Ștergerea contractului va elimina definitiv înregistrarea CAJ selectată (clientul și dosarele sale rămân intacte).")

                if st.button("Confirmă Ștergerea Contractului", type="secondary"):
                    k_id_del = int(contract_de_sters.split(" - ")[0])
                    conn = get_connection()
                    cur = conn.cursor()
                    try:
                        cur.execute("DELETE FROM contracte WHERE id = %s", (k_id_del,))
                        conn.commit()
                        st.success(f"Contractul '{contract_de_sters}' a fost șters cu succes!")
                    except Exception as e:
                        st.error(f"Eroare la ștergerea contractului: {e}")
                    conn.close()
                    st.rerun()
        else:
            st.info("Niciun contract înregistrat.")

# === 3. PONTAJ & TIMESHEET ===
elif modul_ales == "⏱️\nPontaj":
    st.markdown("""
        <div style="background: linear-gradient(135deg, #1E3A8A 0%, #4169E1 100%); padding: 18px 22px; border-radius: 10px; border: 1px solid #D4AF37; color: white; margin-bottom: 20px;">
            <h2 style="margin: 0; font-size: 22px; color: white;">⏱️ Pontaj & Timesheet Ore Lucrate</h2>
        </div>
    """, unsafe_allow_html=True)
    
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, denumire FROM clienti ORDER BY denumire ASC")
    c_list = cur.fetchall()
    cur.execute("SELECT id, numar_dosar FROM dosare ORDER BY id DESC")
    d_list = cur.fetchall()
    conn.close()
    
    c_map = {c['denumire']: c['id'] for c in c_list}
    d_map = {d['numar_dosar']: d['id'] for d in d_list}
    
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
                tarif = c5.number_input("Tarif Orar (RON)", min_value=0.0, step=50.0, value=0.0)
                
                act = st.text_area("Descrierea activității prestate *")
                
                if st.form_submit_button("Înregistrează Orele") and act:
                    dosar_id_val = d_map.get(ds_p, None) if ds_p != "(Niciun dosar)" else None
                    conn = get_connection()
                    cur = conn.cursor()
                    cur.execute("""
                        INSERT INTO pontaj (data_activitate, utilizator_id, client_id, dosar_id, descriere_activitate, ore_lucrate, onorariu_orar)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (dt_p, id_utilizator_curent, c_map[cl_p], dosar_id_val, act, ore, tarif))
                    conn.commit()
                    conn.close()
                    st.success("Activitatea a fost pontată cu succes!")
                    st.rerun()

    st.subheader(f"Istoric Pontaj ({utilizator_selectat})")
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
            CONCAT(ROUND(p.ore_lucrate * p.onorariu_orar, 2), ' RON') AS 'Total Estimativ'
        FROM pontaj p
        JOIN utilizatori u ON p.utilizator_id = u.id
        JOIN clienti c ON p.client_id = c.id
        LEFT JOIN dosare d ON p.dosar_id = d.id
        ORDER BY p.data_activitate DESC, p.id DESC
    """)
    pontaj_df = cur.fetchall()
    conn.close()
    
    if pontaj_df:
        st.dataframe(pd.DataFrame(pontaj_df), use_container_width=True, hide_index=True)
    else:
        st.info("Nu există înregistrări de pontaj.")

# === 4. SARCINI DE LUCRU (TASKS) ===
elif modul_ales == "☑️\nSarcini":
    st.markdown("""
        <div style="background: linear-gradient(135deg, #1E3A8A 0%, #4169E1 100%); padding: 18px 22px; border-radius: 10px; border: 1px solid #D4AF37; color: white; margin-bottom: 20px;">
            <h2 style="margin: 0; font-size: 22px; color: white;">📌 Sarcini de Lucru & Termene Echipă</h2>
        </div>
    """, unsafe_allow_html=True)
    
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, denumire FROM clienti ORDER BY denumire ASC")
    cl_t = cur.fetchall()
    conn.close()
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
                st.success("Sarcina a fost adăugată!")
                st.rerun()

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
    tasks_df = cur.fetchall()
    conn.close()
    
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
                st.success("Sarcina a fost marcată ca finalizată!")
                st.rerun()
    else:
        st.info("Nu există sarcini active.")

# === 5. CĂUTARE PORTAL & ISTORIC ===
elif modul_ales == "🔍\nCăutare":
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
