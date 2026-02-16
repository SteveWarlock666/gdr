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

XP_LEVELS = {1: 0, 2: 300, 3: 900, 4: 2700, 5: 6500}

try:
    df_p = conn.read(worksheet='personaggi', ttl=0)
    for col in ['mana', 'vigore', 'xp', 'lvl', 'ultimo_visto']:
        if col not in df_p.columns:
            df_p[col] = 0 if col != 'lvl' else 1
    df_p = df_p.fillna(0)
    df_m = conn.read(worksheet='messaggi', ttl=0).fillna('')
    df_a = conn.read(worksheet='abilita', ttl=0).fillna('')
except Exception as e:
    st.error(f"Errore caricamento dati: {e}")
    st.stop()

user_pg_df = df_p[df_p['username'].astype(str) == str(st.session_state.user)]

with st.sidebar:
    st.header('🛡️ SCHEDA EROE')
    
    if user_pg_df.empty:
        with st.expander("✨ Risveglio"):
            n_pg = st.text_input('Nome PG')
            rz = st.selectbox('Razza', ['Fenrithar', 'Elling', 'Elpide', 'Minotauro', 'Narun', 'Feyrin', 'Primaris', 'Inferis'])
            cl = st.selectbox('Classe', ['Orrenai', 'Armagister', 'Mago'])
            if st.button('Crea'):
                if n_pg:
                    new = pd.DataFrame([{
                        'username': st.session_state.user, 'nome_pg': n_pg, 'razza': rz, 'classe': cl, 
                        'hp': 20, 'mana': 20, 'vigore': 20, 'xp': 0, 'lvl': 1,
                        'ultimo_visto': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }])
                    conn.update(worksheet='personaggi', data=pd.concat([df_p, new], ignore_index=True))
                    st.cache_data.clear()
                    st.rerun()
    else:
        pg = user_pg_df.iloc[0]
        nome_pg = pg['nome_pg']
        
        with st.container(border=True):
            st.subheader(f"{nome_pg} (Lv. {int(pg['lvl'])})")
            st.caption(f"{pg['razza']} • {pg['classe']}")
            
            st.write(f"❤️ HP: {int(pg['hp'])}/20")
            st.progress(max(0.0, min(1.0, int(pg['hp']) / 20)))
            
            c_res = st.columns(2)
            c_res[0].write(f"✨ MN: {int(pg['mana'])}")
            c_res[1].write(f"⚡ VG: {int(pg['vigore'])}")
            
            cur_lvl = int(pg['lvl'])
            next_xp = XP_LEVELS.get(cur_lvl + 1, 99999)
            cur_xp = int(pg['xp'])
            st.write(f"📖 XP: {cur_xp}/{next_xp}")
            st.progress(max(0.0, min(1.0, cur_xp / next_xp)))

        st.write("📜 Abilità Disponibili:")
        mie_abi = df_a[df_a['proprietario'] == nome_pg]
        for _, abi in mie_abi.iterrows():
            with st.container(border=True):
                st.markdown(f"**{abi['nome']}**")
                st.caption(f"{abi['tipo']} • 🧪 {abi['costo']} • 🎲 {abi['dadi']}")
                st.markdown(f"<small>{abi['descrizione']}</small>", unsafe_allow_html=True)

        st.divider()
        st.write("👥 Compagni:")
        for _, r in df_p.iterrows():
            if r['username'] != st.session_state.user:
                try:
                    ls = datetime.strptime(str(r['ultimo_visto']), '%Y-%m-%d %H:%M:%S')
                    on = datetime.now() - ls < timedelta(minutes=10)
                except:
                    on = False
                st_icon = "🟢" if on else "⚪"
                with st.container(border=True):
                    st.markdown(f"**{st_icon} {r['nome_pg']}** (Lv.{int(r['lvl'])})")
                    st.caption(f"HP: {int(r['hp'])}/20")

st.title('📜 Cronaca dell Abisso')
for _, r in df_m.tail(15).iterrows():
    with st.chat_message("assistant" if r['autore'] == 'Master' else "user"):
        st.write(f"**{r['autore']}**: {r['testo']}")

if not user_pg_df.empty:
    if act := st.chat_input('Cosa fai?'):
        nome_mio = pg['nome_pg']
        with st.spinner('Il Master lancia i dadi...'):
            try:
                storia = "\n".join([f"{r['autore']}: {r['testo']}" for _, r in df_m.tail(4).iterrows()])
                dettagli_abi = "\n".join([f"- {a['nome']}: {a['descrizione']} (Costo: {a['costo']}, Dadi: {a['dadi']})" for _, a in mie_abi.iterrows()])
                
                sys_msg = f"""Sei un Master dark fantasy.
                Regolamento dadi: d4, d6, d8, d10, d12, d20.
                Abilità di {nome_mio}:
                {dettagli_abi}
                
                REGOLE:
                1. Se il giocatore usa un'abilità, simula il tiro del dado specificato (es. 2d6) + d20 per il successo.
                2. Sottrai il costo (Mana/Vigore).
                3. Narra l'esito in modo brutale senza mostrare i numeri dei dadi.
                4. Tag obbligatori se variano: DANNI: X, MANA_USATO: X, VIGORE_USATO: X, XP: X."""
                
                prompt = f"Contesto: {storia}\nGiocatore {nome_mio} tenta: {act}"
                
                res = client.chat.completions.create(
                    messages=[{"role": "system", "content": sys_msg}, {"role": "user", "content": prompt}],
                    model="llama-3.3-70b-versatile"
                ).choices[0].message.content

                d_hp = re.search(r"DANNI:\s*(\d+)", res)
                d_mn = re.search(r"MANA_USATO:\s*(\d+)", res)
                d_vg = re.search(r"VIGORE_USATO:\s*(\d+)", res)
                d_xp = re.search(r"XP:\s*(\d+)", res)
                
                n_hp = max(0, int(pg['hp']) - (int(d_hp.group(1)) if d_hp else 0))
                n_mn = max(0, int(pg['mana']) - (int(d_mn.group(1)) if d_mn else 0))
                n_vg = max(0, int(pg['vigore']) - (int(d_vg.group(1)) if d_vg else 0))
                n_xp = int(pg['xp']) + (int(d_xp.group(1)) if d_xp else 0)
                n_lvl = int(pg['lvl'])
                if n_xp >= XP_LEVELS.get(n_lvl + 1, 99999): n_lvl += 1

                df_p.loc[df_p['username'] == st.session_state.user, ['hp', 'mana', 'vigore', 'xp', 'lvl', 'ultimo_visto']] = [n_hp, n_mn, n_vg, n_xp, n_lvl, datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
                conn.update(worksheet='personaggi', data=df_p)

                new_m = pd.concat([df_m, pd.DataFrame([{'data': datetime.now().strftime('%H:%M'), 'autore': nome_mio, 'testo': act}, {'data': datetime.now().strftime('%H:%M'), 'autore': 'Master', 'testo': res}])], ignore_index=True)
                conn.update(worksheet='messaggi', data=new_m)
                
                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                st.error(f"Errore: {e}")
