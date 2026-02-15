import streamlit as st
from groq import Groq
from streamlit_gsheets import GSheetsConnection
from streamlit_autorefresh import st_autorefresh
import pandas as pd
from datetime import datetime
import random
import re

# Configurazione Pagina
st.set_page_config(page_title='Apocrypha Chronicles', layout='wide')


# Inizializzazione API
if 'GROQ_API_KEY' not in st.secrets:
    st.error("Manca la chiave GROQ_API_KEY nei Secrets!")
    st.stop()

client = Groq(api_key=st.secrets['GROQ_API_KEY'])
conn = st.connection('gsheets', type=GSheetsConnection)

# Sincronizzazione Multiplayer (15s)
st_autorefresh(interval=15000, key='multi_sync')

if 'auth' not in st.session_state:
    st.session_state.auth = False

# --- LOGIN ---
if not st.session_state.auth:
    st.title('🌑 APOCRYPHA')
    u = st.text_input('Username')
    p = st.text_input('Password', type='password')
    if st.button('Entra'):
        if p == 'apocrypha2026' and u:
            st.session_state.auth = True
            st.session_state.user = u
            st.rerun()
    st.stop()

# --- DATI ---
df_p = conn.read(worksheet='personaggi', ttl=0)
df_m = conn.read(worksheet='messaggi', ttl=0)
user_pg = df_p[df_p['username'] == st.session_state.user]

# --- SIDEBAR ---
with st.sidebar:
    st.title('🛡️ IL TUO EROE')
    if user_pg.empty:
        with st.expander("✨ Crea Eroe"):
            nome = st.text_input('Nome')
            rz = st.selectbox('Razza', ['Fenrithar', 'Elling', 'Elpide', 'Minotauro', 'Narun', 'Feyrin', 'Primaris', 'Inferis'])
            cl = st.selectbox('Classe', ['Orrenai', 'Armagister', 'Mago'])
            if st.button('Crea'):
                new = pd.DataFrame([{'username': st.session_state.user, 'nome_pg': nome, 'razza': rz, 'classe': cl, 'hp': 100}])
                conn.update(worksheet='personaggi', data=pd.concat([df_p, new], ignore_index=True))
                st.rerun()
    else:
        pg = user_pg.iloc[0]
        st.subheader(f"👤 {pg['nome_pg']}")
        st.caption(f"{pg['razza']} • {pg['classe']}")
        hp_v = int(pg['hp'])
        st.write(f"❤️ HP: {hp_v}/100")
        st.progress(max(0, min(100, hp_v)) / 100)
        
        st.divider()
        st.markdown("**Compagni Online:**")
        for _, r in df_p[df_p['username'] != st.session_state.user].iterrows():
            st.caption(f"🔸 {r['nome_pg']} ({r['hp']} HP)")

# --- CHAT ---
st.title('📜 Cronaca dell Abisso')
for _, r in df_m.tail(15).iterrows():
    role = 'assistant' if r['autore'] == 'Master' else 'user'
    with st.chat_message(role):
        st.markdown(f"**{r['autore']}**: {r['testo']}")

# --- AZIONE ---
if not user_pg.empty:
    if act := st.chat_input('Cosa fai?'):
        pg_n = pg['nome_pg']
        msg_u = f"{act} [d20: {random.randint(1, 20)}]"
        
        with st.spinner('Il Master narra...'):
            try:
                storia = "\n".join([f"{r['autore']}: {r['testo']}" for _, r in df_m.tail(3).iterrows()])
                res = client.chat.completions.create(
                    messages=[{"role": "system", "content": "Master GDR Dark. Sii breve. Danni: 'DANNI: X'."},
                              {"role": "user", "content": f"{storia}\n{pg_n}: {msg_u}"}],
                    model="llama-3.3-70b-versatile"
                ).choices[0].message.content

                # Danni
                dmg = re.search(r"DANNI:\s*(\d+)", res)
                if dmg:
                    df_p.loc[df_p['username'] == st.session_state.user, 'hp'] = max(0, int(pg['hp']) - int(dmg.group(1)))
                    conn.update(worksheet='personaggi', data=df_p)

                # Update cronaca
                new_m = pd.DataFrame([{'data': datetime.now().strftime('%H:%M'), 'autore': pg_n, 'testo': msg_u},
                                     {'data': datetime.now().strftime('%H:%M'), 'autore': 'Master', 'testo': res}])
                conn.update(worksheet='messaggi', data=pd.concat([df_m, new_m], ignore_index=True))
                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                st.error(f"Errore: {e}")
