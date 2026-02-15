import streamlit as st
from groq import Groq
from streamlit_gsheets import GSheetsConnection
from streamlit_autorefresh import st_autorefresh
import pandas as pd
from datetime import datetime
import random
import re

st.set_page_config(page_title='Apocrypha Master', layout='wide')

# Controllo API Key
if 'GROQ_API_KEY' not in st.secrets:
    st.error("Manca la chiave GROQ_API_KEY nei Secrets!")
    st.stop()

client = Groq(api_key=st.secrets['GROQ_API_KEY'])
conn = st.connection('gsheets', type=GSheetsConnection)

# Sincronizzazione ogni 15 secondi per vedere le mosse degli altri
st_autorefresh(interval=15000, key='sync_global')

if 'auth' not in st.session_state:
    st.session_state.auth = False

# --- ACCESSO ---
if not st.session_state.auth:
    st.title('🌑 APOCRYPHA')
    u = st.text_input('Username')
    p = st.text_input('Password', type='password')
    if st.button('Entra'):
        if p == 'apocrypha2026' and u:
            st.session_state.auth = True
            st.session_state.user = u.strip()
            st.rerun()
    st.stop()

# --- CARICAMENTO DATI ---
try:
    df_p = conn.read(worksheet='personaggi', ttl=0).fillna('')
    df_m = conn.read(worksheet='messaggi', ttl=0).fillna('')
except Exception as e:
    st.error(f"Errore connessione fogli: {e}")
    st.stop()

# Filtro rigoroso per l'utente corrente
user_pg_df = df_p[df_p['username'].astype(str) == str(st.session_state.user)]

# --- SIDEBAR: GESTIONE PG ---
with st.sidebar:
    st.header('🛡️ SCHEDA EROE')
    
    if user_pg_df.empty:
        st.warning("Crea il tuo eroe per iniziare.")
        with st.expander("✨ Risveglio"):
            nome_nuovo = st.text_input('Nome PG')
            rz = st.selectbox('Razza', ['Fenrithar', 'Elling', 'Elpide', 'Minotauro', 'Narun', 'Feyrin', 'Primaris', 'Inferis'])
            cl = st.selectbox('Classe', ['Orrenai', 'Armagister', 'Mago'])
            if st.button('Crea Eroe'):
                if nome_nuovo:
                    new_row = pd.DataFrame([{
                        'username': st.session_state.user,
                        'nome_pg': nome_nuovo,
                        'razza': rz,
                        'classe': cl,
                        'hp': 100
                    }])
                    updated_p = pd.concat([df_p, new_row], ignore_index=True)
                    conn.update(worksheet='personaggi', data=updated_p)
                    st.cache_data.clear()
                    st.rerun()
    else:
        pg = user_pg_df.iloc[0]
        st.subheader(f"👤 {pg['nome_pg']}")
        st.info(f"{pg['razza']} • {pg['classe']}")
        hp_val = int(pg['hp'])
        st.write(f"❤️ Salute: {hp_val}/20")
        st.progress(max(0, min(20, hp_val)) / 20)
        
        st.divider()
        st.write("👥 Viandanti nell'Abisso:")
        # Mostra gli altri PG per il multiplayer
        altri = df_p[df_p['username'].astype(str) != str(st.session_state.user)]
        for _, r in altri.iterrows():
            st.text(f"🔸 {r['nome_pg']} ({r['hp']} HP)")

# --- CRONACA ---
st.title('📜 Cronaca dell Abisso')
for _, r in df_m.tail(15).iterrows():
    is_master = (r['autore'] == 'Master')
    with st.chat_message("assistant" if is_master else "user"):
        st.write(f"**{r['autore']}**: {r['testo']}")

# --- AZIONE ---
if not user_pg_df.empty:
    if act := st.chat_input('Cosa fai?'):
        nome_mio = pg['nome_pg']
        d20_segreto = random.randint(1, 20)
        
        with st.spinner('Il Master osserva...'):
            try:
                storia_recente = "\n".join([f"{r['autore']}: {r['testo']}" for _, r in df_m.tail(4).iterrows()])
                
                prompt = f"""Contesto: {storia_recente}
                Giocatore {nome_mio} tenta: {act}
                Risultato d20 segreto: {d20_segreto}
                Narra l'esito brevemente (max 3 frasi). Non citare il numero del dado.
                Se il giocatore subisce danni, termina il messaggio con 'DANNI: X'."""

                chat = client.chat.completions.create(
                    messages=[{"role": "system", "content": "Sei il Master di un GDR dark fantasy."},
                              {"role": "user", "content": prompt}],
                    model="llama-3.3-70b-versatile"
                )
                risposta = chat.choices[0].message.content

                # Calcolo Danni e aggiornamento HP
                dmg_match = re.search(r"DANNI:\s*(\d+)", risposta)
                if dmg_match:
                    danno = int(dmg_match.group(1))
                    # Ricarichiamo df_p per sicurezza prima dell'update
                    df_p.loc[df_p['username'] == st.session_state.user, 'hp'] = max(0, int(pg['hp']) - danno)
                    conn.update(worksheet='personaggi', data=df_p)

                # Salvataggio messaggi
                nuova_cronaca = pd.concat([df_m, pd.DataFrame([
                    {'data': datetime.now().strftime('%H:%M'), 'autore': nome_mio, 'testo': act},
                    {'data': datetime.now().strftime('%H:%M'), 'autore': 'Master', 'testo': risposta}
                ])], ignore_index=True)
                
                conn.update(worksheet='messaggi', data=nuova_cronaca)
                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                st.error(f"Errore Master: {e}")
