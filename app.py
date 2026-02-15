import streamlit as st
from openai import OpenAI
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Apocrypha Multiplayer", page_icon="⚔️")

# Collegamento API e Database
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
conn = st.connection("gsheets", type=GSheetsConnection)

# --- LOGIN ---
if "autenticato" not in st.session_state:
    st.session_state.autenticato = False

if not st.session_state.autenticato:
    st.title("🛡️ Entra nella Stanza di Apocrypha")
    user = st.text_input("Tuo Nome Reale:")
    pwd = st.text_input("Password:", type="password")
    if st.button("Entra"):
        if pwd == "apocrypha2026" and user:
            st.session_state.autenticato = True
            st.session_state.username = user
            st.rerun()
    st.stop()

# --- SIDEBAR: SCHEDA E GIOCATORI ---
with st.sidebar:
    st.header("👥 Giocatori Online")
    st.write(f"Tu: **{st.session_state.username}**")
    st.divider()
    if st.button("Aggiorna Chat 🔄"):
        st.rerun()

# --- CARICAMENTO MESSAGGI GLOBALI ---
# Leggiamo i messaggi dal foglio "messaggi" (crea un secondo foglio nel tuo Sheets chiamato 'messaggi')
try:
    all_msgs = conn.read(worksheet="messaggi")
except:
    all_msgs = pd.DataFrame(columns=["data", "autore", "testo"])

st.title("⚔️ Apocrypha: Chat Globale")

# Mostra la cronologia condivisa
for index, row in all_msgs.tail(20).iterrows():
    with st.chat_message(row["autore"]):
        st.write(f"**{row['autore']}**: {row['testo']}")

# --- INVIO MESSAGGIO ---
if prompt := st.chat_input("Fai la tua mossa..."):
    # 1. Salva il messaggio del giocatore sul database
    nuovo_msg = pd.DataFrame([{"data": datetime.now(), "autore": st.session_state.username, "testo": prompt}])
    updated_df = pd.concat([all_msgs, nuovo_msg], ignore_index=True)
    conn.update(worksheet="messaggi", data=updated_df)
    
    # 2. Chiedi all'IA di rispondere a TUTTA la conversazione
    context = [{"role": "system", "content": "Sei il Master di un gruppo. Rispondi all'ultimo messaggio tenendo conto della storia."}]
    for i, r in all_msgs.tail(5).iterrows():
        context.append({"role": "user" if r["autore"] != "Master" else "assistant", "content": r["testo"]})
    context.append({"role": "user", "content": prompt})
    
    response = client.chat.completions.create(model="gpt-4o", messages=context).choices[0].message.content
    
    # 3. Salva la risposta del Master sul database
    ia_msg = pd.DataFrame([{"data": datetime.now(), "autore": "Master", "testo": response}])
    final_df = pd.concat([updated_df, ia_msg], ignore_index=True)
    conn.update(worksheet="messaggi", data=final_df)
    
    st.rerun()
