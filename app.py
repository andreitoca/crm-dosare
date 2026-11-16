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
                status VARCHAR(50) DEFAULT 'În lucru'
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
    cur.execute("SELECT id, denumire FROM clienti ORDER BY denumire ASC")
    rows = cur.fetchall()
    conn.close()
    return rows

@st.cache_data(ttl=60, show_spinner=False)
def get_dosare_client_cached(client_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, numar_dosar, obiect FROM dosare WHERE client_id = %s ORDER BY id DESC", (client_id,))
    rows = cur.fetchall()
    conn.close()
    return rows

@st.cache_data(ttl=60, show_spinner=False)
def get_sarcini_detaliate_cached():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT
            s.id,
            s.titlu,
            s.descriere,
            s.termen_limita,
            s.ora_limita,
            s.prioritate,
            s.status,
            s.atribuit_lui,
            u.nume AS responsabil_nume,
            s.client_id,
            COALESCE(c.denumire, '-') AS client_nume,
            s.dosar_id,
            COALESCE(d.numar_dosar, 'Consultanță generală') AS dosar_nume
        FROM sarcini s
        JOIN utilizatori u ON s.atribuit_lui = u.id
        LEFT JOIN clienti c ON s.client_id = c.id
        LEFT JOIN dosare d ON s.dosar_id = d.id
        ORDER BY s.termen_limita ASC, s.id DESC
    """)
    rows = cur.fetchall()
    conn.close()
    return rows

def goleste_cache_sarcini():
    get_sarcini_detaliate_cached.clear()

# --- GENERARE RAPORT WORD SARCINI ---
def genereaza_raport_sarcini_docx(sarcini_lista, status_filtru, avocat_filtru):
    doc = Document()
    for section in doc.sections:
        section.top_margin = Inches(0.75)
        section.bottom_margin = Inches(0.75)
        section.left_margin = Inches(0.75)
        section.right_margin = Inches(0.75)

    p_b = doc.add_paragraph()
    r_b = p_b.add_run(f"TOCA LAW • RAPORT SARCINI ({status_filtru.upper()})")
    r_b.bold = True
    r_b.font.size = Pt(14)
    r_b.font.color.rgb = RGBColor(0x1E, 0x3A, 0x8A)

    p_m = doc.add_paragraph()
    p_m.paragraph_format.space_after = Pt(12)
    p_m.add_run(f"Responsabil: {avocat_filtru}    |    Data generării: {date.today().strftime('%d.%m.%Y')}")

    tabel = doc.add_table(rows=1, cols=6)
    tabel.style = "Table Grid"
    antete = ["Nr.", "Termen", "Titlu Sarcină", "Responsabil", "Client / Dosar", "Status"]
    latimi = [Inches(0.4), Inches(1.0), Inches(2.0), Inches(1.2), Inches(1.8), Inches(0.9)]

    hdr_cells = tabel.rows[0].cells
    for idx_c, text_h in enumerate(antete):
        hdr_cells[idx_c].width = latimi[idx_c]
        p_h = hdr_cells[idx_c].paragraphs[0]
        r_h = p_h.add_run(text_h)
        r_h.bold = True
        r_h.font.size = Pt(9.5)
        r_h.font.color.rgb = RGBColor(0x1E, 0x3A, 0x8A)

    for idx_r, s in enumerate(sarcini_lista, start=1):
        row_cells = tabel.add_row().cells
        dt_t = s["termen_limita"]
        dt_str = dt_t.strftime("%d.%m.%Y") if hasattr(dt_t, "strftime") else str(dt_t)
        vals = [str(idx_r), dt_str, s["titlu"], s["responsabil_nume"], f"{s['client_nume']} ({s['dosar_nume']})", s["status"]]
        for idx_c, val_str in enumerate(vals):
            row_cells[idx_c].width = latimi[idx_c]
            p_c = row_cells[idx_c].paragraphs[0]
            r_c = p_c.add_run(val_str)
            r_c.font.size = Pt(9)

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf.getvalue()

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
utilizator_selectat = st.sidebar.selectbox("Utilizator", list(user_dict.keys()), key="sel_user_sidebar", label_visibility="collapsed")
id_utilizator_curent = user_dict[utilizator_selectat]

if "modul_ales" not in st.session_state:
    st.session_state.modul_ales = "Sarcini"

optiuni_meniu = ["Dosare", "Clienți", "Pontaj", "Sarcini", "Căutare"]
for idx_m, nume_modul in enumerate(optiuni_meniu, start=1):
    st.sidebar.markdown(f'<span class="nav-marker-{idx_m}" style="display:none;"></span>', unsafe_allow_html=True)
    este_activ = (st.session_state.modul_ales == nume_modul)
    if st.sidebar.button(nume_modul, key=f"nav_{idx_m}", type="primary" if este_activ else "secondary", use_container_width=True):
        st.session_state.modul_ales = nume_modul
        st.rerun()

modul_ales = st.session_state.modul_ales

# === MODUL SARCINI & CALENDAR ÎN TIMP REAL ===
if modul_ales == "Sarcini":
    st.markdown("""
        <div style="background: linear-gradient(135deg, #1E3A8A 0%, #4169E1 100%); padding: 18px 22px; border-radius: 10px; border: 1px solid #D4AF37; color: white; margin-bottom: 20px;">
            <h2 style="margin: 0; font-size: 22px; color: white;">📌 Calendar & Sarcini În Timp Real</h2>
        </div>
    """, unsafe_allow_html=True)

    clienti_raw = get_clienti_cached()
    clienti_map = {c["denumire"]: c["id"] for c in clienti_raw} if clienti_raw else {}

    with st.container(border=True):
        st.markdown("<span class='gold-box-marker' style='display:none;'></span>", unsafe_allow_html=True)
        with st.expander("➕ Adaugă Sarcină Nouă în Calendar", expanded=False):
            with st.form("form_add_sarcină_calendar", clear_on_submit=True):
                c1, c2, c3 = st.columns([2, 1, 1])
                titlu_s = c1.text_input("Titlu Sarcină *")
                prioritate_s = c2.selectbox("Prioritate", ["Normală", "Ridicată", "Urgentă"])
                atribuit_s = c3.selectbox("Atribuit către", list(user_dict.keys()))

                c4, c5 = st.columns(2)
                termen_s = c4.date_input("Termen Limită (Ziua în Calendar)", value=date.today())
                ora_s = c5.text_input("Ora Limită", value="16:00")

                client_s = st.selectbox("Client asociat (opțional)", ["(Fără client / General)"] + list(clienti_map.keys()))
                
                dosare_client_list = []
                if client_s != "(Fără client / General)":
                    cid_sel = clienti_map[client_s]
                    dosare_client_list = get_dosare_client_cached(cid_sel)

                opt_dosare = ["💼 Consultanță generală (Fără dosar specific)"] + [f"📁 Dosar {d['numar_dosar']} - {d['obiect'][:30]}" for d in dosare_client_list]
                dosar_ales_str = st.selectbox("Asociat cu Dosar de Instanță sau Consultanță", opt_dosare)

                detalii_s = st.text_area("Descriere / Instrucțiuni sarcină")

                if st.form_submit_button("💾 Salvează Sarcina în Calendar", type="primary") and titlu_s.strip():
                    c_id_val = clienti_map.get(client_s) if client_s != "(Fără client / General)" else None
                    d_id_val = None
                    if "Dosar" in dosar_ales_str and dosare_client_list:
                        d_id_val = dosare_client_list[0]["id"]

                    conn = get_connection()
                    cur = conn.cursor()
                    cur.execute("""
                        INSERT INTO sarcini (titlu, descriere, termen_limita, ora_limita, atribuit_lui, creat_de, client_id, dosar_id, prioritate, status)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'În lucru')
                    """, (
                        titlu_s.strip(), detalii_s.strip(), termen_s, ora_s.strip(),
                        user_dict[atribuit_s], id_utilizator_curent, c_id_val, d_id_val, prioritate_s
                    ))
                    conn.commit()
                    conn.close()
                    goleste_cache_sarcini()
                    st.success("Sarcina a fost adăugată cu succes în calendar!")
                    st.rerun()

    # --- DIALOG EDITARE SARCINĂ ---
    @st.dialog("✏️ Modifică Sarcină")
    def dialog_editeaza_sarcina(s_row):
        st.caption(f"Editare sarcină ID #{s_row['id']}")
        with st.form(f"form_edit_s_{s_row['id']}"):
            t_nou = st.text_input("Titlu", value=s_row["titlu"])
            p_opt = ["Normală", "Ridicată", "Urgentă"]
            p_idx = p_opt.index(s_row["prioritate"]) if s_row["prioritate"] in p_opt else 0
            pr_nou = st.selectbox("Prioritate", p_opt, index=p_idx)
            dt_nou = st.date_input("Termen Limită", value=s_row["termen_limita"] if isinstance(s_row["termen_limita"], date) else date.today())
            desc_nou = st.text_area("Descriere", value=s_row["descriere"] or "")

            c_b1, c_b2 = st.columns(2)
            if c_b1.button("✅ Salvează", type="primary", use_container_width=True):
                conn = get_connection()
                cur = conn.cursor()
                cur.execute("UPDATE sarcini SET titlu = %s, prioritate = %s, termen_limita = %s, descriere = %s WHERE id = %s", (t_nou.strip(), pr_nou, dt_nou, desc_nou.strip(), s_row["id"]))
                conn.commit()
                conn.close()
                goleste_cache_sarcini()
                st.rerun()
            if c_b2.button("❌ Anulează", use_container_width=True):
                st.rerun()

    # --- DIALOG ȘTERGERE SARCINĂ ---
    @st.dialog("⚠️ Șterge Sarcină")
    def dialog_sterge_sarcina(s_id, s_titlu):
        st.warning(f"Ești sigur că dorești să ștergi definitiv sarcina **{s_titlu}**?")
        c_d1, c_d2 = st.columns(2)
        if c_d1.button("✅ Da, șterge", type="primary", use_container_width=True):
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("DELETE FROM sarcini WHERE id = %s", (s_id,))
            conn.commit()
            conn.close()
            goleste_cache_sarcini()
            st.rerun()
        if c_d2.button("❌ Nu", use_container_width=True):
            st.rerun()

    # --- AFIȘARE CALENDAR & LISTĂ SARCINI ÎN TIMP REAL ---
    st.markdown("### 📅 Sarcini Planificate în Calendar & Listă Echipă")
    
    sarcini_toate = get_sarcini_detaliate_cached()

    fc1, fc2, fc3 = st.columns([1.5, 1.5, 1.5])
    filtru_status = fc1.selectbox("Filtrează după status:", ["Toate", "În lucru", "Finalizat"])
    filtru_avocat = fc2.selectbox("Filtrează după responsabil:", ["Toată echipa", utilizator_selectat] + [u for u in user_dict.keys() if u != utilizator_selectat])
    
    luni_ro = {1: "Ianuarie", 2: "Februarie", 3: "Martie", 4: "Aprilie", 5: "Mai", 6: "Iunie", 7: "Iulie", 8: "August", 9: "Septembrie", 10: "Octombrie", 11: "Noiembrie", 12: "Decembrie"}
    luna_selectata = fc3.selectbox("Lună calendar:", list(luni_ro.values()), index=date.today().month - 1)
    luna_nr = [k for k, v in luni_ro.items() if v == luna_selectata][0]

    sarcini_filtrate = []
    for s in sarcini_toate:
        dt_s = s["termen_limita"]
        if isinstance(dt_s, str):
            dt_s = datetime.strptime(dt_s, "%Y-%m-%d").date()
        if dt_s.month != luna_nr:
            continue
        if filtru_status != "Toate" and s["status"] != filtru_status:
            continue
        if filtru_avocat != "Toată echipa" and s["responsabil_nume"] != filtru_avocat:
            continue
        sarcini_filtrate.append((s, dt_s))

    # --- PANOU EXPORT RAPORT SARCINI (WORD) ---
    with st.expander("📄 Generează Raport Sarcini (Format Word .docx)", expanded=False):
        if not DOCX_DISPONIBIL:
            st.warning("Librăria `python-docx` nu este instalată pe server.")
        else:
            s_word_list = [s[0] for s in sarcini_filtrate]
            if s_word_list:
                docx_bytes = genereaza_raport_sarcini_docx(s_word_list, filtru_status, filtru_avocat)
                st.download_button(
                    label=f"⬇️ Descarcă Raport Word Sarcini ({len(s_word_list)} înregistrări)",
                    data=docx_bytes,
                    file_name=f"Raport_Sarcini_{luna_selectata}_{filtru_status}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    type="primary"
                )
            else:
                st.info("Nu există sarcini pentru criteriile selectate.")

    if sarcini_filtrate:
        sarcini_filtrate.sort(key=lambda x: x[1])
        zile_grupate = {}
        for s, dt in sarcini_filtrate:
            zile_grupate.setdefault(dt, []).append(s)

        for zi_dt, lista_s in zile_grupate.items():
            zi_str = zi_dt.strftime("%d.%m.%Y (%A)")
            st.markdown(f"""
                <div style='background-color:#F1F5F9; padding:8px 14px; border-radius:6px; margin-top:14px; margin-bottom:6px; display:flex; justify-content:space-between; align-items:center;'>
                    <span style='font-weight:700; color:#1E3A8A; font-size:14px;'>📅 {zi_str}</span>
                    <span style='font-weight:600; color:#334155; font-size:13px;'>{len(lista_s)} sarcini programate</span>
                </div>
            """, unsafe_allow_html=True)

            for s_item in lista_s:
                sc_desc, sc_meta, sc_fin, sc_ed, sc_del = st.columns([3.8, 2.2, 1.2, 0.45, 0.45], vertical_alignment="center")
                with sc_desc:
                    st.markdown(f"""
                        <div style='font-size:14px; font-weight:600; color:#0F172A;'>{s_item['titlu']}</div>
                        <div style='font-size:12px; color:#64748B;'>{s_item['descriere'] or 'Fără descriere'}</div>
                    """, unsafe_allow_html=True)
                with sc_meta:
                    st.markdown(f"""
                        <div style='font-size:12px; color:#334155;'>👤 <strong>{s_item['responsabil_nume']}</strong></div>
                        <div style='font-size:11px; color:#64748B;'>🏢 {s_item['client_nume']} • 📁 {s_item['dosar_nume']}</div>
                    """, unsafe_allow_html=True)
                with sc_fin:
                    if s_item["status"] != "Finalizat":
                        if st.button("✔ Finalizat", key=f"fin_s_{s_item['id']}", help="Marchează sarcina ca finalizată"):
                            conn = get_connection()
                            cur = conn.cursor()
                            cur.execute("UPDATE sarcini SET status = 'Finalizat' WHERE id = %s", (s_item["id"],))
                            conn.commit()
                            conn.close()
                            goleste_cache_sarcini()
                            st.rerun()
                    else:
                        st.markdown("<div style='font-size:12px; color:#059669; font-weight:700; padding-top:6px;'>✅ Finalizat</div>", unsafe_allow_html=True)
                with sc_ed:
                    if st.button("✏️", key=f"edit_s_{s_item['id']}", help="Modifică sarcina"):
                        dialog_editeaza_sarcina(s_item)
                with sc_del:
                    if st.button("🗑️", key=f"del_s_{s_item['id']}", help="Șterge sarcina"):
                        dialog_sterge_sarcina(s_item["id"], s_item["titlu"])

                st.markdown("<hr style='margin: 4px 0; border: none; border-top: 1px solid #F1F5F9;'>", unsafe_allow_html=True)
    else:
        st.info(f"Nicio sarcină înregistrată pentru luna {luna_selectata} cu filtrele selectate.")