# === MODUL SARCINI & CALENDAR ÎN TIMP REAL ===
if modul_ales == "Sarcini":
    st.markdown("""
        <div style="background: linear-gradient(135deg, #1E3A8A 0%, #4169E1 100%); padding: 18px 22px; border-radius: 10px; border: 1px solid #D4AF37; color: white; margin-bottom: 20px;">
            <h2 style="margin: 0; font-size: 22px; color: white;">📌 Calendar & Sarcini În Timp Real</h2>
        </div>
    """, unsafe_allow_html=True)

    clienti_raw = get_clienti_cached()
    clienti_map = {c["denumire"]: c["id"] for c in clienti_raw} if clienti_raw else {}

    # Formular Adaugare / Creare Sarcină Nouă în Chenar Auriu
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
                st.info