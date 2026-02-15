import streamlit as st
from groq import Groq
from streamlit_gsheets import GSheetsConnection
from streamlit_autorefresh import st_autorefresh
import pandas as pd
from datetime import datetime
import random
import re

# Configurazione base senza CSS iniettato manualmente che sporca la UI
st.set_page_config(page_title='Apocrypha', layout='wide')

if 'GROQ_API_KEY' not in st.secrets:
    st.error("Manca la chiave!")
    st.stop()

client = Groq(api_key=st.secrets['GROQ_API_KEY'])
conn = st.connection('gsheets', type=GSheetsConnection)
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

# --- CARICAMENTO DATI ---
df_p = conn.read(worksheet='personaggi', ttl=0)
df_m = conn.read(worksheet='messaggi', ttl=0)
user_pg = df_p[df_p['username'] == st.session_state.user]

# --- SIDEBAR PULITA ---
with st.sidebar:
    st.header('🛡️ IL TUO EROE')
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
        st.subheader(pg['nome_pg'])
        st.info(f"{pg['razza']} • {pg['classe']}")
        hp_v = int(pg['hp'])
        st.write(f"❤️ HP: {hp_v}/100")
        st.progress(max(0, min(100, hp_v)) / 100)
        
        st.divider()
        st.write("👥 Compagni:")
        for _, r in df_p[df_p['username'] != st.session_state.user].iterrows():
            st.text(f"🔸 {r['nome_pg']} ({r['hp']} HP)")

# --- CRONACA ---
st.title('📜 Cronaca dell Abisso')
# Visualizziamo i messaggi senza fronzoli che causano bug
for _, r in df_m.tail(15).iterrows():
    role = 'assistant' if r['autore'] == 'Master' else 'user'
    with st.chat_message(role):
        st.write(f"**{r['autore']}**: {r['testo']}")

# --- AZIONE ---
if not user_pg.empty:
    if act := st.chat_input('Cosa fai?'):
        pg_n = pg['nome_pg']
        d20_secret = random.randint(1, 20)
        
        with st.spinner('Il Master narra...'):
            try:
                # Prendiamo un minimo di contesto per la coerenza
                context = "\n".join([f"{r['autore']}: {r['testo']}" for _, r in df_m.tail(3).iterrows()])
                
                prompt = f"""Contesto: {context}
                Giocatore: {pg_n} tenta: {act}
                Risultato d20 segreto: {d20_secret}
                Narra l'esito brevemente. Non mostrare il numero del dado.
                Se ci sono danni, scrivi 'DANNI: X' alla fine."""

                res = client.chat.completions.create(
                    messages=[{"role": "system", "content": "Sei un Master dark fantasy."},
                              {"role": "user", "content": prompt}],
                    model="llama-3.3-70b-versatile"
                ).choices[0].message.content

                # Logica Danni
                dmg_find = re.search(r"DANNI:\s*(\d+)", res)
                if dmg_find:
                    new_hp = max(0, int(pg['hp']) - int(dmg_find.group(1)))
                    df_p.loc[df_p['username'] == st.session_state.user, 'hp'] = new_hp
                    conn.update(worksheet='personaggi', data=df_p)

                # Salvataggio messaggi puliti
                new_m = pd.DataFrame([
                    {'data': datetime.now().strftime('%H:%M'), 'autore': pg_n, 'testo': act},
                    {'data': datetime.now().strftime('%H:%M'), 'autore': 'Master', 'testo': res}
                ])
                conn.update(worksheet='messaggi', data=pd.concat([df_m, new_m], ignore_index=True))
                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                st.error(f"Errore: {e}")
