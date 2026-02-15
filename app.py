import streamlit as st
from groq import Groq
from streamlit_gsheets import GSheetsConnection
from streamlit_autorefresh import st_autorefresh
import pandas as pd
from datetime import datetime
import random

# Configurazione Dark Mode
st.set_page_config(page_title='Apocrypha Chronicles', layout='wide')

st.markdown("""
    <style>
    .hero-card {
        background-color: #1a1c24;
        border-radius: 10px;
        padding: 15px;
        border: 1px solid #3e4451;
        margin-bottom: 10px;
    }
    .hero-name { color: #ffffff; font-size: 1.2rem; font-weight: bold; margin-bottom: 0px; }
    .hero-stats { color: #8b949e; font-size: 0.9rem; margin-bottom: 10px; }
    </style>
""", unsafe_allow_html=True)

# Inizializzazione Client Groq
client = Groq(api_key=st.secrets['GROQ_API_KEY'])
conn = st.connection('gsheets', type=GSheetsConnection)

# Refresh automatico sincronizzato per il multiplayer
st_autorefresh(interval=15000, key='multiplayer_sync')

if 'auth' not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    st.title('🌑 APOCRYPHA')
    u = st.text_input('Chi sei?')
    p = st.text_input('Password:', type='password')
    if st.button('Entra nell Abisso'):
        if p == 'apocrypha2026' and u:
            st.session_state.auth = True
            st.session_state.user = u
            st.rerun()
    st.stop()

# Caricamento Dati
df_p = conn.read(worksheet='personaggi', ttl=0)
df_m = conn.read(worksheet='messaggi', ttl=0)

# SIDEBAR GRAFICA
with st.sidebar:
    st.title('🛡️ STATO EROI')
    for _, r in df_p.iterrows():
        hp = int(r['hp'])
        st.markdown(f"""
            <div class="hero-card">
                <div class="hero-name">{r['nome_pg']}</div>
                <div class="hero-stats">{r['razza']} • {r['classe']}</div>
            </div>
        """, unsafe_allow_html=True)
        st.progress(max(0, min(100, hp)) / 100, text=f"HP: {hp}/100")
    
    if st.session_state.user not in df_p['username'].values.astype(str):
        with st.expander("✨ Nuovo Viandante"):
            n = st.text_input('Nome Eroe')
            rz = st.selectbox('Razza', ['Fenrithar', 'Elling', 'Elpide', 'Minotauro', 'Narun', 'Feyrin', 'Primaris', 'Inferis'])
            cl = st.selectbox('Classe', ['Orrenai', 'Armagister', 'Mago'])
            if st.button('Inizia Viaggio'):
                if n:
                    new = pd.DataFrame([{'username': st.session_state.user, 'nome_pg': n, 'razza': rz, 'classe': cl, 'hp': 100}])
                    conn.update(worksheet='personaggi', data=pd.concat([df_p, new], ignore_index=True))
                    st.rerun()

# CRONACA MULTIPLAYER
st.title('📜 Cronaca dell Abisso')
for _, r in df_m.tail(20).iterrows():
    is_master = r['autore'] == 'Master'
    with st.chat_message("assistant" if is_master else "user"):
        st.markdown(f"**{r['autore']}** <small style='color:gray'>{r['data']}</small>", unsafe_allow_html=True)
        st.write(r['testo'])

# AZIONE
if act := st.chat_input('Scrivi la tua mossa...'):
    pg_n = df_p[df_p['username'] == st.session_state.user].iloc[0]['nome_pg']
    azione_finale = f"{act} [d20: {random.randint(1, 20)}]"
    
    with st.spinner('Il Master osserva...'):
        try:
            # Memoria storica per coerenza multiplayer
            storia = "\n".join([f"{r['autore']}: {r['testo']}" for _, r in df_m.tail(4).iterrows()])
            
            completion = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "Sei il Master di un GDR dark fantasy. Rispondi alle azioni dei giocatori in modo brutale e sintetico (max 3 frasi)."},
                    {"role": "user", "content": f"Storia recente:\n{storia}\n\nOra {pg_n} fa: {azione_finale}"}
                ],
                model="llama-3.3-70b-versatile",
            )
            master_res = completion.choices[0].message.content
            
            nuovi_msg = pd.DataFrame([
                {'data': datetime.now().strftime('%H:%M'), 'autore': pg_n, 'testo': azione_finale},
                {'data': datetime.now().strftime('%H:%M'), 'autore': 'Master', 'testo': master_res}
            ])
            conn.update(worksheet='messaggi', data=pd.concat([df_m, nuovi_msg], ignore_index=True))
            st.cache_data.clear()
            st.rerun()
        except Exception as e:
            st.error(f"Errore: {e}")
