import streamlit as st
from openai import OpenAI
from streamlit_gsheets import GSheetsConnection
from streamlit_autorefresh import st_autorefresh
import pandas as pd
from datetime import datetime
import random

# CONFIGURAZIONE PAGINA
st.set_page_config(page_title="Apocrypha Multiplayer", page_icon="⚔️", layout="wide")

# CONNESSIONI
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
# Il refresh automatico ogni 5 secondi
st_autorefresh(interval=5000, key="chatupdate")

# --- LOGIN ---
if "autenticato" not in st.session_state:
    st.session_state.autenticato = False

if not st.session_state.autenticato:
    st.title("🛡️ Accesso ad Apocrypha")
    user = st.text_input("Nome Utente:")
    pwd = st.text_input("Password del Regno:", type="password")
    if st.button("Entra"):
        if pwd == "apocrypha2026" and user:
            st.session_state.autenticato = True
            st.session_state.username = user
            st.rerun()
    st.stop()

# --- GESTIONE PERSONAGGIO (SIDEBAR) ---
if "pg" not in st.session_state:
    st.session_state.pg = None

with st.sidebar:
    st.header(f"👤 {st.session_state.username}")
    if st.session_state.pg is None:
        st.subheader("Crea il tuo Eroe")
        n_pg = st.text_input("Nome PG:")
        r_pg = st.selectbox("Razza:", ["Fenrithar", "Elling", "Elpide", "Minotauro", "Narun", "Feyrin", "Primaris", "Inferis"])
        c_pg = st.selectbox("Classe:", ["Orrenai", "Armagister", "Mago"])
        if st.button("Salva Personaggio"):
            if n_pg:
                st.session_state.pg = {"nome": n_pg, "razza": r_pg, "classe": c_pg, "hp": 100}
                st.rerun()
    else:
        pg = st.session_state.pg
        st.subheader("📜 Scheda")
        st.write(f"**{pg['nome']}**")
        st.write(f"*{pg['razza']} {pg['classe']}*")
        st.write(f"❤️ Salute: {pg['hp']}/100")
        st.progress(pg['hp'] / 100)
        if st.button("Reset PG"):
            st.session_state.pg = None
            st.rerun()

# --- CHAT GLOBALE ---
st.title("⚔️ Cronaca dell'Abisso")

if "messages" not in st.session_state:
    st.session_state.messages = []

# Visualizzazione messaggi
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# INVIO AZIONE
if prompt := st.chat_input("Descrivi la tua azione..."):
    if st.session_state.pg is None:
        st.error("Devi prima creare un personaggio nella barra a sinistra!")
    else:
        # Calcolo dado e intensità
        dado = random.randint(1, 20)
        azione_giocatore = f"{st.session_state.pg['nome']} ({st.session_state.username}): {prompt} (d20: {dado})"
        
        st.session_state.messages.append({"role": "user", "content": azione_giocatore})
        
        # System Prompt con regole di danno
        PROMPT_IA = f"""Sei il Master di Apocrypha. 
        REGOLE:
        - Tono dark fantasy, crudo, italiano.
        - Usa il risultato del d20 per l'intensità:
          1-10: Fallimento (0 danno al mostro).
          11-15: Successo lieve (-1 HP al mostro).
          16-19: Grande successo (-2 HP al mostro).
          20: Critico (-3 HP al mostro).
        - Gestisci tu i mostri e i loro HP.
        - Se il giocatore viene colpito, usa [DANNO: X]."""

        # Generazione risposta
        chat_context = [{"role": "system", "content": PROMPT_IA}] + st.session_state.messages[-10:]
        
        with st.chat_message("assistant"):
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=chat_context
            ).choices[0].message.content
            st.write(response)
            st.session_state.messages.append({"role": "assistant", "content": response})
        
        st.rerun()
