import streamlit as st
from zeep import Client
import pandas as pd
from datetime import datetime
import subprocess
import sys
import json
import re
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from db_config import get_connection

st.set_page_config(page_title="CRM Monitorizare Dosare & CNSC", layout="wide")

WSDL_URL = "http://portalquery.just.ro/Query.asmx?WSDL"

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
        ultima_solutie = "Fara solutie consemnata inca"
        lista_sedinte = []

        if hasattr(dosar, "sedinte") and dosar.sedinte and hasattr(dosar.sedinte, "DosarSedinta"):
            sedinte = dosar.sedinte.DosarSedinta
            for s in sedinte:
                data_dt = s.data
                data_str = data_dt.strftime("%d.%m.%Y") if hasattr(data_dt, "strftime") else str(data_dt)
                sol = s.solutieSumar or "Fara solutie consemnata inca"
                comp = s.complet or "-"
                lista_sedinte.append({
                    "Data": data_str,
                    "Ora": s.ora or "-",
                    "Complet": comp,
                    "Document": s.documentSedinta or "-",
                    "Solutie pe scurt": sol
                })
            if lista_sedinte:
                complet_actual = lista_sedinte[0]["Complet"]
                ultimul_termen = f"{lista_sedinte[0]['Data']} ({lista_sedinte[0]['Ora']})"
                ultima_solutie = f"[{lista_sedinte[0]['Data']}] {lista_sedinte[0]['Solutie pe scurt']}"

        parti_list = []
        if hasattr(dosar, "parti") and dosar.parti and hasattr(dosar.parti, "DosarParte"):
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

