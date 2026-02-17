import streamlit as st
from groq import Groq
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import re
import time
import urllib.parse

st.set_page_config(page_title='Apocrypha Master', layout='wide')

# --- CSS COMPLETO ---
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
    # ttl=0 forza la lettura fresca da Google Sheets ad ogni interazione
    df_p = conn.read(worksheet='personaggi', ttl=0)
    df_m = conn.read(worksheet='messaggi', ttl=0).fillna('')
    df_a = conn.read(worksheet='abilita', ttl=0).fillna('')
    df_n = conn.read(worksheet='nemici', ttl=0).fillna(0)
    
    # Pulizia Posizione
    if 'posizione' in df_p.columns:
        df_p['posizione'] = df_p['posizione'].astype(str).replace('0.0', 'Sconosciuto').replace('0', 'Sconosciuto').replace('nan', 'Sconosciuto')
    
    # Pulizia Numeri
    cols_num = ['hp', 'mana', 'vigore', 'xp', 'lvl']
    for c in cols_num:
        if c in df_p.columns: df_p[c] = pd.to_numeric(df_p[c], errors='coerce').fillna(0)
    
    # Pulizia Testi e Colonne
    cols_text = ['razza', 'classe', 'nome_pg', 'ultimo_visto', 'img', 'img_luogo', 'last_pos']
    for c in cols_text:
        if c not in df_p.columns: 
            df_p[c] = ''
        df_p[c] = df_p[c].fillna('').astype(str)

    if not df_n.empty:
        df_n['hp'] = pd.to_numeric(df_n['hp'], errors='coerce').fillna(0)
        df_n['posizione'] = df_n['posizione'].astype(str).str.strip()
        df_p['posizione'] = df_p['posizione'].astype(str).str.strip()

except Exception as e:
    st.warning(f"Errore caricamento dati: {e}")
    st.stop()

user_pg_df = df_p[df_p['username'].astype(str) == str(st.session_state.user)]

# --- CREAZIONE PG ---
if user_pg_df.empty:
    st.title("🛡️ Crea il tuo Eroe")
    with st.form("creazione_pg"):
        n_nuovo = st.text_input("Nome Eroe")
        r_nuova = st.selectbox("Razza", ["Primaris", "Inferis", "Narun", "Minotauro"])
        c_nuova = st.selectbox("Classe", ["Orrenai", "Elementalista", "Armagister", "Chierico"])
        img_nuova = st.text_input("URL Immagine Profilo (.jpg/.png) - Opzionale")
        
        if st.form_submit_button("Inizia Avventura"):
            nuovo = pd.DataFrame([{
                "username": st.session_state.user, "nome_pg": n_nuovo, 
                "razza": r_nuova, "classe": c_nuova, 
                "hp": 20, "mana": 20, "vigore": 20, "xp": 0, "lvl": 1, 
                "posizione": "Strada per Gauvadon", 
                "img": img_nuova,
                "img_luogo": "",
                "last_pos": "Strada per Gauvadon",
                "ultimo_visto": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }])
            df_p = pd.concat([df_p, nuovo], ignore_index=True)
            conn.update(worksheet='personaggi', data=df_p)
            st.rerun()
    st.stop()

# Recupero Indice del Giocatore Corrente
pg_index = user_pg_df.index[0]
pg = df_p.loc[pg_index]
nome_pg = pg['nome_pg']

