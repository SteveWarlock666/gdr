import streamlit as st
from groq import Groq
from streamlit_gsheets import GSheetsConnection
from streamlit_autorefresh import st_autorefresh
import pandas as pd
from datetime import datetime
import re

st.set_page_config(page_title='Apocrypha Master', layout='wide')

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; }
    div[data-testid="stSidebarUserContent"] { padding-top: 1rem; }
    .compact-row { display: flex; align-items: center; gap: 10px; margin-bottom: 4px; }
    .compact-label { font-size: 12px !important; min-width: 75px; margin: 0 !important; white-space: nowrap; }
    .stProgress { height: 6px !important; flex-grow: 1; }
    #hp-bar .stProgress div[role="progressbar"] > div { background-color: #ff4b4b !important; }
    #mana-bar .stProgress div[role="progressbar"] > div { background-color: #00f2ff !important; }
    #stamina-bar .stProgress div[role="progressbar"] > div { background-color: #00ff88 !important; }
    #xp-bar .stProgress div[role="progressbar"] > div { background-color: #ffffff !important; }
    </style>
""", unsafe_allow_html=True)

if 'GROQ_API_KEY' not in st.secrets:
    st.error("Manca la chiave!")
    st.stop()

client = Groq(api_key=st.secrets['GROQ_API_KEY'])
conn = st.connection('gsheets', type=GSheetsConnection)
st_autorefresh(interval=15000, key='global_sync')

if 'auth' not in st.session_state:
    st.session_state.auth = False

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

XP_LEVELS = {1: 0, 2: 300, 3: 900, 4: 2700, 5: 6500}

try:
    df_p = conn.read(worksheet='personaggi', ttl=0)
    for col in ['mana', 'vigore', 'xp', 'lvl', 'ultimo_visto', 'posizione']:
        if col not in df_p.columns:
            df_p[col] = 0 if col != 'posizione' else 'Skyheaven - Strada per Gauvadon'
    df_p = df_p.fillna(0)
    df_m = conn.read(worksheet='messaggi', ttl=0).fillna('')
    df_a = conn.read(worksheet='abilita', ttl=0).fillna('')
except Exception as e:
    st.error(f"Errore: {e}")
    st.stop()

user_pg_df = df_p[df_p['username'].astype(str) == str(st.session_state.user)]

with st.sidebar:
    st.header('🛡️ SCHEDA EROE')
    if not user_pg_df.empty:
        pg = user_pg_df.iloc[0]
        nome_pg = pg['nome_pg']
        with st.container(border=True):
            st.markdown(f"**{nome_pg} (Lv. {int(pg['lvl'])})**")
            st.caption(f"📍 {pg['posizione']}")
            st.caption(f"{pg['razza']} • {pg['classe']}")
            st.markdown(f'<div class="compact-row" id="hp-bar"><p class="compact-label">❤️ HP: {int(pg["hp"])}/20</p>', unsafe_allow_html=True)
            st.progress(max(0.0, min(1.0, int(pg['hp']) / 20)))
            st.markdown('</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="compact-row" id="mana-bar"><p class="compact-label">✨ MN: {int(pg["mana"])}/20</p>', unsafe_allow_html=True)
            st.progress(max(0.0, min(1.0, int(pg['mana']) / 20)))
            st.markdown('</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="compact-row" id="stamina-bar"><p class="compact-label">⚡ VG: {int(pg["vigore"])}/20</p>', unsafe_allow_html=True)
            st.progress(max(0.0, min(1.0, int(pg['vigore']) / 20)))
            st.markdown('</div>', unsafe_allow_html=True)
            st.divider()
            cur_lvl, cur_xp = int(pg['lvl']), int(pg['xp'])
            next_xp = XP_LEVELS.get(cur_lvl + 1, 99999)
            st.markdown(f'<div class="compact-row" id="xp-bar"><p class="compact-label">📖 XP: {cur_xp}/{next_xp}</p>', unsafe_allow_html=True)
            st.progress(max(0.0, min(1.0, cur_xp / next_xp)))
            st.markdown('</div>', unsafe_allow_html=True)

st.title('📜 Cronaca dell Abisso')
for _, r in df_m.tail(15).iterrows():
    with st.chat_message("assistant" if r['autore'] == 'Master' else "user"):
        st.write(f"**{r['autore']}**: {r['testo']}")

if not user_pg_df.empty:
    if act := st.chat_input('Cosa fai?'):
        nome_mio = pg['nome_pg']
        with st.spinner('Il Master narra...'):
            try:
                storia = "\n".join([f"{r['autore']}: {r['testo']}" for _, r in df_m.tail(5).iterrows()])
                mie_abi = df_a[df_a['proprietario'] == nome_mio]
                dettagli_abi = "\n".join([f"- {a['nome']}: {a['descrizione']} (Costo: {a['costo']}, Dadi: {a['dadi']})" for _, a in mie_abi.iterrows()])
                
                sys_msg = f"""Sei un Master dark fantasy. Luogo: {pg['posizione']}. Giocatore: {nome_mio}.
                STYLE: Narrazione pura. NON scrivere mai risultati numerici (es. "roll: 15").
                LOGICA: d20 interno per successo (1-10 Fallimento, 11-14 -1HP nemico, 15-19 -2HP, 20 Critico).
                Usa i dadi dell'abilità per dare spessore alla descrizione.
                TAG OBBLIGATORI: DANNI: X, MANA_USATO: X, VIGORE_USATO: X, XP: X, LUOGO: Nome."""
                
                res = client.chat.completions.create(messages=[{"role": "system", "content": sys_msg}, {"role": "user", "content": f"Contesto: {storia}\nAbilità: {dettagli_abi}\nAzione: {act}"}], model="llama-3.3-70b-versatile").choices[0].message.content
                
                d_hp = re.search(r"DANNI:\s*(\d+)", res)
                d_mn = re.search(r"MANA_USATO:\s*(\d+)", res)
                d_vg = re.search(r"VIGORE_USATO:\s*(\d+)", res)
