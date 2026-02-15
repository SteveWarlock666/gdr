import streamlit as st
from groq import Groq
from streamlit_gsheets import GSheetsConnection
from streamlit_autorefresh import st_autorefresh
import pandas as pd
from datetime import datetime, timedelta
import random
import re

st.set_page_config(page_title='Apocrypha Master', layout='wide')

if 'GROQ_API_KEY' not in st.secrets:
    st.error("Manca la chiave!")
    st.stop()

client = Groq(api_key=st.secrets['GROQ_API_KEY'])
conn = st.connection('gsheets', type=GSheetsConnection)
st_autorefresh(interval=15000, key='global_sync')

if 'auth' not in st.session_state:
    st.session_state.auth = False

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

try:
    df_p = conn.read(worksheet='personaggi', ttl=0).fillna('')
    df_m = conn.read(worksheet='messaggi', ttl=0).fillna('')
except Exception as e:
    st.error("Errore fogli Google")
    st.stop()

user_pg_df = df_p[df_p['username'].astype(str) == str(st.session_state.user)]

with st.sidebar:
    st.header('🛡️ IL TUO EROE')
    
    if user_pg_df.empty:
        with st.expander("✨ Risveglio"):
            n_pg = st.text_input('Nome PG')
            rz = st.selectbox('Razza', ['Fenrithar', 'Elling', 'Elpide', 'Minotauro', 'Narun', 'Feyrin', 'Primaris', 'Inferis'])
            cl = st.selectbox('Classe', ['Orrenai', 'Armagister', 'Mago'])
            if st.button('Crea'):
                if n_pg:
                    new = pd.DataFrame([{'username': st.session_state.user, 'nome_pg': n_pg, 'razza': rz, 'classe': cl, 'hp': 20, 'ultimo_visto': datetime.now().strftime('%Y-%m-%d %H:%M:%S')}])
                    conn.update(worksheet='personaggi', data=pd.concat([df_p, new], ignore_index=True))
                    st.cache_data.clear()
                    st.rerun()
    else:
        pg = user_pg_df.iloc[0]
        with st.container(border=True):
            st.subheader(f"👤 {pg['nome_pg']}")
            st.caption(f"{pg['razza']} • {pg['classe']}")
            hp_val = int(pg['hp'])
            st.write(f"❤️ Salute: {hp_val}/20")
            st.progress(max(0, min(20, hp_val)) / 20)
        
        st.divider()
        st.write("👥 Compagni:")
        for _, r in df_p.iterrows():
            if r['username'] != st.session_state.user:
                try:
                    last_seen = datetime.strptime(str(r['ultimo_visto']), '%Y-%m-%d %H:%M:%S')
                    is_online = datetime.now() - last_seen < timedelta(minutes=10)
                except:
                    is_online = False
                
                status = "🟢" if is_online else "⚪"
                with st.container(border=True):
                    st.markdown(f"**{status} {r['nome_pg']}**")
                    st.markdown(f"<small>{r['razza']} • {r['classe']}</small>", unsafe_allow_html=True)
                    st.caption(f"Salute: {r['hp']}/20")

st.title('📜 Cronaca dell Abisso')
for _, r in df_m.tail(15).iterrows():
    with st.chat_message("assistant" if r['autore'] == 'Master' else "user"):
        st.write(f"**{r['autore']}**: {r['testo']}")

if not user_pg_df.empty:
    if act := st.chat_input('Cosa fai?'):
        nome_mio = pg['nome_pg']
        d20 = random.randint(1, 20)
        
        with st.spinner('Il Master narra...'):
            try:
                storia = "\n".join([f"{r['autore']}: {r['testo']}" for _, r in df_m.tail(4).iterrows()])
                prompt = f"Contesto: {storia}\nGiocatore {nome_mio} tenta: {act}\nd20: {d20}\nNarra brevemente. Se subisce danni, scrivi DANNI: X alla fine (max 20 HP)."
                
                res = client.chat.completions.create(
                    messages=[{"role": "system", "content": "Sei un Master dark fantasy."}, {"role": "user", "content": prompt}],
                    model="llama-3.3-70b-versatile"
                )
                res_txt = res.choices[0].message.content

                dmg = re.search(r"DANNI:\s*(\d+)", res_txt)
                new_hp = int(pg['hp'])
                if dmg:
                    new_hp = max(0, new_hp - int(dmg.group(1)))
                
                df_p.loc[df_p['username'] == st.session_state.user, 'hp'] = new_hp
                df_p.loc[df_p['username'] == st.session_state.user, 'ultimo_visto'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                conn.update(worksheet='personaggi', data=df_p)

                new_m = pd.concat([df_m, pd.DataFrame([
                    {'data': datetime.now().strftime('%H:%M'), 'autore': nome_mio, 'testo': act},
                    {'data': datetime.now().strftime('%H:%M'), 'autore': 'Master', 'testo': res_txt}
                ])], ignore_index=True)
                conn.update(worksheet='messaggi', data=new_m)
                
                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                st.error(f"Errore: {e}")
