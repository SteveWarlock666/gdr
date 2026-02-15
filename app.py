import streamlit as st
from google import genai
from streamlit_gsheets import GSheetsConnection
from streamlit_autorefresh import st_autorefresh
import pandas as pd
from datetime import datetime
import random

st.set_page_config(page_title='Apocrypha Master', layout='wide')

# 1. Inizializzazione Client
if "GEMINI_API_KEY" not in st.secrets:
    st.error("Manca la chiave GEMINI_API_KEY nei Secrets!")
    st.stop()

client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

# 2. Connessione Fogli e Refresh (15 secondi)
conn = st.connection('gsheets', type=GSheetsConnection)
st_autorefresh(interval=15000, key='refresh_cronaca')

if 'auth' not in st.session_state:
    st.session_state.auth = False

# 3. Login
if not st.session_state.auth:
    st.title("Accedi all'Abisso")
    u = st.text_input('Username')
    p = st.text_input('Password', type='password')
    if st.button('Entra'):
        if p == 'apocrypha2026' and u:
            st.session_state.auth = True
            st.session_state.user = u
            st.rerun()
    st.stop()

# 4. Caricamento Dati
try:
    df_p = conn.read(worksheet='personaggi', ttl=0)
    df_m = conn.read(worksheet='messaggi', ttl=0)
except Exception as e:
    st.error(f"Errore caricamento Google Sheets: {e}")
    st.stop()

# 5. Sidebar Eroi
with st.sidebar:
    st.title('🛡️ EROI')
    for _, r in df_p.iterrows():
        with st.container(border=True):
            st.markdown(f"**{r['nome_pg']}**")
            st.caption(f"{r['razza']} - HP: {r['hp']}/100")
            st.progress(max(0, min(100, int(r['hp']))) / 100)
    
    if st.session_state.user not in df_p['username'].values.astype(str):
        with st.expander("Crea il tuo Eroe"):
            n = st.text_input('Nome Personaggio')
            if st.button('Risvegliati'):
                if n:
                    new_pg = pd.DataFrame([{'username': st.session_state.user, 'nome_pg': n, 'razza': 'Umano', 'classe': 'Viandante', 'hp': 100}])
                    conn.update(worksheet='personaggi', data=pd.concat([df_p, new_pg], ignore_index=True))
                    st.success("Personaggio creato!")
                    st.rerun()

# 6. Chat / Cronaca
st.title('📜 Cronaca dell Abisso')
for _, r in df_m.tail(20).iterrows():
    role = 'assistant' if r['autore'] == 'Master' else 'user'
    with st.chat_message(role):
        st.write(f"**{r['autore']}**: {r['testo']}")

# 7. Invio Azione
if act := st.chat_input('Cosa fai?'):
    # Recupera nome PG
    user_pgs = df_p[df_p['username'] == st.session_state.user]
    if user_pgs.empty:
        st.warning("Crea prima un personaggio nella barra laterale!")
        st.stop()
    
    pg_nome = user_pgs.iloc[0]['nome_pg']
    d20 = random.randint(1, 20)
    azione_completa = f"{act} [d20: {d20}]"
    
    with st.spinner("Il Master sta scrivendo il tuo destino..."):
        prompt = f"Sei il Master di Apocrypha. Narra l'esito di questa azione: {pg_nome} fa {azione_completa}. Sii breve, cupo e brutale."
        
        try:
            # Tenta i modelli in ordine di stabilità
            success = False
            for model_name in ['gemini-1.5-flash', 'gemini-1.5-flash-8b', 'gemini-1.5-pro']:
                try:
                    response = client.models.generate_content(model=model_name, contents=prompt)
                    res_text = response.text
                    success = True
                    break
                except:
                    continue
            
            if success:
                # Salva su Google Sheets
                new_entry = pd.DataFrame([
                    {'data': datetime.now().strftime('%H:%M'), 'autore': pg_nome, 'testo': azione_completa},
                    {'data': datetime.now().strftime('%H:%M'), 'autore': 'Master', 'testo': res_text}
                ])
                updated_df = pd.concat([df_m, new_entry], ignore_index=True)
                conn.update(worksheet='messaggi', data=updated_df)
                st.rerun()
            else:
                st.error("Google non risponde. Controlla la tua API Key o i limiti di quota.")
                
        except Exception as e:
            st.error(f"Errore fatale: {e}")