# --- 3. TRIMITERE EMAIL DIRECT cPanel ---
def trimite_email_notificare(numar_dosar, client_nume, institutie, complet, solutie_veche, solutie_noua):
    conn = get_connection()
    with conn.cursor() as c:
        c.execute("SELECT smtp_server, smtp_port, email_expeditor, parola_email, email_destinatar FROM setari_email WHERE id = 1")
        row = c.fetchone()
    conn.close()
    
    if not row or not row["email_expeditor"] or not row["parola_email"] or not row["email_destinatar"]:
        return False, "Completează datele expeditorului în Tab-ul 3."
        
    smtp_server = row["smtp_server"] or "toca-law.ro"
    smtp_port = int(row["smtp_port"] or 465)
    expeditor = row["email_expeditor"]
    parola = row["parola_email"]
    destinatari_lista = [email.strip() for email in re.split(r"[,;]+", row["email_destinatar"]) if email.strip()]
    if not destinatari_lista:
        return False, "Nu a fost specificată nicio adresă validă de destinatar."

    subiect = f"[Actualizare Dosar] {numar_dosar} ({complet}) - {client_nume}"
    
    html_body = f"""<!DOCTYPE html>
<html>
<head>
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
</head>
<body style="font-family: Arial, Helvetica, sans-serif; color: #222; line-height: 1.5; margin: 0; padding: 15px;">
    <div style="background-color: #1E3A8A; color: #ffffff; padding: 14px 18px; border-radius: 6px;">
        <h2 style="margin: 0; font-size: 18px; color: #ffffff;">Modificare consemnată în dosarul {numar_dosar}</h2>
    </div>
    <div style="padding: 16px; border: 1px solid #E5E7EB; border-radius: 6px; margin-top: 12px; background-color: #ffffff;">
        <p style="margin: 6px 0;"><strong>Client / Proiect:</strong> {client_nume}</p>
        <p style="margin: 6px 0;"><strong>Instanță / Autoritate:</strong> {institutie} &mdash; <strong>Complet:</strong> {complet}</p>
        <hr style="border: 0; border-top: 1px solid #E5E7EB; margin: 15px 0;">
        <p style="margin: 6px 0; color: #4B5563;"><strong>Stare anterioară:</strong><br>{solutie_veche}</p>
        <div style="background-color: #FEF3C7; padding: 12px 16px; border-left: 4px solid #F59E0B; margin: 15px 0; border-radius: 4px;">
            <strong style="color: #92400E; display: block; margin-bottom: 4px;">Soluție / Stare NOUĂ consemnată:</strong>
            <span style="color: #1F2937; font-size: 15px; font-weight: bold;">{solutie_noua}</span>
        </div>
        <p style="font-size: 11px; color: #9CA3AF; margin-top: 20px;">
            Notificare automată transmisă din cPanel ({expeditor}) către: {', '.join(destinatari_lista)}
        </p>
    </div>
</body>
</html>"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subiect
    msg["From"] = f"Notificari Dosare <{expeditor}>"
    msg["To"] = ", ".join(destinatari_lista)
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        if smtp_port == 465:
            context = ssl.create_default_context()
            server = smtplib.SMTP_SSL(smtp_server, smtp_port, context=context, timeout=20)
        else:
            server = smtplib.SMTP(smtp_server, smtp_port, timeout=20)
            server.starttls()
            
        server.login(expeditor, parola)
        server.sendmail(expeditor, destinatari_lista, msg.as_string())
        server.quit()
        return True, f"Email expediat cu succes de la {expeditor} către {len(destinatari_lista)} destinatari!"
    except Exception as e:
        return False, f"Eroare cPanel SMTP: {e}"

# --- 4. INTERFAȚA GRAFICĂ ---
st.title("⚖️ Sistem CRM Dosare & CNSC (Baza MySQL cPanel)")

tab1, tab2, tab3 = st.tabs(["📋 Portofoliu Dosare (CRM)", "🔍 Căutare Rapidă & Istoric", "⚙️ Configurare Expeditor & Email"])

with tab1:
    st.subheader("Adaugă un dosar nou în monitorizare")
    with st.form("form_adauga_dosar", clear_on_submit=True):
        col1, col2, col3, col4 = st.columns([2, 1.5, 2, 1])
        nr_nou = col1.text_input("Număr Dosar (ex: 3504/C5/2026 sau 33730/197/2026)")
        sursa_noua = col2.selectbox("Sursă", ["CNSC", "Portal.just.ro"])
        client_nou = col3.text_input("Nume Client / Proiect")
        buton_adauga = col4.form_submit_button("➕ Salvează în CRM")
        
        if buton_adauga and nr_nou:
            with st.spinner(f"Se extrag datele din {sursa_noua}..."):
                if sursa_noua == "Portal.just.ro":
                    info = interogheaza_instanta(nr_nou)
                else:
                    info = interogheaza_cnsc(nr_nou)
                    
                if not info:
                    st.error(f"Dosarul {nr_nou} nu a fost găsit pe {sursa_noua}! Verifică numărul.")
                else:
                    conn = get_connection()
                    acum = datetime.now().strftime("%d.%m.%Y %H:%M")
                    nr_salvat = info.get("numar_formatat", nr_nou.strip())
                    comp_salvat = info.get("complet", "-")
                    try:
                        with conn.cursor() as c:
                            c.execute("""
                                INSERT INTO dosare (numar_dosar, sursa, client, institutie, complet, obiect, ultimul_termen, ultima_solutie, ultima_verificare)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                            """, (nr_salvat, sursa_noua, client_nou or "-", info["institutie"], comp_salvat, info["obiect"], info["ultimul_termen"], info["ultima_solutie"], acum))
                        conn.commit()
                        st.success(f"Dosarul {nr_salvat} (Complet {comp_salvat}) a fost salvat în MySQL!")
                    except Exception as e:
                        st.warning("Acest dosar există deja sau a intervenit o eroare.")
                    finally:
                        conn.close()

    st.divider()
    
    col_titlu, col_buton = st.columns([3, 1])
    col_titlu.subheader("Dosarele monitorizate (partajate în timp real)")
    
    if col_buton.button("🔄 Verifică TOATE dosarele acum", use_container_width=True):
        conn = get_connection()
        with conn.cursor() as c:
            c.execute("SELECT id, numar_dosar, sursa, client, institutie, complet, ultima_solutie FROM dosare")
            toate = c.fetchall()
            
            modificari_gasite = 0
            progres = st.progress(0)
            
            for idx, rand in enumerate(toate):
                d_id = rand["id"]
                d_nr = rand["numar_dosar"]
                d_sursa = rand["sursa"]
                d_client = rand["client"]
                d_inst = rand["institutie"]
                d_comp = rand["complet"]
                d_sol_veche = rand["ultima_solutie"]
                
                info = interogheaza_instanta(d_nr) if d_sursa == "Portal.just.ro" else interogheaza_cnsc(d_nr)
                acum = datetime.now().strftime("%d.%m.%Y %H:%M")
                
                if info:
                    sol_noua = info["ultima_solutie"]
                    termen_nou = info["ultimul_termen"]
                    comp_nou = info.get("complet", d_comp)
                    
                    if sol_noua != d_sol_veche:
                        modificari_gasite += 1
                        st.toast(f"Modificare în dosarul {d_nr}!", icon="🔔")
                        ok, msg_mail = trimite_email_notificare(d_nr, d_client, info["institutie"], comp_nou, d_sol_veche, sol_noua)
                        if ok:
                            st.info(f"Notificare trimisă pentru dosarul {d_nr}.")
                        else:
                            st.warning(f"Modificare detectată la {d_nr}, dar emailul nu a plecat: {msg_mail}")
                            
                    c.execute("""
                        UPDATE dosare 
                        SET complet = %s, ultimul_termen = %s, ultima_solutie = %s, ultima_verificare = %s
                        WHERE id = %s
                    """, (comp_nou, termen_nou, sol_noua, acum, d_id))
                progres.progress((idx + 1) / max(len(toate), 1))
                
            conn.commit()
        conn.close()
        if modificari_gasite == 0:
            st.success("Toate dosarele au fost verificate. Nu au apărut modificări.")
        else:
            st.success(f"Verificare completă! {modificari_gasite} dosare au suferit modificări.")

    conn = get_connection()
    try:
        df_dosare = pd.read_sql("SELECT * FROM dosare", conn)
    except Exception:
        df_dosare = pd.DataFrame()
    conn.close()
    
    if not df_dosare.empty:
        redenumiri = {
            "numar_dosar": "Număr Dosar",
            "complet": "Complet",
            "client": "Client",
            "sursa": "Sursă",
            "institutie": "Instanță / Autoritate",
            "obiect": "Obiect / Părți",
            "ultimul_termen": "Termen / Dată Decizie",
            "ultima_solutie": "Ultima Soluție / Stadiu",
            "ultima_verificare": "Verificat la"
        }
        df_display = df_dosare.rename(columns=redenumiri)
        cols_show = [v for k, v in redenumiri.items() if v in df_display.columns]
        st.dataframe(df_display[cols_show], use_container_width=True, hide_index=True)
        
        with st.expander("🗑️ Șterge un dosar din monitorizare"):
            col_nr = "Număr Dosar" if "Număr Dosar" in df_display.columns else "numar_dosar"
            id_de_sters = st.selectbox("Selectează dosarul de șters", df_display[col_nr].tolist())
            if st.button("Șterge dosarul selectat"):
                conn = get_connection()
                with conn.cursor() as c:
                    c.execute("DELETE FROM dosare WHERE numar_dosar = %s", (id_de_sters,))
                conn.commit()
                conn.close()
                st.rerun()
    else:
        st.info("Nu există niciun dosar salvat în baza de date MySQL.")

with tab2:
    st.subheader("Inspectează toate ședințele, părțile sau înregistrările unui dosar")
    c1, c2 = st.columns([2, 1])
    nr_cautare = c1.text_input("Număr dosar (ex: 3504/C5/2026 sau 33730/197/2026):", "3504/C5/2026")
    sursa_cautare = c2.selectbox("Sursă căutare", ["CNSC", "Portal.just.ro"])
    
    if st.button("🔍 Căutare detalii complete"):
        with st.spinner("Se interoghează portalul..."):
            if sursa_cautare == "Portal.just.ro":
                info = interogheaza_instanta(nr_cautare)
            else:
                info = interogheaza_cnsc(nr_cautare)
                
            if not info:
                st.warning("Dosarul nu a fost găsit.")
            else:
                st.markdown(f"**Număr:** `{info.get('numar_formatat', nr_cautare)}` | **Instanță:** {info['institutie']} | **Complet:** `{info.get('complet', '-')}` | **Obiect / Părți:** {info['obiect']}")
                st.info(f"**Soluție / Stadiu actual:** {info['ultima_solutie']}")
                if info["parti"]:
                    st.write("**Părți:**")
                    st.dataframe(pd.DataFrame(info["parti"]), use_container_width=True, hide_index=True)
                if info["sedinte"]:
                    st.write("**Istoric Ședințe / Înregistrări CNSC:**")
                    st.dataframe(pd.DataFrame(info["sedinte"]), use_container_width=True, hide_index=True)

with tab3:
    st.subheader("Configurare Cont Expeditor cPanel (Stocat securizat în MySQL)")
    
    conn = get_connection()
    with conn.cursor() as c:
        c.execute("SELECT smtp_server, smtp_port, email_expeditor, parola_email, email_destinatar FROM setari_email WHERE id = 1")
        setari = c.fetchone()
    conn.close()
    
    v_server = setari["smtp_server"] if (setari and setari["smtp_server"]) else "toca-law.ro"
    v_port = setari["smtp_port"] if (setari and setari["smtp_port"]) else 465
    v_exp = setari["email_expeditor"] if (setari and setari["email_expeditor"]) else "actualizari@toca-law.ro"
    v_pass = setari["parola_email"] if (setari and setari["parola_email"]) else ""
    v_dest_default = "madalina.toca@toca-law.ro, andrei.smircea@toca-law.ro, andrei.toca@toca-law.ro"
    v_dest = setari["email_destinatar"] if (setari and setari["email_destinatar"]) else v_dest_default

    with st.form("form_email_cpanel"):
        c1, c2 = st.columns([2, 1])
        s_server = c1.text_input("Server SMTP cPanel", value=v_server)
        s_port = c2.number_input("Port SMTP", value=int(v_port))
        
        s_exp = st.text_input("Adresă Expeditor", value=v_exp)
        s_pass = st.text_input("Parola contului din cPanel", value=v_pass, type="password")
        s_dest = st.text_area("Adresele destinatare (separate prin virgulă):", value=v_dest)
        
        col_s1, col_s2 = st.columns([1, 1])
        salveaza_btn = col_s1.form_submit_button("💾 Salvează Setările în MySQL")
        test_btn = col_s2.form_submit_button("📩 Trimite un email de test")
        
        if salveaza_btn:
            conn = get_connection()
            with conn.cursor() as c:
                c.execute("""
                    INSERT INTO setari_email (id, smtp_server, smtp_port, email_expeditor, parola_email, email_destinatar)
                    VALUES (1, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE 
                        smtp_server=VALUES(smtp_server),
                        smtp_port=VALUES(smtp_port),
                        email_expeditor=VALUES(email_expeditor),
                        parola_email=VALUES(parola_email),
                        email_destinatar=VALUES(email_destinatar)
                """, (s_server, s_port, s_exp, s_pass, s_dest))
            conn.commit()
            conn.close()
            st.success("Setările au fost salvate cu succes în MySQL!")

        if test_btn:
            with st.spinner("Se transmite emailul prin serverul cPanel..."):
                ok, msg = trimite_email_notificare(
                    "3504/C5/2026", 
                    "CLIENT DE TEST S.R.L.", 
                    "CNSC", 
                    "C5", 
                    "În așteptare", 
                    "Admite contestația (Verificare conexiune MySQL & cPanel)"
                )
                if ok:
                    st.success(f"Bravo! {msg}")
                else:
                    st.error(f"Eroare: {msg}")
