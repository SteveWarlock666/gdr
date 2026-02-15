import streamlit as st
from google import genai
from streamlit_gsheets import GSheetsConnection
from streamlit_autorefresh import st_autorefresh
import pandas as pd
from datetime import datetime
import random

st.set_page_config(page_title='Apocrypha Master', layout='wide')

# Verifica chiave nei Secrets
if "GEMINI_API_KEY" not in st.secrets:
    st.error("Inserisci la chiave nei Secrets di Streamlit!")
    st.stop()

client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
conn = st.connection('gsheets', type=GSheetsConnection)

# Refresh ogni 15 secondi per leggere i messaggi degli altri
st_autorefresh(interval=15000, key='refresh_generale')

if 'auth' not in st.session_state:
    st.session_state.auth = False

# Login
if not st.session_state.auth:
    u = st.text_input('Chi sei?')
    p = st.text_input('Password', type='password')
    if st.button('Entra'):
        if p == 'apocrypha2026' and u:
            st.session_state.auth = True
            st.session_state.user = u
            st.rerun()
    st.stop()

# Lettura dati
df_p = conn.read(worksheet='personaggi', ttl=0)
df_m = conn.read(worksheet='messaggi', ttl=0)

# Sidebar
with st.sidebar:
    st.title('🛡️ EROI')
    for _, r in df_p.iterrows():
        st.write(f"**{r['nome_pg']}** (HP: {r['hp']})")

# Cronaca
st.title('📜 Cronaca')
for _, r in df_m.tail(15).iterrows():
    role = 'assistant' if r['autore'] == 'Master' else 'user'
    with st.chat_message(role):
        st.write(f"**{r['autore']}**: {r['testo']}")

# Azione Master
if act := st.chat_input('Cosa fai?'):
    pg_nome = df_p[df_p['username'] == st.session_state.user].iloc[0]['nome_pg']
    msg_u = f"{act} [d20: {random.randint(1, 20)}]"
    
    with st.spinner("Il Master narra..."):
        try:
            # Modello 1.5-flash: è quello con la quota gratuita più generosa
            response = client.models.generate_content(
                model='gemini-1.5-flash', 
                contents=f"Sei il Master di Apocrypha. Narra brevemente: {pg_nome} fa {msg_u}"
            )
            
            new_rows = pd.DataFrame([
                {'data': datetime.now().strftime('%H:%M'), 'autore': pg_nome, 'testo': msg_u},
                {'data': datetime.now().strftime('%H:%M'), 'autore': 'Master', 'testo': response.text}
            ])
            conn.update(worksheet='messaggi', data=pd.concat([df_m, new_rows], ignore_index=True))
            st.rerun()

        except Exception as e:
            st.error(f"Errore: {e}")
            st.info("Se l'errore è 429, aspetta 60 secondi: hai superato il limite di messaggi gratuiti al minuto.")
