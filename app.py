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

# --- STILIZARE MENIU LATERAL (CASETE ALBASTRU ROYAL) ---
st.markdown("""
<style>
    /* Ascunde cerculețul radio standard */
    section[data-testid="stSidebar"] div[role="radiogroup"] label > div:first-child {
        display: none !important;
    }

    /* Spațiere între casete */
    section[data-testid="stSidebar"] div[role="radiogroup"] {
        gap: 10px !important;
    }

    /* Aspectul fiecărei casete (Albastru Royal) */
    section[data-testid="stSidebar"] div[role="radiogroup"] label {
        background: linear-gradient(135deg, #1E3A8A 0%, #4169E1 100%) !important;
        border: 1px solid #2563EB !important;
        border-radius: 8px !important;
        padding: 12px 15px !important;
        width: 100% !important;
        cursor: pointer !important;
        transition: all 0.2s ease-in-out !important;
        box-shadow: 0 2px 5px rgba(30, 58, 138, 0.2) !important;
    }

    /* Textul alb din interiorul casetelor */
    section[data-testid="stSidebar"] div[role="radiogroup"] label p {
        color: #FFFFFF !important;
        font-weight: 600 !important;
        font-size: 14px !important;
        margin: 0 !important;
    }

    /* Efect la trecerea mouse-ului peste casetă (Hover) */
    section[data-testid="stSidebar"] div[role="radiogroup"] label:hover {
        background: linear-gradient(135deg, #172554 0%, #1D4ED8 100%) !important;
        transform: translateX(4px) !important;
        border-color: #D4AF37 !important;
    }

    /* Evidențierea casetei selectate (Active) cu bordură aurie */
    section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) {
        background: linear-gradient(135deg, #0F172A 0%, #1E3A8A 100%) !important;
        border: 2px solid #D4AF37 !important;
        box-shadow: 0 4px 10px rgba(212, 175, 55, 0.3) !important;
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
try:
    st.sidebar.image("220420_[1000xpx]_LOGO_AT.png", use_container_width=True)
except Exception:
    pass

conn = get_connection()
cur = conn.cursor()
cur.execute("SELECT id, nume, rol FROM utilizatori WHERE activ = 1 ORDER BY id ASC")
useri_db = cur.fetchall()
conn.close()

user_dict = {u['nume']: u['id'] for u in useri_db} if useri_db else {"Avocat Coordonator": 1}
utilizator_selectat = st.sidebar.selectbox("👤 Utilizator conectat:", list(user_dict.keys()))
id_utilizator_curent = user_dict[utilizator_selectat]

st.sidebar.markdown("---")
modul_ales = st.sidebar.radio(
    "Navigare:",
    [
        "📋 Portofoliu Dosare",
        "👥 Clienți & Contracte (CAJ)",
        "⏱️ Pontaj & Timesheet",
        "📌 Sarcini de Lucru (Tasks)",
        "🔍 Căutare Portal & Istoric"
    ]
)

# === 1. PORTOFOLIU DOSARE ===
if modul_ales == "📋 Portofoliu Dosare":
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
elif modul_ales == "👥 Clienți & Contracte (CAJ)":
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
                    val_
