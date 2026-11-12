import os
import base64
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
                if len(c) >=
