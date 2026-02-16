import streamlit as st
from groq import Groq
from streamlit_gsheets import GSheetsConnection
from streamlit_autorefresh import st_autorefresh
import pandas as pd
from datetime import datetime, timedelta
import re
import time

st.set_page_config(page_title='Apocrypha Master', layout='wide')

# --- CSS COMPLETO (NON SNELLITO) ---
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

# Refresh a 60s per evitare errore 429 di Google
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

# --- CARICAMENTO DATI (TTL 10s per cache) ---
try:
    df_p = conn.read(worksheet='personaggi', ttl=10).fillna(0)
    df_m = conn.read(worksheet='messaggi', ttl=10).fillna('')
    df_a = conn.read(worksheet='abilita', ttl=10).fillna('')
    df_n = conn.read(worksheet='nemici', ttl=10).fillna(0)
    
    # Normalizzazione colonne e tipi dati
    for col in ['razza', 'classe', 'mana', 'vigore', 'xp', 'lvl', 'ultimo_visto', 'posizione']:
        if col not in df_p.columns: df_p[col] = 0 if col not in ['razza', 'classe', 'posizione', 'ultimo_visto'] else ''
    
    if not df_n.empty:
        df_n['hp'] = pd.to_numeric(df_n['hp'], errors='coerce').fillna(0)
        # Pulizia stringhe posizione per evitare mismatch
        df_n['posizione'] = df_n['posizione'].astype(str).str.strip()
        df_p['posizione'] = df_p['posizione'].astype(str).str.strip()

except Exception as e:
    st.warning("Server Google occupati. Attendi 30 secondi e ricarica.")
    st.stop()

user_pg_df = df_p[df_p['username'].astype(str) == str(st.session_state.user)]

# --- CREAZIONE PG (SE MANCA) ---
if user_pg_df.empty:
    st.title("🛡️ Crea il tuo Eroe")
    with st.form("creazione_pg"):
        n_nuovo = st.text_input("Nome Eroe")
        r_nuova = st.selectbox("Razza", ["Umano", "Elfo", "Nano", "Oscuro"])
        c_nuova = st.selectbox("Classe", ["Guerriero", "Mago", "Ladro", "Chierico"])
        if st.form_submit_button("Inizia Avventura"):
            nuovo = pd.DataFrame([{
                "username": st.session_state.user, "nome_pg": n_nuovo, 
                "razza": r_nuova, "classe": c_nuova, 
                "hp": 20, "mana": 20, "vigore": 20, "xp": 0, "lvl": 1, 
                "posizione": "Strada per Gauvadon", 
                "ultimo_visto": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }])
            df_p = pd.concat([df_p, nuovo], ignore_index=True)
            conn.update(worksheet='personaggi', data=df_p)
            st.rerun()
    st.stop()

pg = user_pg_df.iloc[0]
nome_pg = pg['nome_pg']

# LISTA GIOCATORI VIETATI (Tutti tranne il Master)
lista_giocatori_vietati = ", ".join([name for name in df_p['nome_pg'].astype(str).unique().tolist() if name != nome_pg])

# --- SIDEBAR COMPLETA ---
with st.sidebar:
    st.header('🛡️ SCHEDA EROE')
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
            try:
                uv = datetime.strptime(str(c['ultimo_visto']), '%Y-%m-%d %H:%M:%S')
                st_cl = "🟢" if (datetime.now() - uv) < timedelta(minutes=10) else ""
            except: st_cl = ""
            st.markdown(f"**{c['nome_pg']}** {st_cl}")
            st.caption(f"Liv. {int(c['lvl'])} • {c['razza']} {c['classe']}")
            st.progress(max(0.0, min(1.0, int(c['hp']) / 20)))

# --- CHAT UI ---
st.title('📜 Cronaca dell\'Abisso')
for _, r in df_m.tail(15).iterrows():
    with st.chat_message("assistant" if r['autore'] == 'Master' else "user"):
        st.write(f"**{r['autore']}**: {r['testo']}")

