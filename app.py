import streamlit as st
from openai import OpenAI
from streamlit_gsheets import GSheetsConnection
from streamlit_autorefresh import st_autorefresh
import pandas as pd
from datetime import datetime
import random

# CONFIGURAZIONE
st.set_page_config(page_title="Apocrypha Global", page_icon="⚔️", layout="wide")
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
conn = st.connection("gsheets", type=GSheetsConnection)

# REFRESH OGNI 5 SECONDI PER LA SINCRONIZZAZIONE GLOBALE
st_autorefresh(interval=5000, key="global_refresh")

if "autenticato" not in st.session_state:
    st.session_state.autenticato = False

# --- LOGIN ---
if not st.session_state.autenticato:
    st.title("🛡️ Entra nella Cronaca")
    user = st.text_input("Nome Utente:")
    pwd = st.text_input("Password:", type="password")
    if st.button("Entra"):
        if pwd == "apocrypha2026" and user:
            st.session_state.autenticato = True
            st.session_state.username = user
            st.rerun()
    st.stop()

# --- CARICAMENTO DATI ---
try:
    df_pg = conn.read(worksheet="personaggi", ttl=0)
    df_chat = conn.read(worksheet="messaggi", ttl=0)
except Exception:
    df_pg = pd.DataFrame(columns=["username", "nome_pg", "razza", "classe", "hp"])
    df_chat = pd.DataFrame(columns=["data", "autore", "testo"])

# --- SIDEBAR ---
with st.sidebar:
    st.header("👥 Utenti nel Regno")
    for _, row in df_pg.iterrows():
        st.write(f"🟢 **{row['nome_pg']}**")
        st.caption(f"{row['razza']} {row['classe']} | HP: {row['hp']}")
        st.divider()
    
    if st.session_state.username not in df_pg['username'].values:
        st.subheader("🖋️ Crea il tuo Eroe")
        n_pg = st.text_input("Nome PG:")
        r_pg = st.selectbox("Razza:", ["Fenrithar", "Elling", "Elpide", "Minotauro", "Narun", "Feyrin", "Primaris", "Inferis"])
        c_pg = st.selectbox("Classe:", ["Orrenai", "Armagister", "Mago"])
        if st.button("Salva PG"):
            if n_pg:
                new_pg = pd.DataFrame([{"username": st.session_state.username, "nome_pg": n_pg, "razza": r_pg, "classe": c_pg, "hp": 100}])
                df_pg = pd.concat([df_pg, new_pg], ignore_index=True)
                conn.update(worksheet="personaggi", data=df_pg)
                st.rerun()

# --- CHAT GLOBALE ---
st.title("⚔️ Apocrypha: Cronaca dell'Abisso")
for _, row in df_chat.tail(20).iterrows():
    role = "assistant" if row['autore'] == "Master" else "user"
    with st.chat_message(role):
        st.write(f"**{row['autore']}**: {row['testo']}")

# --- INVIO AZIONE E LOGICA DADI ---
if prompt := st.chat_input("Descrivi la tua azione..."):
    pg_row = df_pg[df_pg['username'] == st.session_state.username]
    if pg_row.empty:
        st.error("Crea il tuo PG a sinistra!")
    else:
        nome_pg = pg_row.iloc[0]['nome_pg']
        
        # LOGICA DADO DINAMICA
        keywords_prova = [
            "attacco", "colpisco", "lancio", "fendente", "scaglio", "tiro", 
            "provo a", "tento di", "cerco di", "indago", "osservo", "esamino", 
            "furtivo", "nascondo", "schivo", "salto", "scassino", "persuado"
        ]
        
        dado_testo = ""
        if any(k in prompt.lower() for k in keywords_prova):
            dado_testo = f"  \n*(d20: {random.randint(1, 20)})*"
        
        testo_utente = f"{prompt}{dado_testo}"
        
        # 1. Salva messaggio utente
        nuovo_m = pd.DataFrame([{"data": datetime.now().strftime("%H:%M"), "autore": nome_pg, "testo": testo_utente}])
        df_chat = pd.concat([df_chat, nuovo_m], ignore_index=True)
        
        # 2. IA - Master Prompt
        PROMPT_IA = f"""Sei il Master di Apocrypha. 
        REGOLE:
        - Tono dark, crudo, epico. Solo lingua italiana.
        - Interpreta il d20 in base all'azione:
            * COMBATTIMENTO: 1-10 fail, 11-15 -1hp mostro, 16-19 -2hp, 20 critico -3hp.
            * PROVE (Furtività, Indagare, etc.): Usa il d20 per narrare il successo o il fallimento dell'azione.
        - Se non c'è un d20, limita la risposta alla narrazione dell'ambiente.
        - Se il giocatore subisce danni, scrivi [DANNO: X]."""
        
        ctx = [{"role": "system", "content": PROMPT_IA}]
        for _, r in df_chat.tail(12).iterrows():
            ctx.append({"role": "assistant" if r['autore'] == "Master" else "user", "content": f"{r['autore']}: {r['testo']}"})
        
        risposta = client.chat.completions.create(model="gpt-4o", messages=ctx).choices[0].message.content
        
        # 3. Salva risposta Master
        df_chat = pd.concat([df_chat, pd.DataFrame([{"data": datetime.now().strftime("%H:%M"), "autore": "Master", "testo": risposta}])], ignore_index=True)
        
        conn.update(worksheet="messaggi", data=df_chat)
        st.rerun()
