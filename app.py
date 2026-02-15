import streamlit as st
from google import genai
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import random

st.set_page_config(page_title='Apocrypha', layout='wide')

if 'GEMINI_API_KEY' not in st.secrets:
    st.error('Chiave mancante nei Secrets')
    st.stop()

client = genai.Client(api_key=st.secrets['GEMINI_API_KEY'])
conn = st.connection('gsheets', type=GSheetsConnection)

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

df_p = conn.read(worksheet='personaggi', ttl=0)
df_m = conn.read(worksheet='messaggi', ttl=0)

with st.sidebar:
    st.title('Stato Eroi')
    for _, r in df_p.iterrows():
        st.write(f"**{r['nome_pg']}** HP: {r['hp']}")
    
    if st.session_state.user not in df_p['username'].values.astype(str):
        with st.expander('Nuovo Eroe'):
            n = st.text_input('Nome')
            if st.button('Crea'):
                new_pg = pd.DataFrame([{'username': st.session_state.user, 'nome_pg': n, 'hp': 100}])
                conn.update(worksheet='personaggi', data=pd.concat([df_p, new_pg], ignore_index=True))
                st.rerun()

st.title('Cronaca')
for _, r in df_m.tail(15).iterrows():
    with st.chat_message('assistant' if r['autore'] == 'Master' else 'user'):
        st.write(f"{r['autore']}: {r['testo']}")

if act := st.chat_input('Cosa fai?'):
    pg = df_p[df_p['username'] == st.session_state.user].iloc[0]['nome_pg']
    res_text = None
    
    for m in ['gemini-1.5-flash', 'gemini-1.5-flash-8b', 'gemini-2.0-flash']:
        try:
            response = client.models.generate_content(model=m, contents=f"Sei il Master di Apocrypha. Narra brevemente: {pg} fa {act}")
            res_text = response.text
            break
        except:
            continue
    
    if res_text:
        new_m = pd.DataFrame([
            {'data': datetime.now().strftime('%H:%M'), 'autore': pg, 'testo': act},
            {'data': datetime.now().strftime('%H:%M'), 'autore': 'Master', 'testo': res_text}
        ])
        conn.update(worksheet='messaggi', data=pd.concat([df_m, new_m], ignore_index=True))
        st.rerun()
    else:
        st.error('Servizio temporaneamente non disponibile')