# --- LOGICA MASTER ---
if act := st.chat_input('Cosa fai?'):
    with st.spinner('Il Master narra...'):
        try:
            storia = "\n".join([f"{r['autore']}: {r['testo']}" for _, r in df_m.tail(5).iterrows()])
            
            nemici_presenti = df_n[df_n['posizione'] == pg['posizione']]
            if nemici_presenti.empty:
                nem_info = "NESSUN NEMICO VISIBILE (Non inventarne)."
            else:
                nem_info = "\n".join([f"- {n['nome_nemico']}: {int(n['hp'])} HP" for _, n in nemici_presenti.iterrows()])
            
            abi_info = "\n".join([f"- {a['nome']}: (Costo: {a['costo']}, Tipo: {a['tipo']})" for _, a in mie_abi.iterrows()])
            
            # PROMPT MIGLIORATO ANTI-PUPPETEERING
            sys_msg = f"""Sei il Master. Giocatore Attuale: {nome_pg}.
            ALTRI GIOCATORI UMANI (NON TOCCARLI): {lista_giocatori_vietati}.
            NEMICI: {nem_info}.
            
            REGOLA SUPREMA (ANTI-PUPPETEERING):
            TU CONTROLLI SOLO IL MONDO E GLI NPC.
            NON descrivere MAI le azioni, i pensieri o le parole di {lista_giocatori_vietati}.
            Se {nome_pg} interagisce con loro, tu descrivi l'ambiente o l'NPC, e STOP. Lascia che siano loro a rispondere.
            
            REGOLE MECCANICHE:
            1. Attacco: d20 (11-14=1, 15-19=2, 20=3). Abilità: d20 + 1d4.
            2. Se (HP Nemico - DANNI) <= 0, il nemico MUORE (cancellalo dalla scena).
            3. XP: Assegna solo se nemico muore.
            4. NON mostrare calcoli nel testo. Solo narrazione.
            
            TAG OUTPUT:
            DANNI_NEMICO: X
            DANNI_RICEVUTI: X
            MANA_USATO: X
            VIGORE_USATO: X
            XP: X
            NOME_NEMICO: nome
            LUOGO: {pg['posizione']}"""
            
            res = client.chat.completions.create(messages=[{"role": "system", "content": sys_msg}, {"role": "user", "content": f"Abilità: {abi_info}\nAzione: {act}"}], model="llama-3.3-70b-versatile").choices[0].message.content
            
            def get_tag(tag, text):
                match = re.search(f"{tag}:\\s*(\\d+)", text)
                return int(match.group(1)) if match else 0
            
            v_nem, v_ric, v_mn, v_vg, v_xp_proposed = get_tag("DANNI_NEMICO", res), get_tag("DANNI_RICEVUTI", res), get_tag("MANA_USATO", res), get_tag("VIGORE_USATO", res), get_tag("XP", res)
            
            xp_confermato = 0
            
            # GESTIONE NEMICI
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
            df_p.loc[df_p['username'] == st.session_state.user, ['hp', 'mana', 'vigore', 'ultimo_visto']] = [
                max(0, int(pg['hp']) - v_ric), 
                max(0, int(pg['mana']) - v_mn), 
                max(0, int(pg['vigore']) - v_vg), 
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ]
            
            if xp_confermato > 0:
                mask_gruppo = df_p['posizione'] == pg['posizione']
                df_p.loc[mask_gruppo, 'xp'] += xp_confermato
            
            conn.update(worksheet='personaggi', data=df_p)
            new_m = pd.concat([df_m, pd.DataFrame([{'data': datetime.now().strftime('%H:%M'), 'autore': nome_pg, 'testo': act}, {'data': datetime.now().strftime('%H:%M'), 'autore': 'Master', 'testo': res}])], ignore_index=True)
            conn.update(worksheet='messaggi', data=new_m)
            
            st.cache_data.clear()
            st.rerun()
        except Exception as e:
            st.error(f"Errore: {e}")
