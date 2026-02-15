import streamlit as st
from google import genai
from streamlit_gsheets import GSheetsConnection
from streamlit_autorefresh import st_autorefresh
import pandas as pd
from datetime import datetime
import random

st.set_page_config(page_title='Apocrypha Master', layout='wide')

# Controllo Chiave
if "GEMINI_API_KEY" not in st.secrets:
    st.error("Manca la chiave GEMINI_API_KEY nei Secrets!")
    st.stop()

# Inizializzazione pulita del client
client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

conn = st.connection('gsheets', type=GSheetsConnection)
st_autorefresh(interval=15000, key='cronaca_refresh')

if 'auth' not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    u = st.text_input('Username')
    p = st.text_input('Password', type='password')
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
    st.title('🛡️ EROI')
    for _, r in df_p.iterrows():
        st.info(f"**{r['nome_pg']}** - HP: {r['hp']}/100")

st.title('📜 Cronaca dell Abisso')
for _, r in df_m.tail(15).iterrows():
    role = 'assistant' if r['autore'] == 'Master' else 'user'
    with st.chat_message(role):
        st.write(f"**{r['autore']}**: {r['testo']}")

if act := st.chat_input('Cosa fai?'):
    pg_nome = df_p[df_p['username'] == st.session_state.user].iloc[0]['nome_pg']
    msg_utente = f"{act} [d20: {random.randint(1, 20)}]"
    
    with st.spinner("Il Master narra..."):
        try:
            # Specifichiamo il modello senza prefissi per evitare il 404
            response = client.models.generate_content(
                model='gemini-1.5-flash', 
                contents=f"Sei il Master di Apocrypha. Narra brevemente: {pg_nome} fa {msg_utente}"
            )
            master_text = response.text

            # Salvataggio
            new_data = pd.DataFrame([
                {'data': datetime.now().strftime('%H:%M'), 'autore': pg_nome, 'testo': msg_utente},
                {'data': datetime.now().strftime('%H:%M'), 'autore': 'Master', 'testo': master_text}
            ])
            conn.update(worksheet='messaggi', data=pd.concat([df_m, new_data], ignore_index=True))
            st.rerun()

        except Exception as e:
            # Se vedi ancora errore qui, riportami il testo esatto
            st.error(f"Errore di comunicazione: {e}")
