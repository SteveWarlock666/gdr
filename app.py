import streamlit as st
import google.generativeai as genai
from streamlit_gsheets import GSheetsConnection
from streamlit_autorefresh import st_autorefresh
import pandas as pd
from datetime import datetime
import random

st.set_page_config(page_title='Apocrypha Master', layout='wide')

# 1. Configurazione API e Scelta Modello
if "GEMINI_API_KEY" not in st.secrets:
    st.error("Manca la chiave nei Secrets!")
    st.stop()

genai.configure(api_key=st.secrets['GEMINI_API_KEY'])

# Cerchiamo il modello corretto per evitare il 404
try:
    available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    # Preferenza: 1.5-flash, altrimenti il primo disponibile
    model_name = 'models/gemini-1.5-flash' if 'models/gemini-1.5-flash' in available_models else available_models[0]
    model = genai.GenerativeModel(model_name)
except Exception as e:
    st.error(f"Errore inizializzazione Google: {e}")
    st.stop()

# 2. Connessione Fogli
conn = st.connection('gsheets', type=GSheetsConnection)
st_autorefresh(interval=15000, key='refresh')

if 'auth' not in st.session_state:
    st.session_state.auth = False

# 3. Login
if not st.session_state.auth:
    u = st.text_input('Chi entra nell Abisso?')
    p = st.text_input('Parola d ordine:', type='password')
    if st.button('Entra'):
        if p == 'apocrypha2026' and u:
            st.session_state.auth = True
            st.session_state.user = u
            st.rerun()
    st.stop()

# 4. Caricamento Dati
df_p = conn.read(worksheet='personaggi', ttl=0)
df_m = conn.read(worksheet='messaggi', ttl=0)

# Sidebar
with st.sidebar:
    st.title('APOCRYPHA')
    for _, r in df_p.iterrows():
        st.info(f"**{r['nome_pg']}**\n\nHP: {r['hp']}/100")
    
    if st.session_state.user not in df_p['username'].values.astype(str):
        with st.expander("Crea Personaggio"):
            n = st.text_input('Nome:')
            raz = st.selectbox('Razza:', ['Fenrithar', 'Elling', 'Elpide', 'Minotauro', 'Narun', 'Feyrin', 'Primaris', 'Inferis'])
            cla = st.selectbox('Classe:', ['Orrenai', 'Armagister', 'Mago'])
            if st.button('Crea'):
                new = pd.DataFrame([{'username': st.session_state.user, 'nome_pg': n, 'razza': raz, 'classe': cla, 'hp': 100}])
                conn.update(worksheet='personaggi', data=pd.concat([df_p, new], ignore_index=True))
                st.rerun()

# 5. Chat
st.title('📜 Cronaca')
for _, r in df_m.tail(15).iterrows():
    role = 'assistant' if r['autore'] == 'Master' else 'user'
    with st.chat_message(role):
        st.write(f"**{r['autore']}**: {r['testo']}")

if act := st.chat_input('Cosa fai?'):
    pg_nome = df_p[df_p['username'] == st.session_state.user].iloc[0]['nome_pg']
    dt = f" [d20: {random.randint(1, 20)}]" if "tento" in act.lower() or "attacco" in act.lower() else ""
    user_msg = f"{act}{dt}"
    
    with st.spinner("Il Master narra..."):
        prompt = f"Sei il Master di Apocrypha, GDR dark fantasy. Narra l'esito di: {pg_nome} fa {user_msg}. Sii breve e brutale."
        try:
            res = model.generate_content(prompt).text
            new_data = pd.DataFrame([
                {'data': datetime.now().strftime('%H:%M'), 'autore': pg_nome, 'testo': user_msg},
                {'data': datetime.now().strftime('%H:%M'), 'autore': 'Master', 'testo': res}
            ])
            conn.update(worksheet='messaggi', data=pd.concat([df_m, new_data], ignore_index=True))
            st.rerun()
        except Exception as e:
            st.error(f"Errore Master: {e}")
