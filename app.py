import streamlit as st
from google import genai
from google.genai import types
from streamlit_gsheets import GSheetsConnection
from streamlit_autorefresh import st_autorefresh
import pandas as pd
from datetime import datetime
import random

st.set_page_config(page_title='Apocrypha', layout='wide')

# 1. Configurazione forzata sulla versione stabile v1
if "GEMINI_API_KEY" not in st.secrets:
    st.error("Manca la chiave!")
    st.stop()

# Inizializzazione esplicita
client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"], http_options={'api_version': 'v1'})

conn = st.connection('gsheets', type=GSheetsConnection)
st_autorefresh(interval=15000, key='global_refresh')

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

# Caricamento dati
df_p = conn.read(worksheet='personaggi', ttl=0)
df_m = conn.read(worksheet='messaggi', ttl=0)

with st.sidebar:
    st.title('EROI')
    for _, r in df_p.iterrows():
        st.write(f"**{r['nome_pg']}** HP: {r['hp']}")

st.title('Cronaca')
for _, r in df_m.tail(15).iterrows():
    role = 'assistant' if r['autore'] == 'Master' else 'user'
    with st.chat_message(role):
        st.write(f"**{r['autore']}**: {r['testo']}")

if act := st.chat_input('Cosa fai?'):
    try:
        pg = df_p[df_p['username'] == st.session_state.user].iloc[0]['nome_pg']
        msg_u = f"{act} [d20: {random.randint(1, 20)}]"
        
        with st.spinner('Il Master risponde...'):
            # Usiamo un nome modello che non può fallire nella v1
            response = client.models.generate_content(
                model='gemini-1.5-flash',
                contents=f"Sei il Master di Apocrypha. Narra brevemente: {pg} fa {msg_u}"
            )
            txt_master = response.text

            new_data = pd.DataFrame([
                {'data': datetime.now().strftime('%H:%M'), 'autore': pg, 'testo': msg_u},
                {'data': datetime.now().strftime('%H:%M'), 'autore': 'Master', 'testo': txt_master}
            ])
            
            updated_df = pd.concat([df_m, new_data], ignore_index=True)
            conn.update(worksheet='messaggi', data=updated_df)
            
            st.cache_data.clear()
            st.rerun()
            
    except Exception as e:
        # Se esce ancora 404 qui, la chiave non è abilitata per le API generative
        st.error(f"Errore: {e}")
