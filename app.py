import streamlit as st
from openai import OpenAI
from streamlit_autorefresh import st_autorefresh
import pandas as pd
from datetime import datetime
import random
import requests

# CONFIGURAZIONE
st.set_page_config(page_title="Apocrypha Persistent", page_icon="⚔️", layout="wide")
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# URL del foglio in formato CSV per la lettura rapida
SHEET_ID = "1cYA0uOrK9YAGEd7ySN_0-hQ0VTAvxwF2LNXk_12wdMY"
URL_PG = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=personaggi"
URL_CHAT = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=messaggi"

st_autorefresh(interval=5000, key="global_refresh")

if "autenticato" not in st.session_state:
    st.session_state.autenticato = False

# --- LOGIN ---
if not st.session_state.autenticato:
    st.title("🛡️ Entra nella Cronaca Persistente")
    user = st.text_input("Tuo Nome:")
    pwd = st.text_input("Password:", type="password")
    if st.button("Entra"):
        if pwd == "apocrypha2026" and user:
            st.session_state.autenticato = True
            st.session_state.username = user
            st.rerun()
    st.stop()

# --- LETTURA DATI ---
@st.cache_data(ttl=5)
def get_data(url):
    return pd.read_csv(url)

try:
    df_pg = get_data(URL_PG)
    df_chat = get_data(URL_CHAT)
except:
    df_pg = pd.DataFrame(columns=["username", "nome_pg", "razza", "classe", "hp"])
    df_chat = pd.DataFrame(columns=["data", "autore", "testo"])

# --- SIDEBAR: LISTA UTENTI ---
with st.sidebar:
    st.header("👥 Online nell'Abisso")
    for _, row in df_pg.iterrows():
        st.write(f"🟢 **{row['nome_pg']}** ({row['username']})")
        st.caption(f"{row['razza']} {row['classe']} | HP: {row['hp']}")
        st.divider()

    if st.session_state.username not in df_pg['username'].values.astype(str):
        st.subheader("🖋️ Crea Eroe")
        n_pg = st.text_input("Nome PG:")
        r_pg = st.selectbox("Razza:", ["Fenrithar", "Elling", "Elpide", "Minotauro", "Narun", "Feyrin", "Primaris", "Inferis"])
        c_pg = st.selectbox("Classe:", ["Orrenai", "Armagister", "Mago"])
        if st.button("Salva PG Permanente"):
            # Qui usiamo un trucco: per scrivere senza API pesanti usiamo un Form o istruiamo l'utente
            st.info("Per rendere il salvataggio automatico stabile, scrivi il primo messaggio in chat!")
            st.session_state.temp_pg = {"nome": n_pg, "razza": r_pg, "classe": c_pg}

# --- CHAT GLOBALE ---
st.title("⚔️ Cronaca di Apocrypha")

for _, row in df_chat.tail(20).iterrows():
    role = "assistant" if str(row['autore']) == "Master" else "user"
    with st.chat_message(role):
        st.write(f"**{row['autore']}**: {row['testo']}")

# --- INVIO AZIONE ---
if prompt := st.chat_input("Descrivi l'azione (prova a..., attacco...)"):
    # Logica dado per prove e attacchi
    keywords = ["attacco", "colpisco", "tiro", "provo a", "tento", "cerco di", "indago", "furtivo"]
    dado_info = ""
    if any(k in prompt.lower() for k in keywords):
        dado_info = f"  \n*(d20: {random.randint(1, 20)})*"
    
    testo_u = f"{prompt}{dado_info}"
    
    # IA Master
    ctx = [{"role": "system", "content": "Sei il Master di Apocrypha. Tono dark. d20: 1-10 fail, 11-15 -1hp, 16-19 -2hp, 20 -3hp."}]
    for _, r in df_chat.tail(10).iterrows():
        ctx.append({"role": "user", "content": str(r['testo'])})
    ctx.append({"role": "user", "content": testo_u})
    
    response = client.chat.completions.create(model="gpt-4o", messages=ctx).choices[0].message.content
    
    # Mostriamo i messaggi subito
    with st.chat_message("user"): st.write(f"**{st.session_state.username}**: {testo_u}")
    with st.chat_message("assistant"): st.write(response)
    
    st.warning("⚠️ Nota: Per la persistenza totale su Sheets è necessaria la Service Account JSON nei Secrets.")
