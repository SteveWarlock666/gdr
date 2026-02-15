import streamlit as st
from openai import OpenAI
from streamlit_gsheets import GSheetsConnection
from streamlit_autorefresh import st_autorefresh
import pandas as pd
from datetime import datetime
import random

st.set_page_config(page_title='Apocrypha Master', layout='wide')
client = OpenAI(api_key=st.secrets['OPENAI_API_KEY'])
conn = st.connection('gsheets', type=GSheetsConnection)

st_autorefresh(interval=5000, key='global_refresh')

if 'autenticato' not in st.session_state:
    st.session_state.autenticato = False

if not st.session_state.autenticato:
    user = st.text_input('Chi osa entrare?')
    pwd = st.text_input('Parola d ordine:', type='password')
    if st.button('Apri il portale'):
        if pwd == 'apocrypha2026' and user:
            st.session_state.autenticato = True
            st.session_state.username = user
            st.rerun()
    st.stop()

def load_world():
    df_pg = conn.read(worksheet='personaggi', ttl=0)
    df_chat = conn.read(worksheet='messaggi', ttl=0)
    return df_pg, df_chat

df_pg, df_chat = load_world()

with st.sidebar:
    st.header('Ananime nell ombra')
    for _, row in df_pg.iterrows():
        st.write(f'**{row["nome_pg"]}** - {row["razza"]} {row["classe"]} [HP: {row["hp"]}]')
    
    if st.session_state.username not in df_pg['username'].values.astype(str):
        st.subheader('Incarna un Eroe')
        n_pg = st.text_input('Nome:')
        r_pg = st.selectbox('Razza:', ['Fenrithar', 'Elling', 'Elpide', 'Minotauro', 'Narun', 'Feyrin', 'Primaris', 'Inferis'])
        c_pg = st.selectbox('Classe:', ['Orrenai', 'Armagister', 'Mago'])
        if st.button('Prendi vita'):
            if n_pg:
                new_data = pd.DataFrame([{'username': st.session_state.username, 'nome_pg': n_pg, 'razza': r_pg, 'classe': c_pg, 'hp': 100}])
                conn.update(worksheet='personaggi', data=pd.concat([df_pg, new_data], ignore_index=True))
                st.rerun()

st.title('Cronaca dell Abisso')

for _, row in df_chat.tail(25).iterrows():
    role = 'assistant' if row['autore'] == 'Master' else 'user'
    with st.chat_message(role):
        st.write(f'**{row["autore"]}**: {row["testo"]}')

if action := st.chat_input('Narra la tua mossa...'):
    pg_row = df_pg[df_pg['username'] == st.session_state.username]
    if pg_row.empty:
        st.error('Devi prima incarnare un eroe.')
    else:
        pg = pg_row.iloc[0]
        dice_tag = ''
        triggers = ['provo', 'tento', 'cerco', 'attacco', 'colpisco', 'indago', 'furtivo', 'percepisco', 'ascolto', 'lancio']
        if any(t in action.lower() for t in triggers):
            res = random.randint(1, 20)
            dice_tag = f' [d20: {res}]'
        
        user_msg = f'{action}{dice_tag}'
        new_user_row = pd.DataFrame([{'data': datetime.now().strftime('%H:%M'), 'autore': pg['nome_pg'], 'testo': user_msg}])
        df_chat_upd = pd.concat([df_chat, new_user_row], ignore_index=True)
        
        master_prompt = (
            'Sei il Master di Apocrypha, un DM di D&D brutale e descrittivo. '
            'Non limitarti a rispondere: genera contesto. Descrivi la puzza di zolfo, il riverbero delle torce, '
            'il rumore di ossa che scricchiolano. Se c’è un d20: 1-10 fallimento atroce, 11-15 successo risicato, '
            '16-19 colpo da maestro, 20 leggenda. Sii articolato, oscuro e crudo. Reagisci ai dettagli del giocatore.'
        )
        
        history = [{'role': 'system', 'content': master_prompt}]
        for _, r in df_chat_upd.tail(15).iterrows():
            history.append({'role': 'assistant' if r['autore'] == 'Master' else 'user', 'content': f'{r["autore"]}: {r["testo"]}'})
        
        ai_resp = client.chat.completions.create(model='gpt-4o', messages=history).choices[0].message.content
        master_row = pd.DataFrame([{'data': datetime.now().strftime('%H:%M'), 'autore': 'Master', 'testo': ai_resp}])
        df_final = pd.concat([df_chat_upd, master_row], ignore_index=True)
        
        conn.update(worksheet='messaggi', data=df_final)
        st.rerun()