# --- SIDEBAR COMPLETA ---
with st.sidebar:
    st.header('🛡️ SCHEDA EROE')
    
    # 1. AVATAR PROFILO
    if len(pg['img']) > 5:
        try:
            st.image(pg['img'], use_container_width=True)
        except:
            st.error("Link immagine errato")
    
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
    for _, a in mie_abi.iterrows():
        with st.container(border=True):
            st.markdown(f"<p style='font-size:12px; margin:0;'>**{a['nome']}**</p>", unsafe_allow_html=True)
            st.caption(f"{a['tipo']} • Costo: {a['costo']}")

    st.divider()
    st.write("👥 Compagni:")
    compagni = df_p[df_p['username'].astype(str) != str(st.session_state.user)]
    for _, c in compagni.iterrows():
        with st.container(border=True):
            # LOGICA ONLINE/OFFLINE
            try:
                uv = datetime.strptime(str(c['ultimo_visto']), '%Y-%m-%d %H:%M:%S')
                # Se visto negli ultimi 10 minuti -> Online
                if datetime.now() - uv < timedelta(minutes=10):
                    status_icon = "🟢 Online"
                    status_time = ""
                else:
                    status_icon = "🔴 Offline"
                    status_time = f"Ultimo: {uv.strftime('%H:%M')}"
            except:
                status_icon = "❓"
                status_time = ""
            
            st.markdown(f"**{c['nome_pg']}** {status_icon}")
            st.caption(f"Liv. {int(c['lvl'])} • {c['razza']} {c['classe']}")
            if status_time: st.caption(status_time)
            st.progress(max(0.0, min(1.0, int(c['hp']) / 20)))

# --- LOGICA IMMAGINE AMBIENTAZIONE (STABILE) ---
curr_pos = str(pg['posizione']).strip()
last_pos = str(pg['last_pos']).strip()

if curr_pos != last_pos or len(pg['img_luogo']) < 5:
    with st.spinner(f"Groq sta dipingendo {curr_pos}..."):
        try:
            prompt_request = f"Create a short, vivid, dark fantasy visual description (max 15 words) for a place called: '{curr_pos}'. Focus on atmosphere, lighting and colors. No intro, just the visual description."
            vis_desc = client.chat.completions.create(messages=[{"role": "user", "content": prompt_request}], model="llama-3.3-70b-versatile").choices[0].message.content
            
            safe_desc = urllib.parse.quote(vis_desc)
            new_img_url = f"https://image.pollinations.ai/prompt/{safe_desc}?width=1200&height=500&nologo=true&seed={int(time.time())}"
            
            df_p.at[pg_index, 'img_luogo'] = new_img_url
            df_p.at[pg_index, 'last_pos'] = curr_pos
            conn.update(worksheet='personaggi', data=df_p)
            
            pg['img_luogo'] = new_img_url
        except Exception as e:
            st.error(f"Errore generazione ambientazione: {e}")

# MOSTRA AMBIENTAZIONE
st.title('📜 Cronaca dell\'Abisso')
if len(pg['img_luogo']) > 5:
    st.image(pg['img_luogo'], caption=f"{pg['posizione']}", use_container_width=True)

# --- CHAT ---
for _, r in df_m.tail(15).iterrows():
    with st.chat_message("assistant" if r['autore'] == 'Master' else "user"):
        st.write(f"**{r['autore']}**: {r['testo']}")

