import streamlit as st
from groq import Groq
from streamlit_gsheets import GSheetsConnection
from streamlit_autorefresh import st_autorefresh
import pandas as pd
from datetime import datetime
import random
import re

# Configurazione Grafica Dark
st.set_page_config(page_title='Apocrypha Chronicles', layout='wide')

st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stChatMessage { border: 1px solid #30363d; border-radius: 8px; background-color: #161b22; }
    .stSidebar { background-color: #161b22; border-right: 1px solid #30363d; }
    h1, h2, h3 { color: #e6edf3; }
    .stProgress > div > div > div > div { background-color: #da3633; }
    </style>
""", unsafe_allow_html=True)

# Inizializzazione API e Connessione
if 'GROQ_API_KEY' not in st.secrets:
    st.error("Inserisci la chiave GROQ_API_KEY nei Secrets di Streamlit!")
    st.stop()

client = Groq(api_key=st.secrets['GROQ_API_KEY'])
conn = st.connection('gsheets', type=GSheetsConnection)

# Sincronizzazione Multiplayer (aggiorna ogni 15 secondi)
st_autorefresh(interval=15000, key='multiplayer_sync')

if 'auth' not in st.session_state:
    st.session_state.auth = False

# --- FASE 1: LOGIN ---
if not st.session_state.auth:
    st.title('🌑 BENVENUTO IN APOCRYPHA')
    col1, col2 = st.columns(2)
    with col1:
        u = st.text_input('Username')
        p = st.text_input('Password', type='password')
        if st.button('Entra nell Abisso'):
            if p == 'apocrypha2026' and u:
                st.session_state.auth = True
                st.session_state.user = u
                st.rerun()
    st.stop()

# --- FASE 2: CARICAMENTO DATI ---
df_p = conn.read(worksheet='personaggi', ttl=0)
df_m = conn.read(worksheet='messaggi', ttl=0)

# Controllo se l'utente ha un personaggio
user_data = df_p[df_p['username'] == st.session_state.user]

# --- SIDEBAR: SCHEDA PERSONAGGIO ---
with st.sidebar:
    st.title('🛡️ IL TUO EROE')
    
    if user_data.empty:
        st.warning("Non hai ancora un personaggio!")
        with st.expander("✨ Crea Eroe"):
            nome = st.text_input('Nome PG')
            razza = st.selectbox('Razza', ['Fenrithar', 'Elling', 'Elpide', 'Minotauro', 'Narun', 'Feyrin', 'Primaris', 'Inferis'])
            classe = st.selectbox('Classe', ['Orrenai', 'Armagister', 'Mago'])
            if st.button('Risvegliati'):
                if nome:
                    new_pg = pd.DataFrame([{
                        'username': st.session_state.user, 
                        'nome_pg': nome, 
                        'razza': razza, 
                        'classe': classe, 
                        'hp': 100
                    }])
                    conn.update(worksheet='personaggi', data=pd.concat([df_p, new_pg], ignore_index=True))
                    st.rerun()
    else:
        pg = user_data.iloc[0]
        st.subheader(f"👤 {pg['nome_pg']}")
        st.caption(f"{pg['razza']} • {pg['classe']}")
        
        hp_attuali = int(pg['hp'])
        st.write(f"❤️ Salute: {hp_attuali}/100")
        st.progress(max(0, min(100, hp_attuali)) / 100)
        
        st.divider()
        st.markdown("**Compagni Online:**")
        altri_pg = df_p[df_p['username'] != st.session_state.user]
        for _, r in altri_pg.iterrows():
            st.caption(f"🔸 {r['nome_pg']} ({r['hp']} HP)")

# --- AREA GIOCO: CRONACA ---
st.title('📜 Cronaca dell Abisso')

# Mostra gli ultimi 15 messaggi per non intasare
for _, r in df_m.tail(15).iterrows():
    role = 'assistant' if r['autore'] == 'Master' else 'user'
    with st.chat_message(role):
        st.markdown(f"**{r['autore']}**: {r['testo']}")

# --- INPUT AZIONE ---
if not user_data.empty:
    if act := st.chat_input('Cosa fai?'):
        pg_n = user_data.iloc[0]['nome_pg']
        hp_n = int(user_data.iloc[0]['hp'])
        d20 = random.randint(1, 20)
        azione_utente = f"{act} [d20: {d20}]"
        
        with st.spinner('Il Master narra...'):
            try:
                # Memoria Multiplayer: legge gli ultimi messaggi per coerenza
                storia = "\n".join([f"{r['autore']}: {r['testo']}" for _, r in df_m.tail(5).iterrows()])
                
                prompt = f"Sei il Master di Apocrypha. Narra l'esito: {pg_n} fa {azione_utente}. Sii breve. Se subisce danni scrivi 'DANNI: X' alla fine."
                
                chat = client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": "GDR Dark Fantasy spietato."},
                        {"role": "user", "content": f"Storia recente:\n{storia}\n\nAzione attuale: {azione_utente}"}
                    ],
                    model="llama-3.3-70b-versatile",
                )
                res_master = chat.choices[0].message.content

                # Calcolo Danni Automatico
                dmg_match = re.search(r"DANNI:\s*(\d+)", res_master)
                if dmg_match:
                    danno = int(dmg_match.group(1))
                    df_p.loc[df_p['username'] == st.session_state.user, 'hp'] = max(0, hp_n - danno)
                    conn.update(worksheet='personaggi', data=df_p)

                # Aggiornamento Cronaca
                nuovi_msg = pd.DataFrame([
                    {'data': datetime.now().strftime('%H:%M'), 'autore': pg_n, 'testo': azione_utente},
                    {'data': datetime.now().strftime('%H:%M'), 'autore': 'Master', 'testo': res_master}
                ])
                conn.update(worksheet='messaggi', data=pd.concat([df_m, nuovi_msg], ignore_index=True))
                
                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                st.error(f"Errore: {e}")
