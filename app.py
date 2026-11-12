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
    st.sidebar.markdown(
        f'<div style="background-color:#FFFFFF; padding:8px 6px; text-align:center; margin-bottom:10px;">'
        f'<img src="data:image/{ext_mime};base64,{b64_logo}" style="max-width:100%; height:auto; display:block; margin:0 auto;" />'
        f'</div>',
        unsafe_allow_html=True
    )

conn = get_connection()
cur = conn.cursor()
cur.execute("SELECT id, nume, rol FROM utilizatori WHERE activ = 1 ORDER BY id ASC")
useri_db = cur.fetchall()
conn.close()

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
    tip_buton = "primary" if este_activ else "secondary"
    cheie_buton = f"nav_{idx_m}"
    if st.sidebar.button(
        nume_modul,
        key=cheie_buton,
        type=tip_buton,
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

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, denumire FROM clienti ORDER BY denumire ASC")
    lista_clienti = cur.fetchall()
    conn.close()
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
        st.success("Toate dosarele au fost actualizate!")
        st.rerun()

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
    dosare_list = cur.fetchall()
    conn.close()

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
                    st.success(f"Clientul '{den}' a fost adăugat!")
                    st.rerun()

        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT id AS ID, denumire AS 'Denumire Client', tip_client AS 'Tip', cui_cnp AS 'CUI/CNP',
                   reprezentant AS 'Contact', telefon AS 'Telefon', email AS 'Email', adresa AS 'Adresă'
            FROM clienti ORDER BY denumire ASC
        """)
        clienti_df = cur.fetchall()
        conn.close()

        if clienti_df:
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
                        st.success(f"Clientul '{cl_de_sters}' a fost șters!")
                    except Exception as e:
                        st.error(f"Eroare la ștergere: {e}")
                    conn.close()
                    st.rerun()
        else:
            st.info("Niciun client înregistrat momentan.")

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
                st.warning("Atenție: Ștergerea contractului va elimina definitiv înregistrarea CAJ selectată.")
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
elif modul_ales == "Pontaj":
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
elif modul_ales == "Sarcini":
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
