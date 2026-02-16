import streamlit as st
from groq import Groq
from streamlit_gsheets import GSheetsConnection
from streamlit_autorefresh import st_autorefresh
import pandas as pd
from datetime import datetime, timedelta
import re
import time

st.set_page_config(page_title='Apocrypha Master', layout='wide')

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; }
    div[data-testid="stSidebarUserContent"] { padding-top: 1rem; }
    .compact-row { display: flex; align-items: center; gap: 10px; margin-bottom: 4px; }
    .compact-label { font-size: 12px !important; min-width: 75px; margin: 0 !important; white-space: nowrap; }
    .stProgress { height: 6px !important; flex-grow: 1; }
    #hp-bar .stProgress div[role="progressbar"] > div { background-color: #ff4b4b !important; }
    #mana-bar .stProgress div[role="progressbar"] > div { background-color: #00f2ff !important; }
    #stamina-bar .stProgress div[role="progressbar"] > div { background-color: #00ff88 !important; }
    #xp-bar .stProgress div[role="progressbar"] > div { background-color: #ffffff !important; }
    div[data-testid="stVerticalBlock"] > div { padding-bottom: 0px !important; margin-bottom: 0px !important; }
    </style>
""", unsafe_allow_html=True)

if 'GROQ_API_KEY' not in st.secrets:
    st.error("Manca la chiave!")
    st.stop()

client = Groq(api_key=st.secrets['GROQ_API_KEY'])
conn = st.connection('gsheets', type=GSheetsConnection)
st_autorefresh(interval=30000, key='global_sync')

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
    for col in ['mana', 'vigore', 'xp', 'lvl', 'ultimo_visto', 'posizione']:
        if col not in df_p.columns:
            df_p[col] = 0 if col != 'posizione' else 'Strada per Gauvadon'
    df_p = df_p.fillna(0)
    df_m = conn.read(worksheet='messaggi', ttl=0).fillna('')
    df_a = conn.read(worksheet='abilita', ttl=0).fillna('')
except Exception as e:
    st.error(f"Errore caricamento: {e}")
    st.stop()

user_pg_df = df_p[df_p['username'].astype(str) == str(st.session_state.user)]

with st.sidebar:
    st.header('🛡️ SCHEDA EROE')
    if not user_pg_df.empty:
        pg = user_pg_df.iloc[0]
        nome_pg = pg['nome_pg']
        with st.container(border=True):
            st.markdown(f"**{nome_pg} (Lv. {int(pg['lvl'])})**")
            st.caption(f"📍 {pg['posizione']}")
            st.caption(f"{pg['razza']} • {pg['classe']}")
            st.markdown(f'<div class="compact-row" id="hp-bar"><p class="compact-label">❤️ HP: {int(pg["hp"])}/20</p>', unsafe_allow_html=True)
            st.progress(max(0.0, min(1.0, int(pg['hp']) / 20)))
            st.markdown('</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="compact-row" id="mana-bar"><p class="compact-label">✨ MN: {int(pg["mana"])}/20</p>', unsafe_allow_html=True)
            st.progress(max(0.0, min(1.0, int(pg['mana']) / 20)))
            st.markdown('</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="compact-row" id="stamina-bar"><p class="compact-label">⚡ VG: {int(pg["vigore"])}/20</p>', unsafe_allow_html=True)
            st.progress(max(0.0, min(1.0, int(pg['vigore']) / 20)))
            st.markdown('</div>', unsafe_allow_html=True)
            st.divider()
            cur_lvl, cur_xp = int(pg['lvl']), int(pg['xp'])
            next_xp = XP_LEVELS.get(cur_lvl + 1, 99999)
            st.markdown(f'<div class="compact-row" id="xp-bar"><p class="compact-label">📖 XP: {cur_xp}/{next_xp}</p>', unsafe_allow_html=True)
            st.progress(max(0.0, min(1.0, cur_xp / next_xp)))
            st.markdown('</div>', unsafe_allow_html=True)
        
        st.write("📜 Abilità:")
        mie_abi = df_a[df_a['proprietario'] == nome_pg]
        for _, abi in mie_abi.iterrows():
            with st.container(border=True):
                st.markdown(f"<p style='font-size:12px; margin:0;'>**{abi['nome']}**</p>", unsafe_allow_html=True)
                st.caption(f"{abi['tipo']} • 🧪 Costo: {abi['costo']} • 🎲 {abi['dadi']}")

        st.divider()
        st.write("👥 Compagni:")
        compagni = df_p[df_p['username'].astype(str) != str(st.session_state.user)]
        for _, c in compagni.iterrows():
            with st.container(border=True):
                try:
                    ultimo_visto = datetime.strptime(str(c['ultimo_visto']), '%Y-%m-%d %H:%M:%S')
                    status = "🟢" if (datetime.now() - ultimo_visto) < timedelta(minutes=10) else ""
                    time_str = "" if status else f"Ultima attività: {ultimo_visto.strftime('%H:%M')}"
                except: status, time_str = "", "Offline"
                st.markdown(f"**{c['nome_pg']}** {status}")
                st.caption(f"Liv. {int(c['lvl'])} • {c['razza']} {c['classe']}")
                if time_str: st.caption(time_str)
                st.progress(max(0.0, min(1.0, int(c['hp']) / 20)))

st.title('📜 Cronaca dell Abisso')
for _, r in df_m.tail(15).iterrows():
    with st.chat_message("assistant" if r['autore'] == 'Master' else "user"):
        st.write(f"**{r['autore']}**: {r['testo']}")

if not user_pg_df.empty:
    if act := st.chat_input('Cosa fai?'):
        nome_mio = pg['nome_pg']
        with st.spinner('Il Master narra...'):
            try:
                storia = "\n".join([f"{r['autore']}: {r['testo']}" for _, r in df_m.tail(5).iterrows()])
                abi_info = "\n".join([f"- {a['nome']}: {a['descrizione']} (Costo: {a['costo']}, Tipo: {a['tipo']}, Dadi: {a['dadi']})" for _, a in mie_abi.iterrows()])
                
                sys_msg = f"""Sei il Master di un GDR dark fantasy. Giocatore: {nome_mio}.
                REGOLE TASSATIVE:
                1. Se DANNI_RICEVUTI > 0, DEVI descrivere nel testo narrativo come il nemico attacca e ferisce Caelum.
                2. COSTI: Se l'abilità usata è di tipo 'Vigore', sottrai SOLO Vigore. Se è di tipo 'Mana', sottrai SOLO Mana. Attacco base sottrae sempre 1 Vigore. MAI scalare entrambi se non richiesto esplicitamente.
                3. DANNI AL NEMICO: Base d20 (11-14=1, 15-19=2, 20=3). Abilità d20 + 1d4 mutatore.
                4. NON scrivere mai dadi o calcoli nel testo.
                5. TAG OBBLIGATORI (SOLO VALORI DELL'AZIONE CORRENTE):
                DANNI_NEMICO: X
                DANNI_RICEVUTI: X
                MANA_USATO: X
                VIGORE_USATO: X
                XP: X
                LUOGO: {pg['posizione']}"""
                
                res = client.chat.completions.create(messages=[{"role": "system", "content": sys_msg}, {"role": "user", "content": f"Contesto: {storia}\nAbilità: {abi_info}\nAzione: {act}"}], model="llama-3.3-70b-versatile").choices[0].message.content
                
                def get_tag(tag, text):
                    match = re.search(f"{tag}:\\s*(\\d+)", text)
                    return int(match.group(1)) if match else 0

                val_ric = get_tag("DANNI_RICEVUTI", res)
                val_mn = get_tag("MANA_USATO", res)
                val_vg = get_tag("VIGORE_USATO", res)
                val_xp = get_tag("XP", res)
                
                n_hp = max(0, int(pg['hp']) - val_ric)
                n_mn = max(0, int(pg['mana']) - val_mn)
                n_vg = max(0, int(pg['vigore']) - val_vg)
                
                if val_xp > 0:
                    df_p.loc[df_p['posizione'] == pg['posizione'], 'xp'] += val_xp

                df_p.loc[df_p['username'] == st.session_state.user, ['hp', 'mana', 'vigore', 'ultimo_visto']] = [n_hp, n_mn, n_vg, datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
                conn.update(worksheet='personaggi', data=df_p)
                new_m = pd.concat([df_m, pd.DataFrame([{'data': datetime.now().strftime('%H:%M'), 'autore': nome_mio, 'testo': act}, {'data': datetime.now().strftime('%H:%M'), 'autore': 'Master', 'testo': res}])], ignore_index=True)
                conn.update(worksheet='messaggi', data=new_m)
                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                st.error(f"Errore: {e}")
