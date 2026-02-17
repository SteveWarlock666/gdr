import streamlit as st
from groq import Groq
from streamlit_gsheets import GSheetsConnection
from streamlit_autorefresh import st_autorefresh
import pandas as pd
from datetime import datetime, timedelta
import re

st.set_page_config(page_title='Apocrypha Master', layout='wide')

# --- CSS COMPLETO ---
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; }
    div[data-testid="stSidebarUserContent"] { padding-top: 1rem; }
    .compact-row { display: flex; align-items: center; gap: 10px; margin-bottom: 4px; }
    .compact-label { font-size: 12px !important; min-width: 75px; margin: 0 !important; white-space: nowrap; }
    .stProgress { height: 6px !important; flex-grow: 1; }
    #hp-bar .stProgress div[role="progressbar"] > div { background-color: #ff4b4b !important; }
    div[data-testid="stVerticalBlock"] > div { padding-bottom: 0px !important; margin-bottom: 0px !important; }
    </style>
""", unsafe_allow_html=True)

if 'GROQ_API_KEY' not in st.secrets:
    st.error("Manca la chiave!")
    st.stop()

client = Groq(api_key=st.secrets['GROQ_API_KEY'])
conn = st.connection('gsheets', type=GSheetsConnection)

# REFRESH AUTOMATICO 60 SECONDI
st_autorefresh(interval=60000, key='global_sync')

if 'auth' not in st.session_state:
    st.session_state.auth = False

# --- LOGIN ---
if not st.session_state.auth:
    st.title('🌑 APOCRYPHA')
    u = st.text_input('Username')
    p = st.text_input('Password', type='password')
    if st.button('Entra'):
        if p == 'apocrypha2026' and u:
            st.session_state.auth = True
            st.session_state.user = u.strip()
            st.rerun()
    st.stop()

# --- CARICAMENTO DATI ---
try:
    df_p = conn.read(worksheet='personaggi', ttl=0)
    df_m = conn.read(worksheet='messaggi', ttl=0).fillna('')
    df_a = conn.read(worksheet='abilita', ttl=0).fillna('')
    df_n = conn.read(worksheet='nemici', ttl=0).fillna(0)
    
    # Pulizia colonne
    for c in ['img', 'hp', 'posizione', 'ultimo_visto']:
        if c not in df_p.columns: df_p[c] = ''
    df_p['posizione'] = df_p['posizione'].astype(str).replace(['0.0', '0', 'nan'], 'Strada per Gauvadon')
    df_p = df_p.fillna('')

except Exception as e:
    st.warning("Sincronizzazione...")
    st.stop()

# --- DEFINIZIONE GIOCATORE ---
u_df = df_p[df_p['username'].astype(str) == str(st.session_state.user)]

if u_df.empty:
    st.title("🛡️ Crea il tuo Eroe")
    with st.form("creazione_pg"):
        n_nuovo = st.text_input("Nome Eroe")
        r_nuova = st.selectbox("Razza", ["Primaris", "Inferis", "Narun", "Minotauro"])
        c_nuova = st.selectbox("Classe", ["Orrenai", "Elementalista", "Armagister", "Chierico"])
        img_nuova = st.text_input("URL Avatar (.jpg/.png)")
        if st.form_submit_button("Inizia"):
            nuovo = pd.DataFrame([{"username": st.session_state.user, "nome_pg": n_nuovo, "razza": r_nuova, "classe": c_nuova, "hp": 20, "mana": 20, "vigore": 20, "xp": 0, "lvl": 1, "posizione": "Strada per Gauvadon", "img": img_nuova, "ultimo_visto": datetime.now().strftime('%Y-%m-%d %H:%M:%S')}])
            conn.update(worksheet='personaggi', data=pd.concat([df_p, nuovo], ignore_index=True))
            st.rerun()
    st.stop()

pg_idx = u_df.index[0]
pg = df_p.loc[pg_idx]
nome_pg = pg['nome_pg']

# --- SIDEBAR ---
with st.sidebar:
    st.header('🛡️ SCHEDA')
    if len(str(pg['img'])) > 5: st.image(pg['img'], use_container_width=True)
    with st.container(border=True):
        st.markdown(f"**{nome_pg}**")
        st.caption(f"📍 {pg['posizione']}")
        st.markdown(f'<div id="hp-bar">', unsafe_allow_html=True)
        st.progress(max(0.0, min(1.0, int(pg['hp']) / 20)))
        st.markdown(f'</div>❤️ HP: {int(pg["hp"])}/20', unsafe_allow_html=True)
    
    st.write("👥 Compagni:")
    comp = df_p[df_p['username'].astype(str) != str(st.session_state.user)]
    for _, c in comp.iterrows():
        with st.container(border=True):
            st.markdown(f"**{c['nome_pg']}**")
            st.progress(max(0.0, min(1.0, int(c['hp']) / 20)))

# --- CHAT UI ---
st.title('📜 Cronaca dell\'Abisso')
for _, r in df_m.tail(20).iterrows():
    with st.chat_message("assistant" if r['autore'] == 'Master' else "user"):
        st.markdown(r['testo'], unsafe_allow_html=True)

# --- AZIONE MASTER ---
if act := st.chat_input('Cosa fai?'):
    with st.spinner('Il Master narra...'):
        try:
            mie_abi = df_a[df_a['proprietario'] == nome_pg]
            abi_txt = "\n".join([f"- {a['nome']}" for _, a in mie_abi.iterrows()])
            altri = ", ".join([n for n in df_p['nome_pg'] if n != nome_pg])

            sys_msg = f"""Sei il Master. Giocatore attuale: {nome_pg}. 
            Altri nel gruppo: {altri}.
            Scrivi SOLO la narrazione. Dopo la storia scrivi ///DATI/// e i tag tecnici.
            TAG: DANNI_NEMICO, DANNI_RICEVUTI, MANA_USATO, VIGORE_USATO, XP, NOME_NEMICO, LUOGO."""
            
            res = client.chat.completions.create(messages=[{"role": "system", "content": sys_msg}, {"role": "user", "content": f"Azione di {nome_pg}: {act}\nAbilità: {abi_txt}"}], model="llama-3.3-70b-versatile").choices[0].message.content
            
            parts = res.split('///DATI///')
            testo_pulito = parts[0].strip()
            dati = parts[1] if len(parts) > 1 else ""

            def get_tag(tag, text):
                m = re.search(f"{tag}:\\s*(\\d+)", text)
                return int(m.group(1)) if m else 0

            v_ric = get_tag("DANNI_RICEVUTI", dati)
            loc_m = re.search(r"LUOGO:\s*(.+)", dati)
            nuovo_luogo = loc_m.group(1).strip() if loc_m else pg['posizione']

            df_p.at[pg_idx, 'hp'] = max(0, int(pg['hp']) - v_ric)
            df_p.at[pg_idx, 'posizione'] = nuovo_luogo
            df_p.at[pg_idx, 'ultimo_visto'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            conn.update(worksheet='personaggi', data=df_p)
            new_m = pd.concat([df_m, pd.DataFrame([{'data': datetime.now().strftime('%H:%M'), 'autore': nome_pg, 'testo': act}, {'data': datetime.now().strftime('%H:%M'), 'autore': 'Master', 'testo': testo_pulito}])], ignore_index=True)
            conn.update(worksheet='messaggi', data=new_m)
            
            st.cache_data.clear()
            st.rerun()
        except: st.error("Errore Master")
