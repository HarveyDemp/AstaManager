import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import json
import os
import glob

st.set_page_config(page_title="Fantacalcio Asta Manager 2026/27", layout="wide")

# ==========================================
# STILE CSS PERSONALIZZATO
# ==========================================
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    
    .block-container {
        padding-top: 0.5rem !important;
        padding-bottom: 1rem !important;
    }

    .stApp {
        background: linear-gradient(135deg, #0f380f 0%, #1e561e 50%, #0f380f 100%);
        color: #ffffff;
    }
    
    /* Sticky Top Container per la barra dell'asta */
    div[data-testid="stVerticalBlock"] > div:has(div.sticky-header-marker) {
        position: sticky;
        top: 0.5rem;
        z-index: 999;
        background-color: rgba(15, 56, 15, 0.95);
        border: 1.5px solid #2ecc71;
        border-radius: 12px;
        padding: 12px 18px;
        box-shadow: 0px 4px 15px rgba(0,0,0,0.6);
        backdrop-filter: blur(5px);
    }

    h1, h2, h3, h4, label {
        color: #ffffff !important;
        font-family: 'Trebuchet MS', sans-serif;
    }
    
    /* Pulsante verde attivo */
    .stButton>button:not(:disabled) {
        background-color: #2ecc71 !important;
        color: #000000 !important;
        font-weight: bold;
        border-radius: 8px;
        border: none;
        box-shadow: 0px 2px 8px rgba(46, 204, 113, 0.4);
    }
    .stButton>button:not(:disabled):hover {
        background-color: #27ae60 !important;
        color: #ffffff !important;
    }

    /* Pulsante grigio disabilitato */
    .stButton>button:disabled {
        background-color: #7f8c8d !important;
        color: #bdc3c7 !important;
        border-radius: 8px;
        border: none;
        cursor: not-allowed;
        opacity: 0.6;
    }
    
    /* Card Viola con contenuto interno */
    .team-card-purple {
        background-color: rgba(106, 13, 173, 0.5);
        border: 2px solid #a855f7;
        border-radius: 12px;
        padding: 15px;
        margin-bottom: 15px;
        box-shadow: 0px 4px 12px rgba(0,0,0,0.4);
        color: #ffffff;
        max-height: 480px;
        overflow-y: auto;
    }
    .team-card-purple h3 {
        color: #f3e8ff !important;
        margin-bottom: 2px;
        font-size: 1.2rem;
    }
    .team-card-purple p.credits {
        font-size: 0.95rem;
        font-weight: bold;
        color: #e9d5ff;
        border-bottom: 1px solid rgba(255,255,255,0.2);
        padding-bottom: 8px;
        margin-bottom: 10px;
    }
    .role-header {
        font-size: 0.85rem;
        font-weight: bold;
        color: #fbcfe8;
        margin-top: 8px;
        margin-bottom: 4px;
        text-transform: uppercase;
    }
    .player-row {
        font-size: 0.82rem;
        color: #ffffff;
        padding: 2px 0;
        border-bottom: 1px dashed rgba(255,255,255,0.1);
    }
    </style>
""", unsafe_allow_html=True)

# Mappatura Abbreviazioni Squadre
SQUADRA_ABBR = {
    "Atalanta": "ATA", "Bologna": "BOL", "Cagliari": "CAG", "Como": "COM",
    "Fiorentina": "FIO", "Frosinone": "FRO", "Genoa": "GEN", "Inter": "INT",
    "Juventus": "JUV", "Lazio": "LAZ", "Lecce": "LEC", "Milan": "MIL",
    "Monza": "MON", "Napoli": "NAP", "Parma": "PAR", "Roma": "ROM",
    "Sassuolo": "SAS", "Torino": "TOR", "Udinese": "UDI", "Venezia": "VEN"
}

# Limiti Slot Ruolo
MAX_SLOTS = {"P": 3, "D": 8, "C": 8, "A": 6}

# ==========================================
# CARICAMENTO DATI MASTERDATA & FORMAZIONI
# ==========================================
@st.cache_data
def load_data():
    master_file = "Quotazioni_Fantacalcio_Stagione_2026_27.xlsx"
    formazioni_file = "Probabili_Formazioni_Serie_A_Squadre.xlsx"
    
    if os.path.exists(master_file):
        listone_df = pd.read_excel(master_file, sheet_name="Tutti", skiprows=1)
        listone_df = listone_df[['R', 'RM', 'Nome', 'Squadra', 'Qt.A', 'FVM']].dropna(subset=['Nome'])
    else:
        st.error(f"File masterdata '{master_file}' non trovato!")
        listone_df = pd.DataFrame(columns=['R', 'RM', 'Nome', 'Squadra', 'Qt.A', 'FVM'])
        
    if os.path.exists(formazioni_file):
        formazioni_df = pd.read_excel(formazioni_file, skiprows=3)
    else:
        st.error(f"File formazioni '{formazioni_file}' non trovato!")
        formazioni_df = pd.DataFrame()
        
    return listone_df, formazioni_df

listone_df, formazioni_df = load_data()

# Mappa veloce Giocatore -> Ruolo
PLAYER_TO_ROLE = dict(zip(listone_df["Nome"], listone_df["R"]))

# ==========================================
# GESTIONE SALVATAGGIO SU FILE JSON
# ==========================================
def save_asta_to_file():
    nome_asta = st.session_state.session_info["nome_asta"].replace(" ", "_")
    filename = f"asta_{nome_asta}.json"
    
    data_to_save = {
        "session_info": st.session_state.session_info,
        "asta_state": st.session_state.asta_state
    }
    
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data_to_save, f, ensure_ascii=False, indent=4)
    return filename

def load_asta_from_file(filename):
    with open(filename, "r", encoding="utf-8") as f:
        data = json.load(f)
    st.session_state.session_info = data["session_info"]
    st.session_state.asta_state = data["asta_state"]
    st.session_state.app_mode = "in_asta"

# Inizializzazione Session State
if "app_mode" not in st.session_state:
    st.session_state.app_mode = "menu"

# ==========================================
# 🏠 SCHERMATA INIZIALE / MENU PRINCIPALE
# ==========================================
if st.session_state.app_mode == "menu":
    st.markdown("<h1 style='text-align: center; margin-top: 2rem;'>⚽ FANTACALCIO ASTA MANAGER 2026/27</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; font-size: 1.2rem;'>Gestore Professionale Asta Fantacalcio in Tempo Reale</p>", unsafe_allow_html=True)
    st.divider()

    col_m1, col_m2, col_m3 = st.columns([1, 1, 1])

    with col_m1:
        st.subheader("🆕 Nuova Asta")
        nome_nuova_asta = st.text_input("Nome Asta / Lega", placeholder="Es. Lega Amici 2026")
        budget_default = st.number_input("Budget Iniziale Crediti", min_value=100, value=500)
        
        if st.button("🚀 Avvia Nuova Asta"):
            if nome_nuova_asta.strip():
                st.session_state.session_info = {"nome_asta": nome_nuova_asta.strip()}
                st.session_state.asta_state = {
                    "squadre": {"MIA SQUADRA": {"budget_iniziale": budget_default, "crediti_residui": budget_default, "rosa": []}},
                    "giocatori_acquistati": {},
                    "current_page": 0
                }
                st.session_state.app_mode = "in_asta"
                st.rerun()
            else:
                st.warning("Inserisci un nome per la nuova asta!")

    with col_m2:
        st.subheader("📂 Carica Asta")
        saved_files = glob.glob("asta_*.json")
        if saved_files:
            selected_file = st.selectbox("Seleziona Asta Salvata", options=saved_files)
            if st.button("📥 Carica Asta Selezionata"):
                load_asta_from_file(selected_file)
                st.success(f"Asta caricata da '{selected_file}'!")
                st.rerun()
        else:
            st.info("Nessuna asta salvata trovata.")

    with col_m3:
        st.subheader("🚪 Esci")
        st.write("Puoi chiudere l'applicazione e il browser in qualsiasi momento.")
        if st.button("❌ Chiudi Sessione"):
            st.success("Puoi chiudere questa scheda del browser.")

# ==========================================
# ⚽ SCHERMATA PRINCIPALE ASTA INTERATTIVA
# ==========================================
elif st.session_state.app_mode == "in_asta":
    
    col_head1, col_head2, col_head3 = st.columns([3, 1, 1])
    with col_head1:
        st.markdown(f"## 🏆 Asta: **{st.session_state.session_info['nome_asta']}**")
    with col_head2:
        if st.button("💾 Salva Asta"):
            fn = save_asta_to_file()
            st.success(f"Asta salvata in '{fn}'!")
    with col_head3:
        if st.button("🚪 Torna al Menu"):
            save_asta_to_file()
            st.session_state.app_mode = "menu"
            st.rerun()

    # BARRA DI RICERCA STICKY PERSISTENTE IN ALTO
    with st.container():
        st.markdown('<div class="sticky-header-marker" style="display:none;"></div>', unsafe_allow_html=True)
        
        col_player, col_squadra, col_prezzo, col_btn = st.columns([4, 2, 1, 1])
        
        giocatori_liberi = listone_df[~listone_df["Nome"].isin(st.session_state.asta_state["giocatori_acquistati"].keys())]
        
        options_dict = {}
        options_list = []
        for idx, row in giocatori_liberi.iterrows():
            nome = str(row["Nome"]).strip()
            sq_full = str(row["Squadra"]).strip()
            sq_abbr = SQUADRA_ABBR.get(sq_full, sq_full[:3].upper())
            
            display_label = f"{nome} ({sq_abbr})"
            options_dict[display_label] = nome
            options_list.append(display_label)
            
        with col_player:
            selected_display = st.selectbox(
                "Cerca / Seleziona Giocatore...",
                options=options_list,
                index=None, # Nessun giocatore selezionato di default
                placeholder="Digitare o selezionare un giocatore...",
                key="player_search_select"
            )
        
        with col_squadra:
            squadra_dest = st.selectbox("Assegna a Squadra", options=list(st.session_state.asta_state["squadre"].keys()))
        
        with col_prezzo:
            prezzo_acquisto = st.number_input("Prezzo (Cr)", min_value=1, value=1)
            
        # Verifica se un giocatore valido è selezionato
        is_valid_player = (selected_display is not None) and (selected_display in options_dict)

        with col_btn:
            st.write("") # Spaziatore
            if st.button("➕ Assegna", disabled=not is_valid_player):
                if is_valid_player:
                    player_real_name = options_dict[selected_display]
                    player_role = PLAYER_TO_ROLE.get(player_real_name, "D")
                    
                    # Controllo vincoli slot ruolo
                    team_rosa = st.session_state.asta_state["squadre"][squadra_dest]["rosa"]
                    current_role_count = sum(1 for p in team_rosa if p.get("Ruolo") == player_role)
                    max_allowed = MAX_SLOTS.get(player_role, 8)
                    
                    if current_role_count >= max_allowed:
                        st.error(f"Impossibile acquistare {player_real_name}! {squadra_dest} ha già raggiunto il limite di {max_allowed} slot per il ruolo {player_role}.")
                    else:
                        st.session_state.asta_state["giocatori_acquistati"][player_real_name] = {
                            "squadra_asta": squadra_dest,
                            "prezzo": prezzo_acquisto
                        }
                        st.session_state.asta_state["squadre"][squadra_dest]["crediti_residui"] -= prezzo_acquisto
                        st.session_state.asta_state["squadre"][squadra_dest]["rosa"].append({
                            "Nome": player_real_name, "Prezzo": prezzo_acquisto, "Ruolo": player_role
                        })
                        save_asta_to_file()
                        st.success(f"{player_real_name} ({player_role}) assegnato a {squadra_dest} per {prezzo_acquisto} cr!")
                        st.rerun()

    st.divider()

    # NAVIGAZIONE SCHERMATE
    pages = ["📋 Listone Master Data", "🏟️ Formazioni Tattiche Campo", "🏆 Rose & Crediti Lega"]

    col_nav_left, col_nav_title, col_nav_right = st.columns([1, 4, 1])

    with col_nav_left:
        if st.button("◀ Precedente"):
            st.session_state.asta_state["current_page"] = (st.session_state.asta_state["current_page"] - 1) % len(pages)
            st.rerun()

    with col_nav_right:
        if st.button("Successivo ▶"):
            st.session_state.asta_state["current_page"] = (st.session_state.asta_state["current_page"] + 1) % len(pages)
            st.rerun()

    with col_nav_title:
        st.markdown(f"<h3 style='text-align: center;'>{pages[st.session_state.asta_state['current_page']]}</h3>", unsafe_allow_html=True)

    st.divider()

    # SCHERMATA 1: LISTONE
    if st.session_state.asta_state["current_page"] == 0:
        st.header("📋 Listone Completo Calciatori 2026/27")
        ruolo_filter = st.radio("Filtra per Ruolo:", ["Tutti", "P", "D", "C", "A"], horizontal=True)
        
        df_display = listone_df.copy()
        if ruolo_filter != "Tutti":
            df_display = df_display[df_display["R"] == ruolo_filter]
            
        df_display["Stato"] = df_display["Nome"].apply(
            lambda x: f"❌ VENDUTO ({st.session_state.asta_state['giocatori_acquistati'][x]['squadra_asta']})" 
            if x in st.session_state.asta_state["giocatori_acquistati"] else "✅ LIBERO"
        )
        st.dataframe(df_display, use_container_width=True, height=550)

    # SCHERMATA 2: CAMPI VERTICALI CON COLORI PER RUOLO
    elif st.session_state.asta_state["current_page"] == 1:
        st.header("🏟️ Probabili Formazioni Campionato Serie A")
        
        def draw_vertical_pitch(team_name, modulo, titolari_text):
            fig, ax = plt.subplots(figsize=(3.8, 5.2))
            rect = patches.Rectangle((0, 0), 60, 100, linewidth=2, edgecolor='white', facecolor='#1e7145')
            ax.add_patch(rect)
            for stripe in range(0, 100, 10):
                if (stripe // 10) % 2 == 0:
                    ax.add_patch(patches.Rectangle((0, stripe), 60, 10, facecolor='#238250', edgecolor='none', zorder=1))

            ax.plot([0, 60], [50, 50], color='white', linewidth=1.5, zorder=2)
            circle = patches.Circle((30, 50), 8, edgecolor='white', facecolor='none', linewidth=1.5, zorder=2)
            ax.add_patch(circle)
            
            area_p = patches.Rectangle((18, 0), 24, 12, edgecolor='white', facecolor='none', linewidth=1.2, zorder=2)
            ax.add_patch(area_p)
            
            players = [p.replace("•", "").split("(")[0].strip() for p in str(titolari_text).split('\n') if p.strip()]
            
            portiere = players[0] if len(players) > 0 else None
            movimento = players[1:] if len(players) > 1 else []

            # 1. Portiere in basso al centro (Giallo Ocra)
            if portiere:
                is_bought = portiere in st.session_state.asta_state["giocatori_acquistati"]
                color = '#7f8c8d' if is_bought else '#f1c40f' # Giallo Ocra
                ax.scatter(30, 8, color=color, s=220, zorder=4, edgecolors='black')
                ax.text(30, 3.5, portiere[:11], color='white', fontsize=7, ha='center', weight='bold', zorder=5)

            lines_schema = [int(n) for n in str(modulo).split('-') if n.isdigit()]
            num_lines = len(lines_schema)
            
            if num_lines == 3:
                y_levels = [26, 54, 82]
                line_roles = ['D', 'C', 'A']
            elif num_lines == 4:
                y_levels = [24, 44, 64, 84]
                line_roles = ['D', 'C', 'C', 'A']
            else:
                y_levels = [int(22 + i * (65 / max(1, num_lines - 1))) for i in range(num_lines)]
                line_roles = ['D', 'C', 'C', 'A'][:num_lines]

            role_color_map = {
                'P': '#f1c40f', # Giallo Ocra
                'D': '#2ecc71', # Verde Chiaro
                'C': '#3498db', # Blu Chiaro
                'A': '#e74c3c'  # Rosso
            }

            idx_player = 0
            for line_idx, count in enumerate(lines_schema):
                y = y_levels[line_idx] if line_idx < len(y_levels) else 50
                x_coords = [60 - (60 * (i + 1) / (count + 1)) for i in range(count)]
                current_line_role = line_roles[line_idx] if line_idx < len(line_roles) else 'C'
                
                for x in x_coords:
                    if idx_player < len(movimento):
                        name = movimento[idx_player]
                        is_bought = name in st.session_state.asta_state["giocatori_acquistati"]
                        
                        p_role = PLAYER_TO_ROLE.get(name, current_line_role)
                        color = '#7f8c8d' if is_bought else role_color_map.get(p_role, '#3498db')
                        
                        ax.scatter(x, y, color=color, s=220, zorder=4, edgecolors='black')
                        ax.text(x, y - 3.8, name[:11], color='white', fontsize=7, ha='center', weight='bold', zorder=5)
                        idx_player += 1

            ax.set_title(f"{team_name} ({modulo})", color='white', fontsize=10, weight='bold')
            ax.set_xlim(-5, 65)
            ax.set_ylim(-5, 105)
            ax.axis('off')
            return fig

        if not formazioni_df.empty and "Squadra" in formazioni_df.columns:
            cols = st.columns(2)
            for idx, row in formazioni_df.iterrows():
                with cols[idx % 2]:
                    st.subheader(row["Squadra"])
                    fig = draw_vertical_pitch(row["Squadra"], row["Modulo"], row["Titolari (con %)"])
                    st.pyplot(fig)
                    
                    with st.expander("🔄 Dettagli Ballottaggi & Panchina"):
                        st.write("**Ballottaggi:**", row["Ballottaggi principali"])
                        st.write("**Panchina:**", row["Panchina principale"])
                        st.write("**Indisponibili:**", row["Indisponibili / Squalificati"])

    # SCHERMATA 3: ROSE CON GIOCATORI DENTRO IL BOX VIOLA E SOTTOGRUPPI RUOLO
    elif st.session_state.asta_state["current_page"] == 2:
        st.header("🏆 Gestione Partecipanti Asta & Crediti")
        
        col_add_team, col_exp = st.columns([2, 2])
        
        with col_add_team:
            with st.expander("➕ Aggiungi Squadra"):
                col_n, col_b, col_a = st.columns([2, 2, 1])
                new_team_name = col_n.text_input("Nome Squadra")
                new_team_budget = col_b.number_input("Budget", min_value=1, value=500)
                if col_a.button("Crea"):
                    if new_team_name and new_team_name not in st.session_state.asta_state["squadre"]:
                        st.session_state.asta_state["squadre"][new_team_name] = {
                            "budget_iniziale": new_team_budget,
                            "crediti_residui": new_team_budget,
                            "rosa": []
                        }
                        save_asta_to_file()
                        st.success(f"Squadra '{new_team_name}' aggiunta!")
                        st.rerun()

        with col_exp:
            st.subheader("📥 Esporta Rose Asta")
            all_export_rows = []
            for t_name, t_data in st.session_state.asta_state["squadre"].items():
                for p_item in t_data["rosa"]:
                    all_export_rows.append({
                        "Squadra Fantacalcio": t_name,
                        "Giocatore": p_item["Nome"],
                        "Ruolo": p_item.get("Ruolo", PLAYER_TO_ROLE.get(p_item["Nome"], "")),
                        "Prezzo Acquisto": p_item["Prezzo"],
                        "Crediti Residui": t_data["crediti_residui"]
                    })
            export_df = pd.DataFrame(all_export_rows) if all_export_rows else pd.DataFrame(columns=["Squadra Fantacalcio", "Giocatore", "Ruolo", "Prezzo Acquisto", "Crediti Residui"])
            
            csv_data = export_df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
            st.download_button(
                label="📄 Scarica Rose (CSV)",
                data=csv_data,
                file_name=f"rose_asta_{st.session_state.session_info['nome_asta']}.csv",
                mime="text/csv"
            )

        st.divider()
        st.subheader("📊 Rose delle Squadre (4 Colonne)")
        
        teams_items = list(st.session_state.asta_state["squadre"].items())
        
        for i in range(0, len(teams_items), 4):
            cols = st.columns(4)
            for col_idx, (team, data) in enumerate(teams_items[i:i+4]):
                with cols[col_idx]:
                    
                    players_by_role = {"P": [], "D": [], "C": [], "A": []}
                    for p in data["rosa"]:
                        r = p.get("Ruolo", PLAYER_TO_ROLE.get(p["Nome"], "C"))
                        if r in players_by_role:
                            players_by_role[r].append(p)
                            
                    card_html = f"""
                    <div class="team-card-purple">
                        <h3>🛡️ {team}</h3>
                        <p class="credits">Crediti: <span style="color:#2ecc71;">{data['crediti_residui']}</span> / {data['budget_iniziale']}</p>
                    """
                    
                    role_names = {"P": "Portieri", "D": "Difensori", "C": "Centrocampisti", "A": "Attaccanti"}
                    total_p_count = sum(len(plist) for plist in players_by_role.values())
                    
                    if total_p_count == 0:
                        card_html += '<p style="font-size:0.85rem; color:#d8b4fe; font-style:italic;">Rosa ancora vuota.</p>'
                    else:
                        for r_code in ["P", "D", "C", "A"]:
                            r_list = players_by_role[r_code]
                            max_s = MAX_SLOTS[r_code]
                            
                            card_html += f'<div class="role-header">{role_names[r_code]} ({len(r_list)}/{max_s})</div>'
                            
                            if r_list:
                                for p_item in r_list:
                                    card_html += f'<div class="player-row">• <b>{p_item["Nome"]}</b> <span style="float:right; color:#2ecc71;">{p_item["Prezzo"]} cr</span></div>'
                            else:
                                card_html += '<div class="player-row" style="color:#a78bfa; font-style:italic;">Nessuno</div>'
                                
                    card_html += '</div>'
                    st.markdown(card_html, unsafe_allow_html=True)