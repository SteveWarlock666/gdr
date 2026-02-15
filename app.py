import streamlit as st
from openai import OpenAI
from streamlit_autorefresh import st_autorefresh
import pandas as pd
from datetime import datetime
import random

# --- CONFIGURAZIONE INTERFACCIA ---
st.set_page_config(page_title="Apocrypha Multiplayer", page_icon="⚔️", layout="wide")

# --- CONNESSIONE API ---
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# --- REFRESH AUTOMATICO OGNI 5 SECONDI ---
st_autorefresh(interval=5000, key="chatupdate")

# --- SISTEMA DI LOGIN ---
if "autenticato" not in st.session_state:
    st.session_state.autenticato = False

if not st.session_state.autenticato:
    st.title("🛡️ Accesso ad Apocrypha")
    user = st.text_input("Nome Utente (per identificarti in chat):")
    pwd = st.text_input("Password del Regno:", type="password")
    if st.button("Entra"):
        if pwd == "apocrypha2026" and user:
            st.session_state.autenticato = True
            st.session_state.username = user
            st.rerun()
    st.stop()

# --- INIZIALIZZAZIONE SESSIONE ---
if "pg" not in st.session_state:
    st.session_state.pg = None
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- BARRA LATERALE: SCHEDA PERSONAGGIO COMPLETA ---
with st.sidebar:
    st.header(f"👤 Account: {st.session_state.username}")
    
    if st.session_state.pg is None:
        st.subheader("🖋️ Crea il tuo Eroe")
        n_pg = st.text_input("Nome del Personaggio:")
        r_pg = st.selectbox("Seleziona Razza:", [
            "Fenrithar", "Elling", "Elpide", "Minotauro", 
            "Narun", "Feyrin", "Primaris", "Inferis"
        ])
        c_pg = st.selectbox("Seleziona Classe:", [
            "Orrenai", "Armagister", "Mago"
        ])
        
        if st.button("Genera Personaggio"):
            if n_pg:
                st.session_state.pg = {
                    "nome": n_pg, 
                    "razza": r_pg, 
                    "classe": c_pg, 
                    "hp": 100
                }
                st.success(f"{n_pg} è pronto all'azione!")
                st.rerun()
            else:
                st.warning("Il tuo eroe deve avere un nome!")
    else:
        # Visualizzazione Scheda Attiva
        pg = st.session_state.pg
        st.subheader("📜 Scheda Eroe")
        st.markdown(f"**Nome:** {pg['nome']}")
        st.markdown(f"**Razza:** {pg['razza']}")
        st.markdown(f"**Classe:** {pg['classe']}")
        
        # Barra Salute
        st.write(f"❤️ Salute: {pg['hp']}/100")
        st.progress(pg['hp'] / 100)
        
        if st.button("Reset / Nuovo Eroe"):
            st.session_state.pg = None
            st.rerun()

# --- AREA DI GIOCO ---
st.title("⚔️ Cronaca dell'Abisso")

# Visualizzazione dei messaggi precedenti
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# --- INVIO AZIONE E LOGICA DADI ---
if prompt := st.chat_input("Descrivi la tua mossa al Master..."):
    if st.session_state.pg is None:
        st.error("⚠️ Devi prima creare il tuo personaggio nella barra laterale!")
    else:
        # 1. Lancio del Dado d20
        dado = random.randint(1, 20)
        
        # 2. Formattazione messaggio giocatore
        info_pg = f"{st.session_state.pg['nome']} ({st.session_state.pg['classe']})"
        messaggio_utente = f"**{info_pg}**: {prompt}  \n*(Risultato d20: {dado})*"
        
        st.session_state.messages.append({"role": "user", "content": messaggio_utente})
        
        # 3. System Prompt (Le Regole del Master)
        PROMPT_IA = f"""Sei il Master di Apocrypha, un GDR dark fantasy.
        REGOLE FONDAMENTALI:
        - Tono descrittivo, brutale, epico. Solo lingua italiana.
        - Identifica sempre chi parla: il giocatore è {st.session_state.pg['nome']}.
        - Usa il risultato del d20 per determinare l'esito:
            * 1-10: Fallimento. Nessun danno al nemico.
            * 11-15: Successo lieve. Il mostro perde 1 HP.
            * 16-19: Grande successo. Il mostro perde 2 HP.
            * 20: Critico! Il mostro perde 3 HP e descrivi un'azione leggendaria.
        - Tu gestisci l'ambiente e i mostri (creali tu, gestisci i loro HP).
        - Se il giocatore subisce danni, scrivi chiaramente [DANNO: X]."""

        # 4. Generazione Risposta Master
        # Teniamo gli ultimi 15 messaggi per la memoria
        contesto = [{"role": "system", "content": PROMPT_IA}] + st.session_state.messages[-15:]
        
        with st.chat_message("assistant"):
            try:
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=contesto
                ).choices[0].message.content
                st.write(response)
                st.session_state.messages.append({"role": "assistant", "content": response})
            except Exception as e:
                st.error(f"Errore di connessione con l'IA: {e}")
        
        # Ricarica per mostrare i messaggi aggiornati
        st.rerun()
