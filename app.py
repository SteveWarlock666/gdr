import streamlit as st
from groq import Groq
from streamlit_gsheets import GSheetsConnection
from streamlit_autorefresh import st_autorefresh
import pandas as pd
from datetime import datetime
import random

# Configurazione Pagina
st.set_page_config(page_title='Apocrypha Master', layout='wide', initial_sidebar_state='expanded')

# CSS per stile Dark GDR
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #e0e0e0; }
    .stChatMessage { border-radius: 10px; border: 1px solid #333; margin-bottom: 10px; }
    .stSidebar { background-color: #161b22; border-right: 1px solid #30363d; }
    </style>
""", unsafe_allow_html=True)

# Controllo Chiavi
if 'GROQ_API_KEY' not in st.secrets:
    st.error('Manca la chiave GROQ_API_KEY nei Secrets!')
    st.stop()

client = Groq(api_key=st.secrets['GROQ_API_KEY'])
conn = st.connection('gsheets', type=GSheetsConnection)

# Refresh automatico ogni 15 secondi
st_autorefresh(interval=15000, key='cronaca_refresh')

if 'auth' not in st.session_state:
    st.session_state.auth = False

# Login Schermata
if not st.session_state.auth:
    st.title('🌑 APOCRYPHA: ACCESSO')
    u = st.text_input('Chi osa sfidare l Abisso?')
    p = st.text_input('Parola d ordine:', type='password')
    if st.button('Entra'):
        if p == 'apocrypha2026' and u:
            st.session_state.auth = True
            st.session_state.user = u
            st.rerun()
    st.stop()

# Caricamento Dati
df_p = conn.read(worksheet='personaggi', ttl=0)
df_m = conn.read(worksheet='messaggi', ttl=0)

# Sidebar: Stato Eroi
with st.sidebar:
    st.title('🛡️ EROI')
    for _, r in df_p.iterrows():
        with st.container(border=True):
            st.markdown(f"**{r['nome_pg']}**")
            st.caption(f"{r['razza']} {r['classe']}")
            hp_val = int(r['hp'])
            color = "green" if hp_val > 50 else "orange" if hp_val > 20 else "red"
            st.markdown(f"<span style='color:{color}'>HP: {hp_val}/100</span>", unsafe_allow_html=True)
            st.progress(max(0, min(100, hp_val)) / 100)
    
    # Creazione PG se non esiste
    if st.session_state.user not in df_p['username'].values.astype(str):
        with st.expander('Crea il tuo Eroe'):
            n = st.text_input('Nome:')
            rz = st.selectbox('Razza:', ['Fenrithar', 'Elling', 'Elpide', 'Minotauro', 'Narun', 'Feyrin', 'Primaris', 'Inferis'])
            cl = st.selectbox('Classe:', ['Orrenai', 'Armagister', 'Mago'])
            if st.button('Risvegliati'):
                if n:
                    new_pg = pd.DataFrame([{'username': st.session_state.user, 'nome_pg': n, 'razza': rz, 'classe': cl, 'hp': 100}])
                    conn.update(worksheet='personaggi', data=pd.concat([df_p, new_pg], ignore_index=True))
                    st.rerun()

# Area Chat / Cronaca
st.title('📜 Cronaca dell Abisso')
st.markdown("---")

# Visualizzazione messaggi (ultimi 20)
for _, r in df_m.tail(20).iterrows():
    role = 'assistant' if r['autore'] == 'Master' else 'user'
    with st.chat_message(role):
        st.write(f"**{r['autore']}** [{r['data']}]: {r['testo']}")

# Input Azione
if act := st.chat_input('Qual è la tua mossa?'):
    pg_row = df_p[df_p['username'] == st.session_state.user]
    if pg_row.empty:
        st.warning('Crea prima un personaggio nella sidebar!')
        st.stop()
    
    pg_nome = pg_row.iloc[0]['nome_pg']
    d20 = random.randint(1, 20)
    azione_log = f"{act} [d20: {d20}]"
    
    with st.spinner('Il Master sta scrivendo il tuo destino...'):
        try:
            # Memoria: prendiamo gli ultimi 5 messaggi per dare contesto
            context = "\n".join([f"{r['autore']}: {r['testo']}" for _, r in df_m.tail(5).iterrows()])
            
            prompt = f"""Sei il Master di Apocrypha, un GDR dark fantasy brutale. 
            Contesto recente:
            {context}
            
            Azione attuale: {pg_nome} fa {azione_log}.
            Narra l'esito in massimo 3 frasi. Sii oscuro, descrittivo e spietato."""
            
            completion = client.chat.completions.create(
                messages=[{"role": "system", "content": "Sei un Master di GDR oscuro e sintetico."},
                          {"role": "user", "content": prompt}],
                model="llama-3.3-70b-versatile",
                temperature=0.7
            )
            master_res = completion.choices[0].message.content
            
            # Aggiornamento Sheet
            nuovi_msg = pd.DataFrame([
                {'data': datetime.now().strftime('%H:%M'), 'autore': pg_nome, 'testo': azione_log},
                {'data': datetime.now().strftime('%H:%M'), 'autore': 'Master', 'testo': master_res}
            ])
            
            conn.update(worksheet='messaggi', data=pd.concat([df_m, nuovi_msg], ignore_index=True))
            st.cache_data.clear()
            st.rerun()
            
        except Exception as e:
            st.error(f"L'oscurità ha bloccato il Master: {e}")
