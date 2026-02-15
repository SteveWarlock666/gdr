import streamlit as st
from google import genai
from streamlit_gsheets import GSheetsConnection
from streamlit_autorefresh import st_autorefresh
import pandas as pd
from datetime import datetime
import random

st.set_page_config(page_title='Apocrypha Master', layout='wide')

if 'GEMINI_API_KEY' not in st.secrets:
    st.error('Manca la chiave nei Secrets')
    st.stop()

client = genai.Client(api_key=st.secrets['GEMINI_API_KEY'])
conn = st.connection('gsheets', type=GSheetsConnection)
st_autorefresh(interval=15000, key='refresh')

if 'auth' not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    u = st.text_input('Chi entra nell Abisso?')
    p = st.text_input('Parola d ordine:', type='password')
    if st.button('Entra'):
        if p == 'apocrypha2026' and u:
            st.session_state.auth = True
            st.session_state.user = u
            st.rerun()
    st.stop()

df_p = conn.read(worksheet='personaggi', ttl=0)
df_m = conn.read(worksheet='messaggi', ttl=0)

with st.sidebar:
    st.title('APOCRYPHA')
    for _, r in df_p.iterrows():
        with st.container(border=True):
            st.markdown(f"**{r['nome_pg']}**")
            st.progress(int(r['hp'])/100, text=f"HP: {r['hp']}")
    
    if st.session_state.user not in df_p['username'].values.astype(str):
        with st.expander('Crea Personaggio'):
            n = st.text_input('Nome:')
            rz = st.selectbox('Razza:', ['Fenrithar', 'Elling', 'Elpide', 'Minotauro', 'Narun', 'Feyrin', 'Primaris', 'Inferis'])
            cl = st.selectbox('Classe:', ['Orrenai', 'Armagister', 'Mago'])
            if st.button('Crea'):
                if n:
                    new = pd.DataFrame([{'username': st.session_state.user, 'nome_pg': n, 'razza': rz, 'classe': cl, 'hp': 100}])
                    conn.update(worksheet='personaggi', data=pd.concat([df_p, new], ignore_index=True))
                    st.rerun()

st.title('Cronaca dell Abisso')
for _, r in df_m.tail(15).iterrows():
    role = 'assistant' if r['autore'] == 'Master' else 'user'
    with st.chat_message(role):
        st.write(f"**{r['autore']}**: {r['testo']}")

if act := st.chat_input('Cosa fai?'):
    pg_data = df_p[df_p['username'] == st.session_state.user]
    if pg_data.empty:
        st.warning('Crea prima un personaggio nella barra laterale')
        st.stop()
    
    pg_nome = pg_data.iloc[0]['nome_pg']
    dt = f" [d20: {random.randint(1, 20)}]" if any(x in act.lower() for x in ['tento', 'attacco', 'cerco']) else ''
    msg = f"{act}{dt}"
    
    with st.spinner('Il Master narra...'):
        prompt = f"Sei il Master di Apocrypha, GDR dark fantasy. Narra l esito di: {pg_nome} fa {msg}. Sii breve e brutale."
        try:
            response = client.models.generate_content(model='gemini-1.5-flash', contents=prompt)
            res_text = response.text
            new_data = pd.DataFrame([
                {'data': datetime.now().strftime('%H:%M'), 'autore': pg_nome, 'testo': msg},
                {'data': datetime.now().strftime('%H:%M'), 'autore': 'Master', 'testo': res_text}
            ])
            conn.update(worksheet='messaggi', data=pd.concat([df_m, new_data], ignore_index=True))
            st.rerun()
        except Exception as e:
            st.error(f"Errore Master: {e}")
