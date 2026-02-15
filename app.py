import streamlit as st
import google.generativeai as genai
from streamlit_gsheets import GSheetsConnection
from streamlit_autorefresh import st_autorefresh
import pandas as pd
from datetime import datetime
import random

st.set_page_config(page_title='Apocrypha Master', layout='wide')

genai.configure(api_key=st.secrets['GEMINI_API_KEY'])
model = genai.GenerativeModel('gemini-1.5-flash')

conn = st.connection('gsheets', type=GSheetsConnection)
st_autorefresh(interval=15000, key='refresh')

if 'auth' not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    u = st.text_input('Nome reale (per identificarsi)')
    p = st.text_input('Parola d ordine:', type='password')
    if st.button('Apri il portale'):
        if p == 'apocrypha2026' and u:
            st.session_state.auth = True
            st.session_state.user = u
            st.rerun()
    st.stop()

def load():
    p = conn.read(worksheet='personaggi', ttl=0)
    m = conn.read(worksheet='messaggi', ttl=0)
    return p, m

df_p, df_m = load()

with st.sidebar:
    st.title('APOCRYPHA')
    st.header('Anime nell ombra')
    for _, r in df_p.iterrows():
        with st.container(border=True):
            st.markdown(f"**{r['nome_pg']}**")
            st.caption(f"{r['razza']} {r['classe']}")
            hp = int(r['hp'])
            st.progress(hp / 100, text=f"HP: {hp}")
    
    if st.session_state.user not in df_p['username'].values.astype(str):
        st.divider()
        n = st.text_input('Nome PG:')
        raz = st.selectbox('Razza:', ['Fenrithar', 'Elling', 'Elpide', 'Minotauro', 'Narun', 'Feyrin', 'Primaris', 'Inferis'])
        cla = st.selectbox('Classe:', ['Orrenai', 'Armagister', 'Mago'])
        if st.button('Incarna'):
            if n:
                new = pd.DataFrame([{'username': st.session_state.user, 'nome_pg': n, 'razza': raz, 'classe': cla, 'hp': 100}])
                conn.update(worksheet='personaggi', data=pd.concat([df_p, new], ignore_index=True))
                st.rerun()

st.title('Cronaca dell Abisso')

for _, r in df_m.tail(20).iterrows():
    role = 'assistant' if r['autore'] == 'Master' else 'user'
    with st.chat_message(role):
        st.write(f"**{r['autore']}**: {r['testo']}")

if act := st.chat_input('Narra la tua mossa...'):
    p_row = df_p[df_p['username'] == st.session_state.user]
    if not p_row.empty:
        pg = p_row.iloc[0]
        dt = f" [d20: {random.randint(1, 20)}]" if any(t in act.lower() for t in ['provo', 'tento', 'attacco', 'colpisco', 'percepisco', 'lancio']) else ''
        msg = f'{act}{dt}'
        u_row = pd.DataFrame([{'data': datetime.now().strftime('%H:%M'), 'autore': pg['nome_pg'], 'testo': msg}])
        df_m_up = pd.concat([df_m, u_row], ignore_index=True)
        
        prompt = (
            'Sei il Master di Apocrypha, un DM di D&D brutale. Narra in modo oscuro e crudo. '
            'Descrivi l ambiente e le sensazioni. Se vedi un d20: 1-10 fallimento, 11-15 scarso, 16-19 ottimo, 20 critico. '
            'Cronologia:\n' + '\n'.join([f"{r['autore']}: {r['testo']}" for _, r in df_m_up.tail(10).iterrows()])
        )
        
        res = model.generate_content(prompt).text
        m_row = pd.DataFrame([{'data': datetime.now().strftime('%H:%M'), 'autore': 'Master', 'testo': res}])
        conn.update(worksheet='messaggi', data=pd.concat([df_m_up, m_row], ignore_index=True))
        st.rerun()
