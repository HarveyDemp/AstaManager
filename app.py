import os
import urllib.parse
import bcrypt
import pandas as pd
import streamlit as st
from st_supabase_connection import SupabaseConnection, execute_query
import itsdangerous
from streamlit_cookies_controller import CookieController
import streamlit.components.v1 as components

# 1. Configurazione Pagina (sempre la prima istruzione Streamlit)
st.set_page_config(
    page_title="Fantacalcio Asta Manager 2026/27",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ==========================================
# 🗄️ CONNESSIONE SUPABASE
# ==========================================
supabase = st.connection(name="supabase_connection", type=SupabaseConnection, ttl=None)

cookie_controller = CookieController(key="fantacalcio_cookie_controller")

COOKIE_NAME = "fantacalcio_auth"
COOKIE_MAX_AGE_DAYS = 30
serializer = itsdangerous.URLSafeTimedSerializer(st.secrets["cookie_secret"])


def create_auth_cookie(username: str, name: str):
    token = serializer.dumps({
        "username": username,
        "name": name
    })
    cookie_controller.set(
        COOKIE_NAME,
        token,
        max_age=60 * 60 * 24 * COOKIE_MAX_AGE_DAYS
    )


def verify_auth_cookie():
    token = cookie_controller.get(COOKIE_NAME)
    if not token:
        return None

    try:
        return serializer.loads(
            token,
            max_age=60 * 60 * 24 * COOKIE_MAX_AGE_DAYS
        )
    except itsdangerous.SignatureExpired:
        st.warning("Cookie scaduto")
        return None
    except itsdangerous.BadSignature as e:
        st.warning(f"Cookie non valido: {e}")
        return None


def hash_password(password: str) -> str:
    """Genera l'hash bcrypt di una password in chiaro."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Verifica una password in chiaro contro il suo hash bcrypt."""
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def get_user_by_username(username: str):
    """Recupera la riga utente da Supabase (o None se non esiste)."""
    result = execute_query(
        supabase.table("users").select("*").eq("username", username),
        ttl=0,
    )
    return result.data[0] if result.data else None


def create_user(username: str, name: str, email: str, password: str):
    """Crea un nuovo utente sulla tabella Supabase 'users'."""
    execute_query(
        supabase.table("users").insert(
            {
                "username": username,
                "name": name,
                "email": email,
                "password_hash": hash_password(password),
            }
        ),
        ttl=0,
    )


def do_logout():
    cookie_controller.remove(COOKIE_NAME)
    st.session_state.authentication_status = False
    st.session_state.username = None
    st.session_state.name = None
    st.session_state.app_mode = "menu"
    st.rerun()


# ==========================================
# 🔐 SCHERMATA LOGIN / REGISTRAZIONE
# ==========================================
if "authentication_status" not in st.session_state:
    st.session_state.authentication_status = False
if "username" not in st.session_state:
    st.session_state.username = None
if "name" not in st.session_state:
    st.session_state.name = None
if "cookie_pending" not in st.session_state:
    st.session_state.cookie_pending = False

if st.session_state.cookie_pending:
    st.session_state.cookie_pending = False
    st.rerun()

# Auto-login da cookie persistente
if not st.session_state.authentication_status:
    cookies = cookie_controller.getAll()
    if cookies is None:
        st.stop()
        
    cookie_data = verify_auth_cookie()
    if cookie_data:
        st.session_state.authentication_status = True
        st.session_state.username = cookie_data["username"]
        st.session_state.name = cookie_data["name"]

if not st.session_state.authentication_status:
    st.markdown(
        """
        <style>
        .login-hero {
            text-align: center;
            margin-top: 1.5rem;
            margin-bottom: 1.2rem;
        }
        .login-hero h1 {
            font-size: 2.1rem;
            margin-bottom: 0.2rem;
            color: #ffffff;
        }
        .login-hero p {
            color: #cbd5e1;
            font-size: 0.95rem;
            margin: 0;
        }
        </style>
        <div class="login-hero">
            <h1>⚽ Fantacalcio Asta Manager 2026/27</h1>
            <p>Accedi al tuo account o registrati per iniziare a gestire la tua asta</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_login_left, col_login_center, col_login_right = st.columns([1, 1.3, 1])

    with col_login_center:
        with st.container(border=True):
            tab_login, tab_register = st.tabs(["🔑 Accedi", "📝 Registrati"])

            with tab_login:
                with st.form("form_login", clear_on_submit=False):
                    login_username = st.text_input("Username")
                    login_password = st.text_input("Password", type="password")
                    submitted_login = st.form_submit_button("🔑 Accedi", use_container_width=True)

                if submitted_login:
                    if not login_username.strip() or not login_password:
                        st.error("❌ Inserisci username e password.")
                    else:
                        try:
                            user_row = get_user_by_username(login_username.strip())
                        except Exception as e:
                            user_row = None
                            st.error(f"⚠️ Errore di connessione al database: {e}")
                        else:
                            if user_row and verify_password(login_password, user_row["password_hash"]):
                                st.session_state.authentication_status = True
                                st.session_state.username = user_row["username"]
                                st.session_state.name = user_row["name"]
                                create_auth_cookie(user_row["username"], user_row["name"])
                                st.session_state.cookie_pending = True
                            else:
                                st.error("❌ Credenziali non valide.")

                if st.session_state.authentication_status and not st.session_state.cookie_pending:
                    st.rerun()

            with tab_register:
                with st.form("form_register", clear_on_submit=True):
                    reg_name = st.text_input("Nome e Cognome")
                    reg_email = st.text_input("Email")
                    reg_username = st.text_input("Username")
                    reg_password = st.text_input("Password", type="password")
                    reg_password2 = st.text_input("Ripeti Password", type="password")
                    submitted_register = st.form_submit_button("📝 Registrati", use_container_width=True)

                if submitted_register:
                    if not all([reg_name.strip(), reg_email.strip(), reg_username.strip(), reg_password, reg_password2]):
                        st.error("❌ Compila tutti i campi.")
                    elif reg_password != reg_password2:
                        st.error("❌ Le due password inserite non coincidono.")
                    elif len(reg_password) < 6:
                        st.error("❌ La password deve avere almeno 6 caratteri.")
                    else:
                        try:
                            if get_user_by_username(reg_username.strip()):
                                st.error("❌ Username già registrato. Scegline un altro.")
                            else:
                                create_user(
                                    reg_username.strip(),
                                    reg_name.strip(),
                                    reg_email.strip(),
                                    reg_password,
                                )
                                st.success(
                                    f"✅ Account per **{reg_username.strip()}** creato con successo! "
                                    f"Ora puoi accedere dalla scheda 'Accedi'."
                                )
                        except Exception as e:
                            st.error(f"⚠️ Errore durante la registrazione: {e}")

    st.stop()

# ==========================================
# 🔓 UTENTE AUTENTICATO
# ==========================================
user_id = st.session_state.username
user_name = st.session_state.name or user_id

# ==========================================
# STILE CSS PERSONALIZZATO
# ==========================================
CARD_BORDER_COLORS = ["#3b82f6", "#10b981", "#f43f5e", "#a855f7", "#06b6d4", "#f59e0b"]
_card_color_css = ""
for _idx, _color in enumerate(CARD_BORDER_COLORS):
    _card_color_css += f"""
    [class*="st-key-teamcard__c{_idx}__"] {{
        background: linear-gradient(135deg, rgba(20, 30, 55, 0.95), rgba(10, 15, 30, 0.98)) !important;
        border: 2px solid {_color} !important;
        border-radius: 14px !important;
        padding: 14px !important;
        box-shadow: 0px 6px 18px rgba(0,0,0,0.65), 0px 0px 0px 1px {_color}33 !important;
        margin-bottom: 15px !important;
    }}
    """

st.markdown(
    f"""
    <style>
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    [data-testid="stHeader"] {{
        background: transparent !important;
    }}
    section.main div[data-testid="stVerticalBlock"] {{
        gap: 0.5rem;
    }}
    .stApp {{
        background: linear-gradient(135deg, #0f380f 0%, #1e561e 50%, #0f380f 100%);
        color: #ffffff;
    }}
    [data-testid="stSidebar"] {{
        background-color: rgba(15, 40, 15, 0.98) !important;
        border-right: 2px solid #2ecc71 !important;
    }}
    div[data-testid="stVerticalBlock"] > div:has(div.sticky-header-marker):has([data-testid="stHorizontalBlock"]) {{
        position: sticky;
        top: 0.1rem;
        z-index: 999;
        background-color: rgba(15, 56, 15, 0.95);
        border: 1.5px solid #2ecc71;
        border-radius: 12px;
        padding: 8px 14px;
        box-shadow: 0px 4px 15px rgba(0,0,0,0.6);
        backdrop-filter: blur(5px);
    }}
    @media (max-width: 768px) {{
        div[data-testid="stVerticalBlock"] > div:has(div.sticky-header-marker):has([data-testid="stHorizontalBlock"]) {{
            position: static !important;
            top: auto !important;
            backdrop-filter: none !important;
        }}
    }}
    h1, h2, h3, h4, label {{
        color: #ffffff !important;
        font-family: 'Trebuchet MS', sans-serif;
        margin-top: 0 !important;
    }}
    h2 {{ margin-bottom: 0.3rem !important; }}
    h4 {{ margin-bottom: 0.1rem !important; }}
    .stButton > button {{
        background-color: #2d3748 !important;
        color: #ffffff !important;
        border: 1px solid #4a5568 !important;
        border-radius: 8px !important;
        font-weight: bold !important;
        box-shadow: 0px 2px 6px rgba(0, 0, 0, 0.4) !important;
    }}
    .stButton > button:hover {{
        background-color: #4a5568 !important;
        color: #2ecc71 !important;
        border-color: #2ecc71 !important;
    }}
    {_card_color_css}
    [class*="st-key-iconbtn__"] .stButton > button {{
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        font-size: 1.15rem !important;
        padding: 0px !important;
        min-height: 0px !important;
        height: auto !important;
        width: auto !important;
    }}
    [class*="st-key-iconbtn__"] .stButton > button:hover {{
        background: transparent !important;
        transform: scale(1.3);
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

SQUADRA_ABBR = {
    "Atalanta": "ATA", "Bologna": "BOL", "Cagliari": "CAG", "Como": "COM",
    "Fiorentina": "FIO", "Frosinone": "FRO", "Genoa": "GEN", "Inter": "INT",
    "Juventus": "JUV", "Lazio": "LAZ", "Lecce": "LEC", "Milan": "MIL",
    "Monza": "MON", "Napoli": "NAP", "Parma": "PAR", "Roma": "ROM",
    "Sassuolo": "SAS", "Torino": "TOR", "Udinese": "UDI", "Venezia": "VEN"
}

MAX_SLOTS = {"P": 3, "D": 8, "C": 8, "A": 6}


@st.cache_data
def load_data():
    master_file = "Quotazioni_Fantacalcio_Stagione_2026_27.xlsx"
    formazioni_file = "Probabili_Formazioni_Serie_A_Squadre.xlsx"
    
    if os.path.exists(master_file):
        listone_df = pd.read_excel(master_file, sheet_name="Tutti", skiprows=1)
        listone_df = listone_df[['R', 'RM', 'Nome', 'Squadra', 'Qt.A', 'FVM']].dropna(subset=['Nome'])
    else:
        listone_df = pd.DataFrame(columns=['R', 'RM', 'Nome', 'Squadra', 'Qt.A', 'FVM'])
        
    if os.path.exists(formazioni_file):
        formazioni_df = pd.read_excel(formazioni_file, skiprows=3)
    else:
        formazioni_df = pd.DataFrame()
        
    return listone_df, formazioni_df


listone_df, formazioni_df = load_data()
PLAYER_TO_ROLE = dict(zip(listone_df["Nome"], listone_df["R"]))


def save_asta_to_file():
    nome_asta = st.session_state.session_info["nome_asta"]
    data_to_save = {
        "session_info": st.session_state.session_info,
        "asta_state": st.session_state.asta_state,
        "preferiti": st.session_state.get("preferiti", []),
    }
    execute_query(
        supabase.table("aste").upsert(
            {
                "owner_username": st.session_state.username,
                "nome_asta": nome_asta,
                "stato_json": data_to_save,
                "updated_at": "now()",
            },
            on_conflict="owner_username,nome_asta",
        ),
        ttl=0,
    )
    return nome_asta


def list_aste_utente():
    result = execute_query(
        supabase.table("aste")
        .select("nome_asta, updated_at, stato_json")
        .eq("owner_username", st.session_state.username)
        .order("updated_at", desc=True),
        ttl=0,
    )
    rows = result.data or []
    for r in rows:
        r["modalita"] = (r.get("stato_json") or {}).get("asta_state", {}).get("modalita", "tutte")
    return rows


def load_asta_from_file(nome_asta):
    result = execute_query(
        supabase.table("aste")
        .select("stato_json")
        .eq("owner_username", st.session_state.username)
        .eq("nome_asta", nome_asta),
        ttl=0,
    )
    if not result.data:
        st.error("❌ Asta non trovata.")
        return False
    data = result.data[0]["stato_json"]
    st.session_state.session_info = data["session_info"]
    st.session_state.asta_state = data["asta_state"]
    st.session_state.preferiti = data.get("preferiti", [])
    st.session_state.app_mode = "in_asta"
    return True


@st.fragment
def render_mia_squadra_panel(nome_squadra):
    is_open = st.session_state.mia_rosa_open
    panel_width = 280

    st.markdown(
        f"""
        <style>
        [class*="st-key-mia_rosa_panel"] {{
            position: fixed !important;
            top: 3.6rem !important;
            right: {0 if is_open else -panel_width}px !important;
            width: {panel_width}px !important;
            height: calc(100vh - 4.4rem) !important;
            overflow-y: auto;
            background: rgba(15, 40, 15, 0.98) !important;
            border-left: 2px solid #2ecc71 !important;
            padding: 14px 12px !important;
            z-index: 10000 !important;
            box-shadow: -6px 0 18px rgba(0,0,0,0.45);
            transition: right 0.2s ease-in-out;
        }}
        [class*="st-key-mia_rosa_toggle"] {{
            position: fixed !important;
            top: 23vh !important;
            right: {panel_width if is_open else 0}px !important;
            transform: translateY(-50%) !important;
            z-index: 20000 !important;
            width: auto !important;
            transition: right 0.2s ease-in-out;
        }}
        [class*="st-key-mia_rosa_toggle"] .stButton > button {{
            width: 48px !important;
            min-width: 48px !important;
            height: 58px !important;
            padding: 8px 7px !important;
            color: #2ecc71 !important;
            background: #0f380f !important;
            border: 2px solid #2ecc71 !important;
            border-right: none !important;
            border-radius: 10px 0 0 10px !important;
            font-size: 1.15rem !important;
            font-weight: bold !important;
            box-shadow: -4px 4px 12px rgba(0,0,0,0.5) !important;
        }}
        .mia-rosa-title {{ font-size: 1.05rem; font-weight: 800; color: #ffffff; margin-bottom: 4px; }}
        .mia-rosa-credits {{ font-size: 0.85rem; font-weight: bold; color: #e2e8f0; border-bottom: 1px solid rgba(255,255,255,0.2); padding-bottom: 6px; margin-bottom: 8px; }}
        </style>
        """,
        unsafe_allow_html=True,
    )

    with st.container(key="mia_rosa_toggle"):
        if st.button("⭐ ›" if is_open else "⭐ ‹", key="btn_toggle_mia_rosa"):
            st.session_state.mia_rosa_open = not st.session_state.mia_rosa_open
            st.rerun(scope="fragment")
    
    if not is_open:
        return

    team_data = st.session_state.asta_state["squadre"][nome_squadra]

    with st.container(key="mia_rosa_panel"):
        st.markdown(f'<div class="mia-rosa-title">⭐ {nome_squadra}</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="mia-rosa-credits">Crediti: <span style="color:#2ecc71;">{team_data["crediti_residui"]}</span> / {team_data["budget_iniziale"]}</div>',
            unsafe_allow_html=True
        )

        role_names_panel = {"P": "Portieri", "D": "Difensori", "C": "Centrocampisti", "A": "Attaccanti"}
        players_by_role = {"P": [], "D": [], "C": [], "A": []}

        for p in team_data["rosa"]:
            r = p.get("Ruolo", PLAYER_TO_ROLE.get(p["Nome"], "C"))
            if r in players_by_role:
                players_by_role[r].append(p)

        if not team_data["rosa"]:
            st.markdown("<p style='font-size:0.85rem; color:#cbd5e1; font-style:italic;'>Rosa ancora vuota.</p>", unsafe_allow_html=True)
        else:
            for r_code in ["P", "D", "C", "A"]:
                r_list = players_by_role[r_code]
                max_s = MAX_SLOTS[r_code]
                role_html = f"<div class='role-header'>{role_names_panel[r_code]} ({len(r_list)}/{max_s})</div>"
                if r_list:
                    players_html = "<div class='player-list'>"
                    for p_item in r_list:
                        players_html += f"<div class='player-row'>• {p_item['Nome']} — {p_item['Prezzo']} cr</div>"
                    players_html += "</div>"
                    st.markdown(role_html + players_html, unsafe_allow_html=True)
                else:
                    st.markdown(role_html + "<div class='player-row' style='color:#94a3b8; font-style:italic;'>Nessuno</div>", unsafe_allow_html=True)


# Inizializzazione Session State
if "app_mode" not in st.session_state:
    st.session_state.app_mode = "menu"
if "mia_rosa_open" not in st.session_state:
    st.session_state.mia_rosa_open = True    
if "preferiti" not in st.session_state:
    st.session_state.preferiti = []
if "_reset_player_search" not in st.session_state:
    st.session_state._reset_player_search = False
if st.session_state._reset_player_search:
    st.session_state["player_search_select"] = None
    st.session_state["search_filter_text"] = ""
    st.session_state._reset_player_search = False
if "editing_team" not in st.session_state:
    st.session_state.editing_team = None
if "confirm_delete_team" not in st.session_state:
    st.session_state.confirm_delete_team = None
if "confirm_delete_player" not in st.session_state:
    st.session_state.confirm_delete_player = None


# Dialog Modali
@st.dialog("⚠️ Conferma Eliminazione Squadra")
def dialog_delete_team(target_team):
    st.write(f"Sei sicuro di voler eliminare definitivamente la squadra **'{target_team}'**?")
    st.warning("⚠️ Tutti i suoi calciatori torneranno liberi nel listone.")
    col1, col2 = st.columns(2)
    if col1.button("✅ Sì, Elimina", key="dlg_del_team_yes", use_container_width=True):
        for p_name, p_info in list(st.session_state.asta_state["giocatori_acquistati"].items()):
            if p_info["squadra_asta"] == target_team:
                del st.session_state.asta_state["giocatori_acquistati"][p_name]
        if target_team in st.session_state.asta_state["squadre"]:
            del st.session_state.asta_state["squadre"][target_team]
        st.session_state.confirm_delete_team = None
        st.session_state.editing_team = None
        save_asta_to_file()
        st.rerun()
    if col2.button("❌ Annulla", key="dlg_del_team_no", use_container_width=True):
        st.session_state.confirm_delete_team = None
        st.session_state.editing_team = None
        st.rerun()


@st.dialog("⚠️ Conferma Svincolo Calciatore")
def dialog_delete_player(info):
    st.write(f"Rimuovere **{info['nome']}** dalla rosa di **{info['team']}**?")
    st.info(f"💰 Verranno rimborsati **{info['prezzo']} crediti** a **{info['team']}**.")
    col1, col2 = st.columns(2)
    if col1.button("✅ Sì, Rimuovi", key="dlg_del_p_yes", use_container_width=True):
        t_data = st.session_state.asta_state["squadre"].get(info["team"])
        if t_data:
            t_data["crediti_residui"] += info["prezzo"]
            t_data["rosa"] = [p for p in t_data["rosa"] if p["Nome"] != info["nome"]]
        if info["nome"] in st.session_state.asta_state["giocatori_acquistati"]:
            del st.session_state.asta_state["giocatori_acquistati"][info["nome"]]
        st.session_state.confirm_delete_player = None
        st.session_state.editing_team = None
        save_asta_to_file()
        st.rerun()
    if col2.button("❌ Annulla", key="dlg_del_p_no", use_container_width=True):
        st.session_state.confirm_delete_player = None
        st.session_state.editing_team = None
        st.rerun()


# ==========================================
# 🏠 MENU PRINCIPALE
# ==========================================
if st.session_state.app_mode == "menu":
    col_menu_title, col_menu_logout = st.columns([5, 1])
    with col_menu_title:
        st.markdown("<h1 style='margin-top: 0.5rem;'>⚽ FANTACALCIO ASTA MANAGER 2026/27</h1>", unsafe_allow_html=True)
    with col_menu_logout:
        st.write("")
        if st.button("🚪 Logout", key="logout_menu", use_container_width=True):
            do_logout()
    st.caption(f"👋 Bentornato, **{user_name}**")
    st.divider()
    
    col_m1, col_m2 = st.columns([1, 1])

    with col_m1:
        st.subheader("🆕 Nuova Asta")
        nome_nuova_asta = st.text_input("Nome Asta / Lega", placeholder="Es. Lega Amici 2026")

        modalita_asta = st.radio(
            "Modalità Asta",
            options=["tutte", "mia_squadra"],
            format_func=lambda m: "👥 Tutte le squadre" if m == "tutte" else "⭐ Solo la mia squadra",
            horizontal=True,
        )

        if modalita_asta == "tutte":
            num_squadre = st.number_input("Numero di Squadre Partecipanti", min_value=2, max_value=20, value=8)
            budget_default = st.number_input("Budget Iniziale Crediti", min_value=100, value=500)
        else:
            nome_mia_squadra_input = st.text_input("Nome della tua Squadra", value="La Mia Squadra")
            budget_default = st.number_input("Budget Iniziale Crediti", min_value=100, value=500)

        if st.button("🚀 Avvia Nuova Asta", use_container_width=True):
            if nome_nuova_asta.strip():
                st.session_state.session_info = {"nome_asta": nome_nuova_asta.strip()}

                if modalita_asta == "tutte":
                    squadre_auto = {}
                    for i in range(1, num_squadre + 1):
                        squadre_auto[f"Squadra {i}"] = {
                            "budget_iniziale": budget_default,
                            "crediti_residui": budget_default,
                            "rosa": []
                        }
                    st.session_state.asta_state = {
                        "modalita": "tutte",
                        "squadre": squadre_auto,
                        "giocatori_acquistati": {},
                        "current_page": 0
                    }
                else:
                    nome_mia = nome_mia_squadra_input.strip() or "La Mia Squadra"
                    st.session_state.asta_state = {
                        "modalita": "mia_squadra",
                        "mia_squadra_nome": nome_mia,
                        "squadre": {
                            nome_mia: {
                                "budget_iniziale": budget_default,
                                "crediti_residui": budget_default,
                                "rosa": []
                            }
                        },
                        "giocatori_acquistati": {},
                        "current_page": 0
                    }

                st.session_state.preferiti = []
                st.session_state.app_mode = "in_asta"
                st.rerun()
            else:
                st.error("❌ Inserisci un nome per l'asta.")

    with col_m2:
        st.subheader("📂 Carica Asta")
        try:
            saved_aste = list_aste_utente()
        except Exception as e:
            saved_aste = []
            st.error(f"⚠️ Errore nel recupero delle aste salvate: {e}")

        if saved_aste:
            def _label_asta(row):
                tag = "⭐ Mia Squadra" if row.get("modalita") == "mia_squadra" else "👥 Tutte le Squadre"
                return f"{row['nome_asta']}  —  {tag}"

            label_to_nome = {_label_asta(row): row["nome_asta"] for row in saved_aste}
            selected_label = st.selectbox("Seleziona Asta Salvata", options=list(label_to_nome.keys()))
            if st.button("📥 Carica Asta Selezionata", use_container_width=True):
                if load_asta_from_file(label_to_nome[selected_label]):
                    st.rerun()
        else:
            st.info("Nessuna asta salvata trovata.")


# ==========================================
# ⚽ APPLICAZIONE ASTA
# ==========================================
elif st.session_state.app_mode == "in_asta":

    # Script JS iniettato ESCLUSIVAMENTE quando si è in modalità asta
    components.html(
        """
        <script>
        (function() {
            const doc = window.parent.document;

            const COMMON_STYLE = {
                width: '48px',
                height: '58px',
                boxSizing: 'border-box',
                top: '23vh',
                zIndex: '999999',
                background: '#0f380f',
                border: '2px solid #2ecc71',
                boxShadow: '4px 4px 12px rgba(0,0,0,0.5)',
            };

            function applyCommon(el, extra) {
                el.style.setProperty('box-sizing', 'border-box', 'important');
                el.style.setProperty('width', COMMON_STYLE.width, 'important');
                el.style.setProperty('height', COMMON_STYLE.height, 'important');
                el.style.setProperty('top', COMMON_STYLE.top, 'important');
                el.style.setProperty('z-index', COMMON_STYLE.zIndex, 'important');
                el.style.setProperty('background', COMMON_STYLE.background, 'important');
                el.style.setProperty('border', COMMON_STYLE.border, 'important');
                el.style.setProperty('box-shadow', COMMON_STYLE.boxShadow, 'important');
                el.style.setProperty('margin', '0', 'important');
                el.style.setProperty('padding', '0', 'important');
                el.style.setProperty('display', 'flex', 'important');
                el.style.setProperty('align-items', 'center', 'important');
                el.style.setProperty('justify-content', 'center', 'important');
                el.style.setProperty('cursor', 'pointer', 'important');
                el.style.setProperty('overflow', 'hidden', 'important');
                Object.assign(el.style, extra || {});
            }

            function styleSidebarToggle() {
                const icons = doc.querySelectorAll('span[data-testid="stIconMaterial"]');

                icons.forEach(span => {
                    const txt = span.textContent.trim();
                    const btn = span.closest('button');
                    if (!btn) return;

                    let lens = btn.querySelector('.custom-lens-icon');
                    if (!lens) {
                        lens = doc.createElement('span');
                        lens.className = 'custom-lens-icon';
                        lens.style.fontSize = '1.15rem';
                        lens.style.fontWeight = 'bold';
                        lens.style.color = '#2ecc71';
                        lens.style.pointerEvents = 'none';
                        lens.style.whiteSpace = 'nowrap';
                        btn.appendChild(lens);
                    }

                    if (txt === 'keyboard_double_arrow_right') {
                        btn.style.setProperty('position', 'fixed', 'important');
                        btn.style.setProperty('left', '0px', 'important');
                        btn.style.setProperty('right', 'auto', 'important');
                        btn.style.setProperty('border-left', 'none', 'important');
                        btn.style.setProperty('border-radius', '0 10px 10px 0', 'important');
                        applyCommon(btn);

                        span.style.setProperty('display', 'none', 'important');
                        lens.textContent = '🔍 ›';
                    }

                    if (txt === 'keyboard_double_arrow_left') {
                        const sidebar = doc.querySelector('section[data-testid="stSidebar"]');
                        const sidebarWidth = sidebar ? sidebar.getBoundingClientRect().width : 336;

                        btn.style.setProperty('position', 'fixed', 'important');
                        btn.style.setProperty('left', sidebarWidth + 'px', 'important');
                        btn.style.setProperty('right', 'auto', 'important');
                        btn.style.setProperty('border-left', 'none', 'important');
                        btn.style.setProperty('border-radius', '0 10px 10px 0', 'important');
                        applyCommon(btn);

                        span.style.setProperty('display', 'none', 'important');
                        lens.textContent = '🔍 ‹';
                    }
                });
            }

            const observer = new MutationObserver(styleSidebarToggle);
            observer.observe(doc.body, { childList: true, subtree: true, attributes: true });
            styleSidebarToggle();
        })();
        </script>
        """,
        height=0,
    )

    with st.sidebar:
        st.markdown(
            f"""
            <div class="sidebar-user">
                <div class="sidebar-avatar">👤</div>
                <div>
                    <div class="sidebar-user-name">{user_name}</div>
                    <div class="sidebar-user-sub">Bentornato</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("🚪 Logout", key="logout_sidebar", use_container_width=True):
            do_logout()
        st.divider()

        n_pref = len(st.session_state.preferiti)
        st.markdown(
            f"""
            <div class="pref-header">
                <span class="pref-header-title">⭐ Preferiti</span>
                <span class="pref-header-count">{n_pref}</span>
            </div>
            <div class="pref-caption">I tuoi calciatori sotto osservazione</div>
            """,
            unsafe_allow_html=True,
        )

        if st.session_state.preferiti:
            pref_df = listone_df[listone_df["Nome"].isin(st.session_state.preferiti)]
            ROLE_LABEL = {"P": "P", "D": "D", "C": "C", "A": "A"}

            for idx, p_row in pref_df.iterrows():
                p_name = p_row["Nome"]
                p_role = p_row["R"]
                is_sold = p_name in st.session_state.asta_state["giocatori_acquistati"]

                with st.container(key=f"prefcard__{p_name}"):
                    c_badge, c_info, c_del = st.columns([1, 4.2, 0.9])
                    badge_class = "pref-role-sold" if is_sold else f"pref-role-{p_role}"
                    c_badge.markdown(
                        f'<div class="pref-role-badge {badge_class}">{ROLE_LABEL.get(p_role, p_role)}</div>',
                        unsafe_allow_html=True,
                    )
                    sold_wrap_open = '<div class="pref-sold">' if is_sold else '<div>'
                    c_info.markdown(
                        f"{sold_wrap_open}"
                        f'<div class="pref-name-line">{p_name}</div>'
                        f'<div class="pref-team-line">{p_row["Squadra"]}</div>'
                        f"</div>",
                        unsafe_allow_html=True,
                    )
                    with c_del:
                        with st.container(key=f"iconbtn__delpref__{p_name}"):
                            if st.button("✕", key=f"del_pref_{p_name}"):
                                st.session_state.preferiti.remove(p_name)
                                st.rerun()
        else:
            st.markdown(
                '<div class="pref-empty-box">Nessun giocatore nei preferiti.<br>Aggiungili dal listone con ⭐</div>',
                unsafe_allow_html=True,
            )

    col_head1, col_head2, col_head3 = st.columns([3, 1, 1])

    with col_head1:
        _modalita_corrente = st.session_state.asta_state.get("modalita", "tutte")
        _modalita_label = "⭐ Mia Squadra" if _modalita_corrente == "mia_squadra" else "👥 Tutte le Squadre"
        st.markdown(
            f"## **{st.session_state.session_info['nome_asta']}**&nbsp;"
            f"<span style='font-size:0.72rem; font-weight:700; color:#2ecc71; "
            f"background:rgba(46,204,113,0.15); border:1px solid rgba(46,204,113,0.4); "
            f"border-radius:999px; padding:3px 10px; vertical-align:middle;'>{_modalita_label}</span>",
            unsafe_allow_html=True,
        )

    with col_head2:
        if st.button("💾 Salva Asta"):
            save_asta_to_file()
            st.success("Asta salvata!")

    with col_head3:
        if st.button("🚪 Menu"):
            save_asta_to_file()
            st.session_state.app_mode = "menu"
            st.rerun()

    # ==========================================
    # BARRA STICKY: NAVIGAZIONE + ASSEGNAZIONE
    # ==========================================
    modalita = st.session_state.asta_state.get("modalita", "tutte")
    mia_squadra_nome = st.session_state.asta_state.get("mia_squadra_nome")

    if modalita == "mia_squadra":
        render_mia_squadra_panel(mia_squadra_nome)
        PAGE_NAMES = ["Listone", "Formazioni"]
    else:
        PAGE_NAMES = ["Listone", "Formazioni", "Fantarose"]

    with st.container():
        st.markdown('<div class="sticky-header-marker" style="display:none;"></div>', unsafe_allow_html=True)

        col_nav_left, col_nav_title, col_nav_right = st.columns([1, 4, 1])

        with col_nav_left:
            if st.button("◀ Precedente", key="nav_prev", use_container_width=True):
                st.session_state.asta_state["current_page"] = (
                    st.session_state.asta_state["current_page"] - 1
                ) % len(PAGE_NAMES)
                st.rerun()

        with col_nav_title:
            st.markdown(
                f"<h4 style='text-align:center; margin:4px 0;'>"
                f"{PAGE_NAMES[st.session_state.asta_state['current_page']]}</h4>",
                unsafe_allow_html=True,
            )

        with col_nav_right:
            if st.button("Successivo ▶", key="nav_next", use_container_width=True):
                st.session_state.asta_state["current_page"] = (
                    st.session_state.asta_state["current_page"] + 1
                ) % len(PAGE_NAMES)
                st.rerun()

        st.markdown("<hr style='margin:8px 0; border-color:rgba(255,255,255,0.15);'>", unsafe_allow_html=True)

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
                index=None,
                placeholder="Digitare o selezionare un giocatore...",
                key="player_search_select"
            )
            if selected_display and selected_display in options_dict:
                st.session_state["search_filter_text"] = options_dict[selected_display]
            else:
                st.session_state["search_filter_text"] = ""

        with col_squadra:
            if modalita == "mia_squadra":
                assegna_a = st.selectbox(
                    "Assegna a",
                    options=["mia", "altri"],
                    format_func=lambda v: f"⭐ {mia_squadra_nome}" if v == "mia" else "🔒 Altra Squadra",
                )
            else:
                squadra_dest = st.selectbox("Assegna a Squadra", options=list(st.session_state.asta_state["squadre"].keys()))
        
        with col_prezzo:
            prezzo_acquisto = st.number_input("Prezzo (Cr)", min_value=1, value=1)

        is_valid_player = (selected_display is not None) and (selected_display in options_dict)
        with col_btn:
            st.write("")
            if st.button("➕ Assegna", disabled=not is_valid_player):
                if is_valid_player:
                    player_real_name = options_dict[selected_display]
                    player_role = PLAYER_TO_ROLE.get(player_real_name, "D")

                    if modalita == "mia_squadra":
                        if assegna_a == "mia":
                            team_rosa = st.session_state.asta_state["squadre"][mia_squadra_nome]["rosa"]
                            current_role_count = sum(1 for p in team_rosa if p.get("Ruolo") == player_role)
                            max_allowed = MAX_SLOTS.get(player_role, 8)

                            if current_role_count >= max_allowed:
                                st.error(f"❌ Limite raggiunto! Hai già {current_role_count}/{max_allowed} nel ruolo {player_role}.")
                            else:
                                st.session_state.asta_state["giocatori_acquistati"][player_real_name] = {
                                    "squadra_asta": mia_squadra_nome,
                                    "prezzo": prezzo_acquisto
                                }
                                st.session_state.asta_state["squadre"][mia_squadra_nome]["crediti_residui"] -= prezzo_acquisto
                                st.session_state.asta_state["squadre"][mia_squadra_nome]["rosa"].append({
                                    "Nome": player_real_name, "Prezzo": prezzo_acquisto, "Ruolo": player_role
                                })
                                st.session_state._reset_player_search = True
                                save_asta_to_file()
                                st.rerun()
                        else:
                            st.session_state.asta_state["giocatori_acquistati"][player_real_name] = {
                                "squadra_asta": "Altra Squadra",
                                "prezzo": prezzo_acquisto
                            }
                            st.session_state._reset_player_search = True
                            save_asta_to_file()
                            st.rerun()

                    else:
                        team_rosa = st.session_state.asta_state["squadre"][squadra_dest]["rosa"]
                        current_role_count = sum(1 for p in team_rosa if p.get("Ruolo") == player_role)
                        max_allowed = MAX_SLOTS.get(player_role, 8)

                        if current_role_count >= max_allowed:
                            st.error(f"❌ Limite raggiunto! {squadra_dest} ha già {current_role_count}/{max_allowed} nel ruolo {player_role}.")
                        else:
                            st.session_state.asta_state["giocatori_acquistati"][player_real_name] = {
                                "squadra_asta": squadra_dest,
                                "prezzo": prezzo_acquisto
                            }
                            st.session_state.asta_state["squadre"][squadra_dest]["crediti_residui"] -= prezzo_acquisto
                            st.session_state.asta_state["squadre"][squadra_dest]["rosa"].append({
                                "Nome": player_real_name, "Prezzo": prezzo_acquisto, "Ruolo": player_role
                            })
                            st.session_state._reset_player_search = True
                            save_asta_to_file()
                            st.rerun()
    st.divider()

    # ==========================================
    # SCHERMATA 1: LISTONE MASTER DATA
    # ==========================================
    if st.session_state.asta_state["current_page"] == 0:
        if "metric_filter" not in st.session_state:
            st.session_state.metric_filter = "Totale"

        st.markdown(
            """
            <div class="listone-hero">
                <h2>📋 Listone Completo Calciatori 2026/27</h2>
                <p>Clicca sulle schede in alto per filtrare rapidamente i calciatori o affina la ricerca per ruolo.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        totale_giocatori = len(listone_df)
        venduti = len(st.session_state.asta_state["giocatori_acquistati"])
        liberi = totale_giocatori - venduti
        preferiti_count = len(st.session_state.preferiti)

        stat_cols = st.columns(4)
        stats = [
            ("Totale", "👥 Totale", totale_giocatori),
            ("Liberi", "✅ Liberi", liberi),
            ("Venduti", "❌ Venduti", venduti),
            ("Preferiti", "⭐ Preferiti", preferiti_count),
        ]

        for col, (filter_key, label, value) in zip(stat_cols, stats):
            with col:
                with st.container(key=f"metric_btn_{filter_key}"):
                    if st.button(f"{label}\n{value}", key=f"btn_stat_{filter_key}", use_container_width=True):
                        st.session_state.metric_filter = filter_key
                        st.rerun()

        st.write("")

        ROLE_LABELS = {
            "Tutti": "Tutti",
            "P": "🟨 Portieri",
            "D": "🟩 Difensori",
            "C": "🟦 Centrocampisti",
            "A": "🟥 Attaccanti",
        }

        col_filter, col_sort, col_order = st.columns([3, 1.3, 1])

        with col_filter:
            ruolo_filter = st.segmented_control(
                "Filtra per Ruolo:",
                options=list(ROLE_LABELS.keys()),
                format_func=lambda r: ROLE_LABELS[r],
                default="Tutti",
            )
            if ruolo_filter is None:
                ruolo_filter = "Tutti"

        with col_sort:
            sort_by = st.selectbox("Ordina per", options=["Nome", "Qt.A", "FVM"], index=2)

        with col_order:
            sort_desc = st.toggle("Decrescente", value=True)

        df_display = listone_df.copy()
        m_filter = st.session_state.metric_filter

        if m_filter == "Liberi":
            df_display = df_display[~df_display["Nome"].isin(st.session_state.asta_state["giocatori_acquistati"].keys())]
        elif m_filter == "Venduti":
            df_display = df_display[df_display["Nome"].isin(st.session_state.asta_state["giocatori_acquistati"].keys())]
        elif m_filter == "Preferiti":
            df_display = df_display[df_display["Nome"].isin(st.session_state.preferiti)]

        if ruolo_filter != "Tutti":
            df_display = df_display[df_display["R"] == ruolo_filter]

        search_term = st.session_state.get("search_filter_text", "")
        if search_term:
            df_display = df_display[df_display["Nome"] == search_term]

        df_display = df_display.sort_values(by=sort_by, ascending=not sort_desc)

        ROLE_BADGE = {"P": "🟨 P", "D": "🟩 D", "C": "🟦 C", "A": "🟥 A"}
        df_display["Ruolo"] = df_display["R"].map(ROLE_BADGE).fillna(df_display["R"])
        df_display["Preferito"] = df_display["Nome"].apply(lambda x: x in st.session_state.preferiti)
        df_display["Stato"] = df_display["Nome"].apply(
            lambda x: f"🔴 {st.session_state.asta_state['giocatori_acquistati'][x]['squadra_asta']}"
            if x in st.session_state.asta_state["giocatori_acquistati"] else "🟢 Libero"
        )

        if df_display.empty:
            st.info(f"Nessun calciatore trovato per la sezione **{m_filter}** con i filtri selezionati.")
        else:
            fvm_max = int(listone_df["FVM"].max()) if not listone_df.empty and listone_df["FVM"].notna().any() else 100

            edited_df = st.data_editor(
                df_display[["Preferito", "Nome", "Ruolo", "Squadra", "Qt.A", "FVM", "Stato"]],
                use_container_width=True,
                height=550,
                hide_index=True,
                column_config={
                    "Preferito": st.column_config.CheckboxColumn(
                        "⭐", help="Spunta per aggiungere o rimuovere dai preferiti", default=False, width="small"
                    ),
                    "Nome": st.column_config.TextColumn("Giocatore", width="medium"),
                    "Ruolo": st.column_config.TextColumn("R", width="small"),
                    "Squadra": st.column_config.TextColumn("Squadra"),
                    "Qt.A": st.column_config.NumberColumn("Quot. Asta", format="%d"),
                    "FVM": st.column_config.ProgressColumn(
                        "FVM", format="%d", min_value=0, max_value=fvm_max
                    ),
                    "Stato": st.column_config.TextColumn("Stato", width="medium"),
                },
                disabled=["Nome", "Ruolo", "Squadra", "Qt.A", "FVM", "Stato"],
                key=f"listone_editor_{m_filter}_{ruolo_filter}_{sort_by}_{sort_desc}",
            )

            current_favs = set(st.session_state.preferiti)
            changed = False
            for _, row in edited_df.iterrows():
                p_name = row["Nome"]
                is_fav = row["Preferito"]
                if is_fav and p_name not in current_favs:
                    st.session_state.preferiti.append(p_name)
                    changed = True
                elif not is_fav and p_name in current_favs:
                    st.session_state.preferiti.remove(p_name)
                    changed = True
            if changed:
                st.rerun()

    # ==========================================
    # SCHERMATA 2: PROBABILI FORMAZIONI
    # ==========================================
    elif st.session_state.asta_state["current_page"] == 1:
        st.header("🏟️ Probabili Formazioni Campionato Serie A")

        @st.fragment
        def render_team_pitch_fragment(row):
            st.subheader(row["Squadra"])
            import re
            players = [re.sub(r'\(.*?\)', '', p).replace("•", "").strip() for p in str(row["Titolari (con %)"]).split('\n') if p.strip()]

            ballottaggi_map = {}
            raw_ball = str(row.get("Ballottaggi principali", ""))
            if raw_ball and raw_ball.lower() != "nan":
                lines = [b.strip() for b in re.split(r'[\n;]+', raw_ball) if b.strip()]
                for line in lines:
                    match = re.search(r'(.+?)[-\/](.+)', line)
                    if match:
                        part1 = match.group(1).strip()
                        part2 = match.group(2).strip()

                        pct1_m = re.search(r'(\d+)%?', part1)
                        pct2_m = re.search(r'(\d+)%?', part2)

                        pct1 = int(pct1_m.group(1)) if pct1_m else 50
                        pct2 = int(pct2_m.group(1)) if pct2_m else (100 - pct1 if pct1 <= 100 else 50)

                        name1 = re.sub(r'\(.*?\)', '', re.sub(r'\d+%?', '', part1)).strip(' -/.•')
                        name2 = re.sub(r'\(.*?\)', '', re.sub(r'\d+%?', '', part2)).strip(' -/.•')

                        matched_starter = None
                        for pl in players:
                            if pl.lower() in name1.lower() or name1.lower() in pl.lower():
                                matched_starter = pl
                                break

                        if matched_starter and matched_starter not in ballottaggi_map:
                            ballottaggi_map[matched_starter] = {
                                "sub": name2,
                                "pct1": pct1,
                                "pct2": pct2
                            }

            svg_defs = []
            role_colors = {'P': '#f1c40f', 'D': '#2ecc71', 'C': '#3498db', 'A': '#e74c3c'}

            def get_player_color(p_name, default_role):
                clean_p_name = p_name.strip()
                acquistati = st.session_state.asta_state["giocatori_acquistati"]
                
                if clean_p_name in acquistati:
                    return '#7f8c8d'
                
                for acq_p in acquistati:
                    if clean_p_name.lower() in acq_p.lower() or acq_p.lower() in clean_p_name.lower():
                        return '#7f8c8d'
                
                p_role = PLAYER_TO_ROLE.get(clean_p_name, default_role)
                return role_colors.get(p_role, '#3498db')

            svg_html = (
                '<div style="text-align:center;"><svg width="100%" height="430" viewBox="0 0 100 135" preserveAspectRatio="xMidYMid meet" style="background:#1e7145; border-radius:8px;">'
                '<rect x="0" y="0" width="100" height="135" fill="#1e7145" stroke="#f1c40f" stroke-width="1.0"/>'
                '<line x1="0" y1="67.5" x2="100" y2="67.5" stroke="#f1c40f" stroke-width="1"/>'
                '<circle cx="50" cy="67.5" r="14" stroke="#f1c40f" stroke-width="1" fill="none"/>'
                '<rect x="18" y="0" width="64" height="28" stroke="#f1c40f" stroke-width="1" fill="none"/>'
                '<rect x="34" y="0" width="32" height="10" stroke="#f1c40f" stroke-width="1" fill="none"/>'
                '<path d="M 38 28 A 12 12 0 0 0 62 28" stroke="#f1c40f" stroke-width="1" fill="none"/>'
                '<rect x="18" y="107" width="64" height="28" stroke="#f1c40f" stroke-width="1" fill="none"/>'
                '<rect x="34" y="125" width="32" height="10" stroke="#f1c40f" stroke-width="1" fill="none"/>'
                '<path d="M 38 107 A 12 12 0 0 1 62 107" stroke="#f1c40f" stroke-width="1" fill="none"/>'
            )

            if players:
                def build_player_svg(p_name, x, y, default_role, node_idx):
                    nonlocal svg_defs
                    p_pref = "⭐" if p_name in st.session_state.preferiti else ""
                    text_style = 'font-size="4.2" font-weight="bold" text-anchor="middle" fill="white" stroke="black" stroke-width="0.4" paint-order="stroke fill"'

                    if p_name in ballottaggi_map:
                        ball_info = ballottaggi_map[p_name]
                        sub_name = ball_info["sub"]
                        pct1 = ball_info["pct1"]

                        c_fill1 = get_player_color(p_name, default_role)
                        c_fill2 = get_player_color(sub_name, default_role)

                        sub_pref = "⭐" if sub_name in st.session_state.preferiti else ""
                        clean_team = re.sub(r'[^a-zA-Z0-9]', '', str(row['Squadra']))
                        grad_id = f"ballgrad_{clean_team}_{node_idx}"
                        
                        svg_defs.append(
                            f'<linearGradient id="{grad_id}" x1="0%" y1="0%" x2="100%" y2="100%">'
                            f'<stop offset="{pct1}%" stop-color="{c_fill1}"/>'
                            f'<stop offset="{pct1}%" stop-color="black"/>'
                            f'<stop offset="{pct1 + 1.5}%" stop-color="black"/>'
                            f'<stop offset="{pct1 + 1.5}%" stop-color="{c_fill2}"/>'
                            f'</linearGradient>'
                        )

                        node_html = f'<circle cx="{x}" cy="{y}" r="6.5" fill="url(#{grad_id})" stroke="black" stroke-width="1.0"/>'
                        text1 = f'<text x="{x}" y="{y+8.0}" {text_style}>{p_name[:12]} {p_pref}</text>'
                        text2 = f'<text x="{x}" y="{y+12.5}" {text_style}>/{sub_name[:12]} {sub_pref}</text>'
                        return node_html + text1 + text2
                    else:
                        c_fill = get_player_color(p_name, default_role)
                        node_html = f'<circle cx="{x}" cy="{y}" r="6.5" fill="{c_fill}" stroke="black" stroke-width="1.0"/>'
                        text_html = f'<text x="{x}" y="{y+8.5}" {text_style}>{p_name[:12]} {p_pref}</text>'
                        return node_html + text_html

                portiere = players[0]
                movimento = players[1:]
                pitch_elements = [build_player_svg(portiere, 50, 8, 'P', 0)]

                lines_schema = [int(n) for n in str(row["Modulo"]).split('-') if n.isdigit()]
                y_levels = [35, 70, 105] if len(lines_schema) == 3 else [30, 60, 90, 118]
                line_roles = ['D', 'C', 'A'] if len(lines_schema) == 3 else ['D', 'C', 'C', 'A']

                idx_p = 0
                node_counter = 1
                for line_idx, count in enumerate(lines_schema):
                    y = y_levels[line_idx] if line_idx < len(y_levels) else 70
                    x_coords = [(100 * (i + 1) / (count + 1)) for i in range(count)]
                    r_code = line_roles[line_idx] if line_idx < len(line_roles) else 'C'

                    for x in x_coords:
                        if idx_p < len(movimento):
                            p_name = movimento[idx_p]
                            pitch_elements.append(build_player_svg(p_name, x, y, r_code, node_counter))
                            idx_p += 1
                            node_counter += 1

                defs_html = "<defs>" + "".join(svg_defs) + "</defs>" if svg_defs else ""
                svg_html += defs_html + "".join(pitch_elements)

            svg_html += "</svg></div>"
            st.markdown(svg_html, unsafe_allow_html=True)

            with st.expander("🔄 Dettagli Ballottaggi & Panchina"):
                st.write("**Ballottaggi:**", row["Ballottaggi principali"])
                st.write("**Panchina:**", row["Panchina principale"])
                st.write("**Indisponibili:**", row["Indisponibili / Squalificati"])

        if not formazioni_df.empty and "Squadra" in formazioni_df.columns:
            for i in range(0, len(formazioni_df), 4):
                cols = st.columns(4)
                for col_idx, (_, row) in enumerate(formazioni_df.iloc[i:i+4].iterrows()):
                    with cols[col_idx]:
                        render_team_pitch_fragment(row)

    # ==========================================
    # SCHERMATA 3: FANTAROSE
    # ==========================================
    elif st.session_state.asta_state["current_page"] == 2:
        col_title3, col_export3 = st.columns([5, 1])
        with col_title3:
            st.header("Gestione Partecipanti Asta & Crediti")
        with col_export3:
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
            export_df = pd.DataFrame(all_export_rows) if all_export_rows else pd.DataFrame(
                columns=["Squadra Fantacalcio", "Giocatore", "Ruolo", "Prezzo Acquisto", "Crediti Residui"]
            )
            csv_data = export_df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
            st.write("")
            st.download_button(
                label="📥 CSV",
                data=csv_data,
                file_name=f"rose_asta_{st.session_state.session_info['nome_asta']}.csv",
                mime="text/csv",
                use_container_width=True,
            )

        if st.session_state.confirm_delete_team:
            dialog_delete_team(st.session_state.confirm_delete_team)

        if st.session_state.confirm_delete_player:
            dialog_delete_player(st.session_state.confirm_delete_player)

        st.divider()

        role_names = {"P": "Portieri", "D": "Difensori", "C": "Centrocampisti", "A": "Attaccanti"}
        teams_items = list(st.session_state.asta_state["squadre"].items())

        for i in range(0, len(teams_items), 4):
            cols = st.columns(4)
            for col_idx, (team, data) in enumerate(teams_items[i:i+4]):
                with cols[col_idx]:
                    color_idx = (i + col_idx) % len(CARD_BORDER_COLORS)
                    b_color = CARD_BORDER_COLORS[color_idx]

                    with st.container(key=f"teamcard__c{color_idx}__{team}", border=True):
                        c_title, c_edit, c_del = st.columns([5, 1, 1])
                        c_title.markdown(
                            f"<div style='color:{b_color}; font-size: 1.1rem; font-weight: bold; padding-top: 4px;'> {team}</div>",
                            unsafe_allow_html=True,
                        )

                        with c_edit:
                            with st.container(key=f"iconbtn__edit__{team}"):
                                if st.button("✏️", key=f"edit_btn_{team}"):
                                    st.session_state.editing_team = team if st.session_state.editing_team != team else None
                                    st.rerun()

                        with c_del:
                            with st.container(key=f"iconbtn__del__{team}"):
                                if st.button("❌", key=f"del_btn_{team}"):
                                    st.session_state.confirm_delete_team = team
                                    st.rerun()

                        if st.session_state.editing_team == team:
                            st.caption("✏️ **Rinomina Squadra:**")
                            renamed_val = st.text_input("Nuovo nome:", value=team, key=f"inp_rename_{team}", label_visibility="collapsed")
                            if st.button("Salva Nome", key=f"save_rename_{team}", use_container_width=True):
                                if renamed_val.strip() and renamed_val.strip() != team and renamed_val.strip() not in st.session_state.asta_state["squadre"]:
                                    new_name = renamed_val.strip()
                                    new_squadre = {}
                                    for k, v in st.session_state.asta_state["squadre"].items():
                                        if k == team:
                                            new_squadre[new_name] = v
                                        else:
                                            new_squadre[k] = v

                                    st.session_state.asta_state["squadre"] = new_squadre

                                    for p_info in st.session_state.asta_state["giocatori_acquistati"].values():
                                        if p_info["squadra_asta"] == team:
                                            p_info["squadra_asta"] = new_name

                                    st.session_state.editing_team = None
                                    save_asta_to_file()
                                    st.rerun()
                                elif renamed_val.strip() == team:
                                    st.session_state.editing_team = None
                                    st.rerun()

                            if data["rosa"]:
                                st.caption("🗑️ **Svincola / Elimina Calciatore:**")
                                player_opts = ["-- Seleziona calciatore --"] + [
                                    f"{p['Nome']} ({p.get('Ruolo', PLAYER_TO_ROLE.get(p['Nome'], ''))}) - {p['Prezzo']} cr"
                                    for p in data["rosa"]
                                ]
                                sel_p_str = st.selectbox(
                                    "Calciatore da rimuovere:",
                                    options=player_opts,
                                    key=f"sel_rm_{team}",
                                    label_visibility="collapsed"
                                )
                                if sel_p_str and sel_p_str != "-- Seleziona calciatore --":
                                    p_name_only = sel_p_str.split(" (")[0]
                                    target_p = next((p for p in data["rosa"] if p["Nome"] == p_name_only), None)
                                    if target_p:
                                        if st.button(f"❌ Rimuovi {p_name_only} (+{target_p['Prezzo']} cr)", key=f"btn_del_p_{team}", use_container_width=True):
                                            st.session_state.confirm_delete_player = {
                                                "team": team,
                                                "nome": target_p["Nome"],
                                                "prezzo": target_p["Prezzo"]
                                            }
                                            st.rerun()
                            st.markdown("<hr style='margin: 8px 0; border: none; border-top: 1px solid rgba(255,255,255,0.15);'>", unsafe_allow_html=True)

                        players_by_role = {"P": [], "D": [], "C": [], "A": []}
                        for p in data["rosa"]:
                            r = p.get("Ruolo", PLAYER_TO_ROLE.get(p["Nome"], "C"))
                            if r in players_by_role:
                                players_by_role[r].append(p)

                        st.markdown(
                            f"<p class='credits-info'>Crediti: "
                            f"<span style='color:#2ecc71;'>{data['crediti_residui']}</span> / {data['budget_iniziale']}</p>",
                            unsafe_allow_html=True,
                        )

                        total_p_count = sum(len(plist) for plist in players_by_role.values())

                        if total_p_count == 0:
                            st.markdown(
                                "<p style='font-size:0.85rem; color:#cbd5e1; font-style:italic;'>Rosa ancora vuota.</p>",
                                unsafe_allow_html=True,
                            )
                        else:
                            for r_code in ["P", "D", "C", "A"]:
                                r_list = players_by_role[r_code]
                                max_s = MAX_SLOTS[r_code]
                                role_html = f"<div class='role-header'>{role_names[r_code]} ({len(r_list)}/{max_s})</div>"
                                if r_list:
                                    players_html = "<div class='player-list'>"
                                    for p_item in r_list:
                                        players_html += f"<div class='player-row'>• {p_item['Nome']}  —  {p_item['Prezzo']} cr</div>"
                                    players_html += "</div>"
                                    st.markdown(role_html + players_html, unsafe_allow_html=True)
                                else:
                                    st.markdown(
                                        role_html + "<div class='player-row' style='color:#94a3b8; font-style:italic;'>Nessuno</div>",
                                        unsafe_allow_html=True,
                                    )

        st.divider()
        with st.expander("➕ Aggiungi Nuova Squadra"):
            col_n, col_b, col_a = st.columns([3, 2, 1])
            new_team_name = col_n.text_input("Nome Squadra", key="new_team_name_input", label_visibility="collapsed", placeholder="Nome Squadra")
            new_team_budget = col_b.number_input("Budget", min_value=1, value=500, key="new_team_budget_input", label_visibility="collapsed")
            with col_a:
                if st.button("Crea", key="create_team_btn", use_container_width=True):
                    if new_team_name and new_team_name not in st.session_state.asta_state["squadre"]:
                        st.session_state.asta_state["squadre"][new_team_name] = {
                            "budget_iniziale": new_team_budget,
                            "crediti_residui": new_team_budget,
                            "rosa": []
                        }
                        save_asta_to_file()
                        st.rerun()