import streamlit as st
import google.generativeai as genai
from streamlit_gsheets import GSheetsConnection
from streamlit_autorefresh import st_autorefresh
import pandas as pd
from datetime import datetime
import random

st.set_page_config(page_title='Apocrypha Master', layout='wide')

# Configura Gemini
if "GEMINI_API_KEY" not in st.secrets:
    st.error("Manca la chiave GEMINI_API_KEY nei Secrets!")
    st.stop()

genai.configure(api_key=st.secrets['GEMINI_API_KEY'])
model = genai.GenerativeModel('gemini-1.5-flash-latest')

conn = st.connection('gsheets', type=GSheetsConnection)

# Refresh ogni 20 secondi per non intasare Google
st_autorefresh(interval=20000, key='global_refresh')

if 'auth' not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    u = st.text_input('Chi osa entrare?')
    p = st.text_input('Parola d ordine:', type='password')
    if st.button('Apri il portale'):
        if p == 'apocrypha2026' and u:
            st.session_state.auth = True
            st.session_state.user = u
            st.rerun()
    st.stop()

# Caricamento dati
try:
    df_p = conn.read(worksheet='personaggi', ttl=0)
    df_m = conn.read(worksheet='messaggi', ttl=0)
except Exception as e:
    st.error(f"Errore lettura foglio: {e}")
    st.stop()

with st.sidebar:
    st.title('APOCRYPHA')
    st.header('Anime nell ombra')
    for _, r in df_p.iterrows():
        with st.container(border=True):
            st.markdown(f"**{r['nome_pg']}**")
            st.caption(f"{r['razza']} {r['classe']}")
            st.progress(int(r['hp']) / 100, text=f"HP: {r['hp']}")
    
    if st.session_state.user not in df_p['username'].values.astype(str):
        st.divider()
        n = st.text_input('Nome PG:')
        raz = st.selectbox('Razza:', ['Fenrithar', 'Elling', 'Elpide', 'Minotauro', 'Narun', 'Feyrin', 'Primaris', 'Inferis'])
        cla = st.selectbox('Classe:', ['Orrenai', 'Armagister', 'Mago'])
        if st.button('Incarna'):
            if n:
                new_pg = pd.DataFrame([{'username': st.session_state.user, 'nome_pg': n, 'razza': raz, 'classe': cla, 'hp': 100}])
                conn.update(worksheet='personaggi', data=pd.concat([df_p, new_pg], ignore_index=True))
                st.rerun()

st.title('Cronaca dell Abisso')

# Mostra i messaggi esistenti
for _, r in df_m.tail(15).iterrows():
    role = 'assistant' if r['autore'] == 'Master' else 'user'
    with st.chat_message(role):
        st.write(f"**{r['autore']}**: {r['testo']}")

# Input azione
if act := st.chat_input('Descrivi la tua mossa...'):
    pg_row = df_p[df_p['username'] == st.session_state.user]
    if pg_row.empty:
        st.warning("Devi creare un PG nella barra laterale prima di scrivere.")
    else:
        pg_nome = pg_row.iloc[0]['nome_pg']
        
        # Gestione d20
        dt = ""
        if any(t in act.lower() for t in ['attacco', 'tento', 'provo', 'cerco', 'percepisco', 'scalo']):
            dt = f" [d20: {random.randint(1, 20)}]"
        
        testo_utente = f"{act}{dt}"
        
        # Generazione risposta Master
        with st.spinner("Il Master osserva..."):
            prompt = (
                f"Sei il Master di Apocrypha, un DM oscuro e brutale. Narra con stile dark fantasy. "
                f"Reagisci all'azione di {pg_nome}: {testo_utente}. "
                f"Contesto precedente:\n" + "\n".join([f"{row['autore']}: {row['testo']}" for _, row in df_m.tail(5).iterrows()])
            )
            try:
                response = model.generate_content(prompt)
                master_res = response.text
                
                # Prepara i nuovi dati
                new_msgs = pd.DataFrame([
                    {'data': datetime.now().strftime('%H:%M'), 'autore': pg_nome, 'testo': testo_utente},
                    {'data': datetime.now().strftime('%H:%M'), 'autore': 'Master', 'testo': master_res}
                ])
                
                # Salva tutto
                updated_df = pd.concat([df_m, new_msgs], ignore_index=True)
                conn.update(worksheet='messaggi', data=updated_df)
                st.rerun()
            except Exception as e:
                st.error(f"Errore durante l'invio: {e}")
