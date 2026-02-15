import streamlit as st
from google import genai
from streamlit_gsheets import GSheetsConnection
from streamlit_autorefresh import st_autorefresh
import pandas as pd
from datetime import datetime
import random

st.set_page_config(page_title='Apocrypha', layout='wide')

if "GEMINI_API_KEY" not in st.secrets:
    st.error("Chiave mancante!")
    st.stop()

client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
conn = st.connection('gsheets', type=GSheetsConnection)
st_autorefresh(interval=15000, key='refresh_cronaca')

if 'auth' not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    u = st.text_input('User')
    p = st.text_input('Pass', type='password')
    if st.button('Entra'):
        if p == 'apocrypha2026' and u:
            st.session_state.auth = True
            st.session_state.user = u
            st.rerun()
    st.stop()

df_p = conn.read(worksheet='personaggi', ttl=0)
df_m = conn.read(worksheet='messaggi', ttl=0)

with st.sidebar:
    st.title('EROI')
    for _, r in df_p.iterrows():
        st.write(f"{r['nome_pg']} HP:{r['hp']}")

st.title('Cronaca')
for _, r in df_m.tail(15).iterrows():
    with st.chat_message('assistant' if r['autore'] == 'Master' else 'user'):
        st.write(f"{r['autore']}: {r['testo']}")

if act := st.chat_input('Cosa fai?'):
    try:
        pg = df_p[df_p['username'] == st.session_state.user].iloc[0]['nome_pg']
        msg_u = f"{act} [d20:{random.randint(1, 20)}]"
        
        # 1. Chiamata AI
        res = client.models.generate_content(model='gemini-1.5-flash', contents=act)
        txt_m = res.text

        # 2. Creazione nuove righe
        new = pd.DataFrame([
            {'data': datetime.now().strftime('%H:%M'), 'autore': pg, 'testo': msg_u},
            {'data': datetime.now().strftime('%H:%M'), 'autore': 'Master', 'testo': txt_m}
        ])
        
        # 3. Aggiornamento forzato
        updated = pd.concat([df_m, new], ignore_index=True)
        conn.update(worksheet='messaggi', data=updated)
        
        # 4. Reset manuale per forzare il movimento
        st.cache_data.clear()
        st.rerun()
    except Exception as e:
        st.error(f"Blocco: {e}")
