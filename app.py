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
st_autorefresh(interval=60000, key='global_sync')

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
    df_p = conn.read(worksheet='personaggi', ttl=10).fillna(0)
    df_m = conn.read(worksheet='messaggi', ttl=10).fillna('')
    df_a = conn.read(worksheet='abilita', ttl=10).fillna('')
    df_n = conn.read(worksheet='nemici', ttl=10).fillna(0)
except:
    st.warning("Server carichi, attendi un istante.")
    st.stop()

user_pg_df = df_p[df_p['username'].astype(str) == str(st.session_state.user)]

if user_pg_df.empty:
    st.title("🛡️ Crea il tuo Eroe")
    with st.form("creazione_pg"):
        n_nuovo = st.text_input("Nome")
        r_nuova = st.selectbox("Razza", ["Umano", "Elfo", "Nano", "Oscuro"])
        c_nuova = st.selectbox("Classe", ["Guerriero", "Mago", "Ladro", "Chierico"])
        if st.form_submit_button("Inizia"):
            nuovo = pd.DataFrame([{"username": st.session_state.user, "nome_pg": n_nuovo, "razza": r_nuova, "classe": c_nuova, "hp": 20, "mana": 20, "vigore": 20, "xp": 0, "lvl": 1, "posizione": "Strada per Gauvadon", "ultimo_visto": datetime.now().strftime('%Y-%m-%d %H:%M:%S')}])
            df_p = pd.concat([df_p, nuovo], ignore_index=True)
            conn.update(worksheet='personaggi', data=df_p)
            st.rerun()
    st.stop()

pg = user_pg_df.iloc[0]
nome_pg = pg['nome_pg']

with st.sidebar:
    st.header('🛡️ SCHEDA EROE')
    with st.container(border=True):
        st.markdown(f"**{nome_pg} (Lv. {int(pg['lvl'])})**")
        st.caption(f"📍 {pg['posizione']}")
        st.markdown(f'<div class="compact-row" id="hp-bar"><p class="compact-label">❤️ HP: {int(pg["hp"])}/20</p>', unsafe_allow_html=True); st.progress(max(0.0, min(1.0, int(pg['hp']) / 20))); st.markdown('</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="compact-row" id="mana-bar"><p class="compact-label">✨ MN: {int(pg["mana"])}/20</p>', unsafe_allow_html=True); st.progress(max(0.0, min(1.0, int(pg['mana']) / 20))); st.markdown('</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="compact-row" id="stamina-bar"><p class="compact-label">⚡ VG: {int(pg["vigore"])}/20</p>', unsafe_allow_html=True); st.progress(max(0.0, min(1.0, int(pg['vigore']) / 20))); st.markdown('</div>', unsafe_allow_html=True)
    
    st.write("📜 Abilità:")
    mie_abi = df_a[df_a['proprietario'] == nome_pg]
    for _, a in mie_abi.iterrows():
        with st.container(border=True):
            st.markdown(f"<p style='font-size:12px; margin:0;'>**{a['nome']}**</p>", unsafe_allow_html=True)
            st.caption(f"{a['tipo']} • Costo: {a['costo']}")

    st.divider()
    st.write("👥 Compagni:")
    compagni = df_p[df_p['username'].astype(str) != str(st.session_state.user)]
    for _, c in compagni.iterrows():
        with st.container(border=True):
            try:
                uv = datetime.strptime(str(c['ultimo_visto']), '%Y-%m-%d %H:%M:%S')
                st_cl = "🟢" if (datetime.now() - uv) < timedelta(minutes=10) else ""
            except: st_cl = ""
            st.markdown(f"**{c['nome_pg']}** {st_cl}")
            st.caption(f"Liv. {int(c['lvl'])} • {c['razza']}")
            st.progress(max(0.0, min(1.0, int(c['hp']) / 20)))

st.title('📜 Cronaca dell\'Abisso')
for _, r in df_m.tail(15).iterrows():
    with st.chat_message("assistant" if r['autore'] == 'Master' else "user"):
        st.write(f"**{r['autore']}**: {r['testo']}")

if act := st.chat_input('Cosa fai?'):
    with st.spinner('Il Master narra...'):
        try:
            storia = "\n".join([f"{r['autore']}: {r['testo']}" for _, r in df_m.tail(5).iterrows()])
            nem_info = "\n".join([f"- {n['nome_nemico']}: {int(n['hp'])} HP" for _, n in df_n[df_n['posizione'] == pg['posizione']].iterrows()])
            abi_info = "\n".join([f"- {a['nome']}: (Costo: {a['costo']}, Tipo: {a['tipo']})" for _, a in mie_abi.iterrows()])
            
            sys_msg = f"""Sei il Master. Giocatore: {nome_pg}. Nemici: {nem_info}.
            REGOLE MECCANICHE TASSATIVE (Ignora la fighitudine della descrizione):
            1. OGNI attacco tira un d20. Danni al nemico: 11-14=1, 15-19=2, 20=3.
            2. Se si usa un'abilità (NOME_ABILITA), somma +1d4 al danno d20 e scala il costo esatto.
            3. Se NON è un'abilità, è attacco base: scala sempre 1 Vigore.
            4. Se DANNI_RICEVUTI > 0, narra obbligatoriamente il colpo nemico.
            TAG: DANNI_NEMICO: X, DANNI_RICEVUTI: X, MANA_USATO: X, VIGORE_USATO: X, XP: X, NOME_NEMICO: nome, LUOGO: {pg['posizione']}"""
            
            res = client.chat.completions.create(messages=[{"role": "system", "content": sys_msg}, {"role": "user", "content": f"Abilità disponibili: {abi_info}\nAzione: {act}"}], model="llama-3.3-70b-versatile").choices[0].message.content
            
            def get_tag(tag, text):
                match = re.search(f"{tag}:\\s*(\\d+)", text)
                return int(match.group(1)) if match else 0
            
            v_nem, v_ric, v_mn, v_vg, v_xp = get_tag("DANNI_NEMICO", res), get_tag("DANNI_RICEVUTI", res), get_tag("MANA_USATO", res), get_tag("VIGORE_USATO", res), get_tag("XP", res)
            
            t_match = re.search(r"NOME_NEMICO:\s*([^\n,]+)", res)
            if t_match:
                df_n.loc[df_n['nome_nemico'] == t_match.group(1).strip(), 'hp'] -= v_nem
                conn.update(worksheet='nemici', data=df_n)

            df_p.loc[df_p['username'] == st.session_state.user, ['hp', 'mana', 'vigore', 'ultimo_visto']] = [max(0, int(pg['hp']) - v_ric), max(0, int(pg['mana']) - v_mn), max(0, int(pg['vigore']) - v_vg), datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
            if v_xp > 0: df_p.loc[df_p['posizione'] == pg['posizione'], 'xp'] += v_xp
            
            conn.update(worksheet='personaggi', data=df_p)
            new_m = pd.concat([df_m, pd.DataFrame([{'data': datetime.now().strftime('%H:%M'), 'autore': nome_pg, 'testo': act}, {'data': datetime.now().strftime('%H:%M'), 'autore': 'Master', 'testo': res}])], ignore_index=True)
            conn.update(worksheet='messaggi', data=new_m)
            st.cache_data.clear(); st.rerun()
        except Exception as e:
            st.error(f"Errore: {e}")
