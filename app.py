import streamlit as st
from groq import Groq
from streamlit_gsheets import GSheetsConnection
from streamlit_autorefresh import st_autorefresh
import pandas as pd
from datetime import datetime, timedelta
import re
import time
import urllib.parse
import hashlib

st.set_page_config(page_title='Apocrypha Master', layout='wide')

# --- CSS INTEGRALE ---
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; }
    div[data-testid="stSidebarUserContent"] { padding-top: 1rem; }
    .compact-row { display: flex; align-items: center; gap: 10px; margin-bottom: 4px; }
    .compact-label { font-size: 12px !important; min-width: 85px; margin: 0 !important; white-space: nowrap; }
    .stProgress { height: 6px !important; flex-grow: 1; }
    #hp-bar .stProgress div[role="progressbar"] > div { background-color: #ff4b4b !important; }
    #mana-bar .stProgress div[role="progressbar"] > div { background-color: #00f2ff !important; }
    #stamina-bar .stProgress div[role="progressbar"] > div { background-color: #00ff88 !important; }
    #xp-bar .stProgress div[role="progressbar"] > div { background-color: #ffffff !important; }
    div[data-testid="stVerticalBlock"] > div { padding-bottom: 0px !important; margin-bottom: 0px !important; }
    </style>
""", unsafe_allow_html=True)

if 'GROQ_API_KEY' not in st.secrets:
    st.error("Chiave API mancante nei Secrets!")
    st.stop()

client = Groq(api_key=st.secrets['GROQ_API_KEY'])
conn = st.connection('gsheets', type=GSheetsConnection)

# REFRESH AUTOMATICO 60 SECONDI
st_autorefresh(interval=60000, key='global_sync')

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
            st.session_state.user = u.strip()
            st.rerun()
    st.stop()

XP_LEVELS = {1: 0, 2: 300, 3: 900, 4: 2700, 5: 6500}

# --- CARICAMENTO DATI ---
try:
    df_p = conn.read(worksheet='personaggi', ttl=0)
    df_m = conn.read(worksheet='messaggi', ttl=0).fillna('')
    df_a = conn.read(worksheet='abilita', ttl=0).fillna('')
    df_n = conn.read(worksheet='nemici', ttl=0).fillna(0)
    
    cols_num = ['hp', 'mana', 'vigore', 'xp', 'lvl']
    for c in cols_num:
        if c in df_p.columns: df_p[c] = pd.to_numeric(df_p[c], errors='coerce').fillna(0)
    
    cols_text = ['razza', 'classe', 'nome_pg', 'ultimo_visto', 'img', 'img_luogo', 'last_pos', 'posizione']
    for c in cols_text:
        if c not in df_p.columns: df_p[c] = ''
    df_p = df_p.fillna('')
except:
    st.warning("Sincronizzazione database in corso...")
    st.stop()

u_df = df_p[df_p['username'].astype(str) == str(st.session_state.user)]

if u_df.empty:
    st.title("🛡️ Crea il tuo Eroe")
    with st.form("creazione_pg"):
        n_nuovo = st.text_input("Nome Eroe")
        r_nuova = st.selectbox("Razza", ["Primaris", "Inferis", "Narun", "Minotauro"])
        c_nuova = st.selectbox("Classe", ["Orrenai", "Elementalista", "Armagister", "Chierico"])
        img_nuova = st.text_input("URL Avatar (.jpg/.png)")
        if st.form_submit_button("Inizia"):
            nuovo = pd.DataFrame([{"username": st.session_state.user, "nome_pg": n_nuovo, "razza": r_nuova, "classe": c_nuova, "hp": 20, "mana": 20, "vigore": 20, "xp": 0, "lvl": 1, "posizione": "Strada per Gauvadon", "img": img_nuova, "img_luogo": "", "last_pos": "", "ultimo_visto": datetime.now().strftime('%Y-%m-%d %H:%M:%S')}])
            conn.update(worksheet='personaggi', data=pd.concat([df_p, nuovo], ignore_index=True))
            st.rerun()
    st.stop()

pg_idx = u_df.index[0]
pg = df_p.loc[pg_idx]
nome_pg = pg['nome_pg']

# --- SIDEBAR (Status Completo con Icone) ---
with st.sidebar:
    st.header('🛡️ SCHEDA EROE')
    if len(str(pg['img'])) > 5: st.image(pg['img'], use_container_width=True)
    with st.container(border=True):
        st.markdown(f"**{nome_pg}** (Lv. {int(pg['lvl'])})")
        st.caption(f"📍 {pg['posizione']}")
        
        st.markdown(f'<div class="compact-row" id="hp-bar"><p class="compact-label">❤️ HP: {int(pg["hp"])}/20</p>', unsafe_allow_html=True)
        st.progress(max(0.0, min(1.0, int(pg['hp']) / 20)))
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown(f'<div class="compact-row" id="mana-bar"><p class="compact-label">✨ MN: {int(pg["mana"])}/20</p>', unsafe_allow_html=True)
        st.progress(max(0.0, min(1.0, int(pg['mana']) / 20)))
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown(f'<div class="compact-row" id="stamina-bar"><p class="compact-label">⚡ VG: {int(pg["vigore"])}/20</p>', unsafe_allow_html=True)
        st.progress(max(0.0, min(1.0, int(pg["vigore"]) / 20)))
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.divider()
        cur_xp, nxt_xp = int(pg['xp']), XP_LEVELS.get(int(pg['lvl']) + 1, 99999)
        st.markdown(f'<div class="compact-row" id="xp-bar"><p class="compact-label">📖 XP: {cur_xp}/{nxt_xp}</p>', unsafe_allow_html=True)
        st.progress(max(0.0, min(1.0, cur_xp / nxt_xp)))
        st.markdown('</div>', unsafe_allow_html=True)

    st.write("📜 Abilità:")
    m_a = df_a[df_a['proprietario'] == nome_pg]
    for _, a in m_a.iterrows():
        with st.container(border=True):
            st.markdown(f"**{a['nome']}**")
            st.caption(f"{a['tipo']} • Costo: {a['costo']}")

    st.divider()
    st.write("👥 Compagni:")
    compagni = df_p[df_p['username'].astype(str) != str(st.session_state.user)]
    for _, c in compagni.iterrows():
        with st.container(border=True):
            try:
                uv = datetime.strptime(str(c['ultimo_visto']), '%Y-%m-%d %H:%M:%S')
                status_icon = "🟢 Online" if datetime.now() - uv < timedelta(minutes=10) else "🔴 Offline"
                status_time = "" if "Online" in status_icon else f"Ultimo: {uv.strftime('%H:%M')}"
            except:
                status_icon = "❓"
                status_time = ""
            st.markdown(f"**{c['nome_pg']}** {status_icon}")
            st.caption(f"Liv. {int(c['lvl'])} • {c['razza']} {c['classe']}")
            if status_time: st.caption(status_time)
            st.progress(max(0.0, min(1.0, int(c['hp']) / 20)))

# --- LOGICA IMMAGINE AMBIENTE ---
curr_pos = str(pg['posizione']).strip()
if curr_pos != str(pg['last_pos']).strip():
    seed = int(hashlib.sha256(curr_pos.encode('utf-8')).hexdigest(), 16) % 10**8
    safe_place = urllib.parse.quote(curr_pos)
    new_url = f"https://image.pollinations.ai/prompt/dark-fantasy-scenery-painting-{safe_place}?width=1200&height=600&nologo=true&seed={seed}"
    df_p.at[pg_idx, 'img_luogo'] = new_url
    df_p.at[pg_idx, 'last_pos'] = curr_pos
    conn.update(worksheet='personaggi', data=df_p)
    new_m = pd.concat([df_m, pd.DataFrame([{'data': datetime.now().strftime('%H:%M'), 'autore': 'Master', 'testo': f"IMG|{curr_pos}|{new_url}"}])], ignore_index=True)
    conn.update(worksheet='messaggi', data=new_m)
    st.cache_data.clear()
    st.rerun()

# --- CHAT UI ---
st.title('📜 Cronaca dell\'Abisso')
for _, r in df_m.tail(25).iterrows():
    with st.chat_message("assistant" if r['autore'] == 'Master' else "user"):
        if str(r['testo']).startswith('IMG|'):
            p_img = str(r['testo']).split('|')
            st.write(f"***Nuova zona scoperta: {p_img[1]}***")
            st.image(p_img[2], use_container_width=True)
        else:
            st.markdown(r['testo'], unsafe_allow_html=True)

# --- AZIONE MASTER ---
if act := st.chat_input('Cosa fai?'):
    with st.spinner('Il Master narra...'):
        try:
            m_a_txt = "\n".join([f"- {a['nome']}" for _, a in m_a.iterrows()])
            altri = ", ".join([n for n in df_p['nome_pg'] if n != nome_pg])
            sys_msg = f"Sei il Master di 4 giocatori. Attuale: {nome_pg}. Altri: {altri}. Scrivi SOLO la narrazione. NON citare mai blacklist o dati tecnici nel testo. Inserisci ///DATI/// a fine messaggio. TAG: DANNI_NEMICO, DANNI_RICEVUTI, MANA_USATO, VIGORE_USATO, XP, NOME_NEMICO, LUOGO."
            res = client.chat.completions.create(messages=[{"role": "system", "content": sys_msg}, {"role": "user", "content": f"Azione di {nome_pg}: {act}\nAbilita: {m_a_txt}"}], model="llama-3.3-70b-versatile").choices[0].message.content
            
            parts = res.split('///DATI///')
            testo_pulito = parts[0].strip()
            dati = parts[1] if len(parts) > 1 else ""
            
            def get_tag(tag, text):
                m = re.search(f"{tag}:\\s*(\\d+)", text)
                return int(m.group(1)) if m else 0
            
            v_ric, v_mn, v_vg = get_tag("DANNI_RICEVUTI", dati), get_tag("MANA_USATO", dati), get_tag("VIGORE_USATO", dati)
            v_nem, v_xp = get_tag("DANNI_NEMICO", dati), get_tag("XP", dati)
            loc_m = re.search(r"LUOGO:\s*(.+)", dati)
            nuovo_luogo = loc_m.group(1).strip() if loc_m else pg['posizione']
            
            df_p.at[pg_idx, 'hp'] = max(0, int(pg['hp']) - v_ric)
            df_p.at[pg_idx, 'mana'] = max(0, int(pg['mana']) - v_mn)
            df_p.at[pg_idx, 'vigore'] = max(0, int(pg['vigore']) - v_vg)
            df_p.at[pg_idx, 'posizione'] = nuovo_luogo
            df_p.at[pg_idx, 'ultimo_visto'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            if v_xp > 0: df_p.loc[df_p['posizione'] == pg['posizione'], 'xp'] += v_xp
            
            conn.update(worksheet='personaggi', data=df_p)
            new_m = pd.concat([df_m, pd.DataFrame([{'data': datetime.now().strftime('%H:%M'), 'autore': nome_pg, 'testo': act}, {'data': datetime.now().strftime('%H:%M'), 'autore': 'Master', 'testo': testo_pulito}])], ignore_index=True)
            conn.update(worksheet='messaggi', data=new_m)
            st.cache_data.clear()
            st.rerun()
        except: st.error("Errore di connessione con il Master")