# --- INPUT E LOGICA MASTER ---
if act := st.chat_input('Cosa fai?'):
    with st.spinner('Il Master narra...'):
        try:
            nemici_presenti = df_n[df_n['posizione'] == pg['posizione']]
            if nemici_presenti.empty:
                nem_info = "NESSUN NEMICO VISIBILE."
            else:
                nem_info = "\n".join([f"- {n['nome_nemico']}: {int(n['hp'])} HP" for _, n in nemici_presenti.iterrows()])
            
            abi_info = "\n".join([f"- {a['nome']}: (Costo: {a['costo']}, Tipo: {a['tipo']})" for _, a in mie_abi.iterrows()])
            
            # Lista nera per anti-puppeteering
            lista_altri = [name for name in df_p['nome_pg'].astype(str).unique().tolist() if name != nome_pg]
            str_blacklist = ", ".join(lista_altri)

            # PROMPT DI SISTEMA
            sys_msg = f"""Sei un MOTORE DI GIOCO NEUTRALE (Master). 
            Giocatore Attuale: {nome_pg}.
            
            [BLACKLIST - PERSONAGGI VIETATI]
            Tu NON puoi controllare, né far parlare, né descrivere i pensieri di: {str_blacklist}.
            Questi sono altri GIOCATORI REALI.
            
            [REGOLA D'ORO ANTI-PUPPETEERING]
            Se {nome_pg} parla o interagisce con uno dei nomi nella BLACKLIST:
            1. TU DEVI FERMARTI.
            2. Descrivi solo l'ambiente circostante (il vento, la luce, i suoni di fondo).
            3. Descrivi la reazione generica dell'ambiente, MA NON LA RISPOSTA DEL PERSONAGGIO.
            
            [INFO NEMICI]
            {nemici_presenti}
            
            REGOLE MECCANICHE:
            1. Attacco: d20 (11-14=1, 15-19=2, 20=3). Abilità: d20 + 1d4.
            2. Se (HP Nemico - DANNI) <= 0, il nemico MUORE (descrivi morte e cancella).
            3. XP: Assegna solo se nemico muore.
            
            TAG OUTPUT (Invisibili al player):
            DANNI_NEMICO: X
            DANNI_RICEVUTI: X
            MANA_USATO: X
            VIGORE_USATO: X
            XP: X
            NOME_NEMICO: nome
            LUOGO: {pg['posizione']}"""
            
            res = client.chat.completions.create(messages=[{"role": "system", "content": sys_msg}, {"role": "user", "content": f"Abilità: {abi_info}\nAzione: {act}"}], model="llama-3.3-70b-versatile").choices[0].message.content
            
            # --- PARSING E SALVATAGGIO ---
            def get_tag(tag, text):
                match = re.search(f"{tag}:\\s*(\\d+)", text)
                return int(match.group(1)) if match else 0
            
            v_nem, v_ric, v_mn, v_vg, v_xp_proposed = get_tag("DANNI_NEMICO", res), get_tag("DANNI_RICEVUTI", res), get_tag("MANA_USATO", res), get_tag("VIGORE_USATO", res), get_tag("XP", res)
            
            # Check cambio luogo
            loc_match = re.search(r"LUOGO:\s*(.+)", res)
            nuovo_luogo = loc_match.group(1).strip() if loc_match else pg['posizione']
            
            # Gestione Nemici
            xp_confermato = 0
            t_match = re.search(r"NOME_NEMICO:\s*([^\n,]+)", res)
            if t_match and v_nem > 0:
                bersaglio = t_match.group(1).strip()
                idx_nem = df_n[(df_n['nome_nemico'] == bersaglio) & (df_n['posizione'] == pg['posizione'])].index
                if not idx_nem.empty:
                    nuovi_hp = df_n.loc[idx_nem, 'hp'].values[0] - v_nem
                    df_n.loc[idx_nem, 'hp'] = nuovi_hp
                    if nuovi_hp <= 0:
                        df_n = df_n.drop(idx_nem)
                        xp_confermato = v_xp_proposed
                    conn.update(worksheet='nemici', data=df_n)

            # Aggiornamento PG
            df_p.at[pg_index, 'hp'] = max(0, int(pg['hp']) - v_ric)
            df_p.at[pg_index, 'mana'] = max(0, int(pg['mana']) - v_mn)
            df_p.at[pg_index, 'vigore'] = max(0, int(pg['vigore']) - v_vg)
            df_p.at[pg_index, 'ultimo_visto'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            df_p.at[pg_index, 'posizione'] = nuovo_luogo 
            
            if xp_confermato > 0:
                mask_gruppo = df_p['posizione'] == pg['posizione']
                df_p.loc[mask_gruppo, 'xp'] += xp_confermato
            
            conn.update(worksheet='personaggi', data=df_p)
            
            # Pulizia Output
            testo_pulito = re.sub(r'(TAG OUTPUT:|DANNI_NEMICO:|DANNI_RICEVUTI:|MANA_USATO:|VIGORE_USATO:|XP:|NOME_NEMICO:|LUOGO:).*', '', res, flags=re.DOTALL).strip()
            
            new_m = pd.concat([df_m, pd.DataFrame([{'data': datetime.now().strftime('%H:%M'), 'autore': nome_pg, 'testo': act}, {'data': datetime.now().strftime('%H:%M'), 'autore': 'Master', 'testo': testo_pulito}])], ignore_index=True)
            conn.update(worksheet='messaggi', data=new_m)
            
            st.cache_data.clear()
            st.rerun()
        except Exception as e:
            st.error(f"Errore: {e}")
