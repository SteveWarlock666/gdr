import streamlit as st
from openai import OpenAI
from streamlit_gsheets import GSheetsConnection
from streamlit_autorefresh import st_autorefresh
import pandas as pd
from datetime import datetime
import random

st.set_page_config(page_title="Apocrypha Multiplayer", page_icon="⚔️", layout="wide")
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
conn = st.connection("gsheets", type=GSheetsConnection)

st_autorefresh(interval=5000, key="chatupdate")

# --- LOGIN E SESSIONE ---
if "autenticato" not in st.session_state:
    st.session_state.autenticato = False

if not st.session_state.autenticato:
    st.title("🛡️ Entra in Apocrypha")
    user = st.text_input("Tuo Nome:")
    pwd = st.text_input("Password:", type="password")
    if st.button("Entra"):
        if pwd == "apocrypha2026" and user:
            st.session_state.autenticato = True
            st.session_state.username = user
            st.rerun()
    st.stop()

# --- CARICAMENTO DATI SICURO ---
try:
    df_chat = conn.read(worksheet="messaggi", ttl="0s")
except:
    df_chat = pd.DataFrame(columns=["data", "autore", "testo"])

# --- SIDEBAR ---
with st.sidebar:
    st.header(f"👤 {st.session_state.username}")
    # Per ora teniamo i PG in sessione per evitare l'errore di scrittura su GSheets
    if "pg" not in st.session_state:
        st.subheader("Crea Eroe")
        n_pg = st.text_input("Nome PG:")
        r_pg = st.selectbox("Razza:", ["Fenrithar", "Elling", "Elpide", "Minotauro", "Narun", "Feyrin", "Primaris", "Inferis"])
        if st.button("Conferma"):
            st.session_state.pg = {"nome": n_pg, "razza": r_pg, "hp": 100}
            st.rerun()
    else:
        st.write(f"**{st.session_state.pg['nome']}**")
        st.write(f"❤️ HP: {st.session_state.pg['hp']}/100")

# --- CHAT ---
st.title("⚔️ Cronaca dell'Abisso")

for idx, row in df_chat.tail(15).iterrows():
    with st.chat_message("assistant" if row['autore'] == "Master" else "user"):
        st.write(f"**{row['autore']}**: {row['testo']}")

if prompt := st.chat_input("Tua azione..."):
    dado = random.randint(1, 20)
    testo_finale = f"{prompt} (d20: {dado})"
    
    # SYSTEM PROMPT
    PROMPT_IA = f"Sei il Master di Apocrypha. Giocatore: {st.session_state.username}. Usa il d20 per narrare l'intensità (11-15: -1hp, 16-19: -2hp, 20: -3hp critico). Solo italiano, tono dark."
    
    # Risposta IA
    res = client.chat.completions.create(model="gpt-4o", messages=[{"role": "system", "content": PROMPT_IA}, {"role": "user", "content": testo_finale}]).choices[0].message.content
    
    # Per evitare l'errore di scrittura, per ora visualizziamo e basta 
    # (Per salvare davvero su GSheets serve l'autenticazione Service Account JSON)
    st.write(f"**Tu**: {testo_finale}")
    st.write(f"**Master**: {res}")
