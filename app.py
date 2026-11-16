# --- VIZUALIZARE KANBAN COLORATĂ PENTRU SARCINI / DOSARE ---
st.markdown("""
<style>
    .kanban-col {
        background-color: #F8FAFC;
        border-radius: 10px;
        padding: 10px;
        min-height: 400px;
        border: 1px solid #E2E8F0;
    }
    .kanban-card {
        background-color: #FFFFFF;
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        border: 1px solid #CBD5E1;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("### 🗂️ Panou Kanban - Stadiul Activităților și Sarcinilor")

# Definim stările și culorile asociate tab-ului cardului / antetului
stari_kanban = {
    "Nou": {"culoare": "#F472B6", "nume": "Nou"},          # Roz
    "În lucru": {"culoare": "#FACC15", "nume": "În lucru"},  # Galben
    "Pe rol": {"culoare": "#94A3B8", "nume": "Pe rol"},      # Gri deschis
    "Așteptare": {"culoare": "#38BDF8", "nume": "Așteptare"},# Albastru
    "Finalizat": {"culoare": "#4ADE80", "nume": "Finalizat"},# Verde
    "Renunțări": {"culoare": "#F87171", "nume": "Renunțări"} # Roșu
}

cols_kanban = st.columns(len(stari_kanban))

# Preluăm sarcinile sau dosarele din baza de date
sarcini_kanban = get_sarcini_detaliate_cached()

for idx, (stare_cheie, config) in enumerate(stari_kanban.items()):
    with cols_kanban[idx]:
        # Antetul coloanei colorat
        st.markdown(f"""
            <div style="background-color: {config['culoare']}; color: #0F172A; font-weight: 700; text-align: center; padding: 8px; border-radius: 6px 6px 0 0; font-size: 13px;">
                {config['nume']}
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown('<div class="kanban-col">', unsafe_allow_html=True)
        
        # Filtrăm elementele pentru starea curentă (mapăm statusul existent sau folosim un status implicit)
        elemente_stare = [s for s in sarcini_kanban if s.get("status", "În lucru") == stare_cheie or (stare_cheie == "În lucru" and s.get("status") == "În lucru")]
        
        if not elemente_stare:
            st.markdown("<p style='font-size: 12px; color: #94A3B8; text-align: center; margin-top: 20px;'>Niciun element</p>", unsafe_allow_html=True)
        
        for item in elemente_stare:
            st.markdown(f"""
                <div class="kanban-card">
                    <div style="font-weight: 700; font-size: 13px; color: #1E3A8A;">{item.get('titlu', 'Fără titlu')}</div>
                    <div style="font-size: 11px; color: #475569; margin-top: 4px;">👤 {item.get('responsabil_nume', '-')}</div>
                    <div style="font-size: 11px; color: #64748B;">🏢 {item.get('client_nume', '-')}</div>
                    <div style="font-size: 10px; color: #94A3B8; margin-top: 6px;">📅 {item.get('termen_limita', '-')}</div>
                </div>
            """, unsafe_allow_html=True)
            
        st.markdown('</div>', unsafe_allow_html=True)