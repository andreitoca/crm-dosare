import os
import base64
import streamlit as st
import pandas as pd
from datetime import datetime, date
from zeep import Client
from playwright.sync_api import sync_playwright
from db_config import get_connection

st.set_page_config(page_title="CRM Toca Law", page_icon="⚖️", layout="wide")

# --- STILIZARE MENIU LATERAL (ZONA LOGO ALBĂ + BARĂ ALBASTRU ROYAL + BUTOANE CU ICONURI PNG) ---
st.markdown("""
<style>
    /* Partea de sus (logo + utilizator) albă (primii 185px), iar tot restul barei până jos Albastru Royal */
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

    /* Selectorul de utilizator pe zona albă */
    section[data-testid="stSidebar"] div[data-baseweb="select"] > div {
        background-color: #F8FAFC !important;
        border: 1px solid #CBD5E1 !important;
        border-radius: 8px !important;
        color: #0F172A !important;
        font-size: 13px !important;
        font-weight: 600 !important;
        margin-bottom: 18px !important;
    }

    /* Stilizare chenare butoane din zona Albastru Royal */
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

    /* Buton inactiv (chenar alb pe Albastru Royal) */
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

    /* Buton activ (Verde Smarald) */
    section[data-testid="stSidebar"] div.stButton > button[kind="primary"] {
        background-color: #00B87C !important;
        border: 1px solid #00B87C !important;
        color: #FFFFFF !important;
        box-shadow: 0 3px 10px rgba(0, 184, 124, 0.35) !important;
    }

    /* Injectare icon-uri PNG albe în interiorul fiecărui buton */
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

# --- FUNCȚII DE INTEROGARE PORTALURI ---
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
def img_to_css_url(filename):
    if os.path.exists(filename):
        with open(filename, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        return f'url("data:image/png;base64,{b64}")'
    return "none"

st.markdown(f"""
<style>
    :root {{
        --icon-dosare: {img_to_css_url("File.png")};
        --icon-clienti: {img_to_css_url("Mood Dollar.png")};
        --icon-pontaj: {img_to_css_url("Alarm.png")};
        --icon-sarcini: {img_to_css_url("Clipboard.png")};
        --icon-cautare: {img_to_css_url("Zoom Check.png")};
    }}
</style>
""", unsafe_allow_html=True)

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
        <div style="background-color: #FFFFFF; padding: 8px 6px; text-align: center; margin-bottom: 10px;">
            <img src="data:image/{ext_mime};base64,{b64_logo}" style="max-width: 100%; height: auto; display: block; margin: 0 auto;" />
        </div>
    """, unsafe_allow_html=True)

conn = get_connection()
cur = conn.cursor()
cur.execute("SELECT id, nume, rol FROM utilizatori WHERE activ = 1 ORDER BY id ASC")
useri_db = cur.fetchall()
conn.close()

user_dict = {u['nume']: u['id'] for u in useri_db} if useri_db else {"Avocat Coordonator": 1}
utilizator_selectat = st.sidebar.selectbox("Utilizator", list(user_dict.keys()), key="sel_user_sidebar", label_visibility="collapsed")
id_utilizator_curent = user_dict[utilizator_selectat]

if "modul_ales" not in st.session_state:
    st.session_state.modul_ales = "Dosare"

optiuni_meniu = ["Dosare", "Clienți", "Pontaj", "Sarcini", "Căutare"]
for idx_m, nume_modul in enumerate(optiuni_meniu, start=1):
    st.sidebar.markdown(f'<span class="nav-marker-{idx_m}" style="display:none;"></span>', unsafe_allow_html=True)
    este_activ = (st.session_state.modul_ales == nume_modul)
    if st.sidebar.button(nume_modul, key=f
