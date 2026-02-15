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

try:
    df_pg = conn.read(worksheet="personaggi")
except:
    df_pg = pd.DataFrame(columns=["username", "nome_pg", "razza", "classe", "hp"])

try:
    df_chat = conn.read(worksheet="messaggi")
except:
    df_chat = pd.DataFrame(columns=["data", "autore", "testo"])

pg_data = df_pg[df_pg['username'] == st.session_state.username]

with st.sidebar:
    st.header(f"👤 {st.session_state.username}")
    if pg_data.empty:
        st.subheader("Crea il tuo Eroe")
        n_pg = st.text_input("Nome PG:")
        r_pg = st.selectbox("Razza:", ["Fenrithar", "Elling", "Elpide", "Minotauro", "Narun", "Feyrin", "Primaris", "Inferis"])
        c_pg = st.selectbox("Classe:", ["Orrenai", "Armagister", "Mago"])
        if st.button("Salva PG"):
            new_pg = pd.DataFrame([{"username": st.session_state.username, "nome_pg": n_pg, "razza": r_pg, "classe": c_pg, "hp": 100}])
            df_pg = pd.concat([df_pg, new_pg], ignore_index=True)
            conn.update(worksheet="personaggi", data=df_pg)
            st.rerun()
    else:
        st.subheader("📜 Tua Scheda")
        current_pg = pg_data.iloc[0]
        st.write(f"**{current_pg['nome_pg']}** ({current_pg['razza']} {current_pg['classe']})")
        st.write(f"❤️ Salute: {current_pg['hp']}/100")
        st.progress(int(current_pg['hp']) / 100)
    
    st.divider()
    st.subheader("👥 Gruppo Online")
    for idx, row in df_pg.iterrows():
        status = "🟢" if row['username'] == st.session_state.username else "⚪"
        st.write(f"{status} **{row['nome_pg']}** - HP: {row['hp']}")

st.title("⚔️ Apocrypha: Cronaca dell'Abisso")

for idx, row in df_chat.tail(20).iterrows():
    role = "assistant" if row['autore'] == "Master" else "user"
    with st.chat_message(role):
        st.write(f"**{row['autore']}**: {row['testo']}")

if prompt := st.chat_input("Descrivi la tua azione..."):
    dado = random.randint(1, 20)
    azione_con_dado = f"{prompt} (Risultato dado d20: {dado})"
    
    u_msg = pd.DataFrame([{"data": datetime.now().strftime("%H:%M:%S"), "autore": st.session_state.username, "testo": azione_con_dado}])
    df_chat = pd.concat([df_chat, u_msg], ignore_index=True)
    
    PROMPT_IA = f"""Sei il Master di Apocrypha. 
    REGOLE DI COMBATTIMENTO E INTENSITÀ:
    1. Gestisci i mostri con coerenza. Un mostro comune ha circa 10-15 HP.
    2. Leggi il Risultato dado d20 e descrivi l'intensità:
       - Da 1 a 10: Fallimento o colpo parato. Nessun danno al mostro. Descrizione di goffaggine o difesa nemica.
       - Da 11 a 15: Colpo a segno. Danno: -1 HP al mostro. Descrizione di un graffio o colpo leggero.
       - Da 16 a 19: Colpo eccellente. Danno: -2 HP al mostro. Descrizione di un fendente profondo o colpo brutale.
       - 20: Successo Critico. Danno: -3 HP al mostro. Descrizione epica di mutilazione o colpo vitale.
    3. Identifica il giocatore dal nome autore.
    4. Se un mostro colpisce, usa [DANNO: X A NOME_PG].
    5. Tono dark fantasy, crudo, solo italiano."""

    context = [{"role": "system", "content": PROMPT_IA}]
    for i, r in df_chat.tail(12).iterrows():
        context.append({"role": "assistant" if r['autore'] == "Master" else "user", "content": f"{r['autore']}: {r['testo']}"})
    
    resp = client.chat.completions.create(model="gpt-4o", messages=context).choices[0].message.content
    
    m_msg = pd.DataFrame([{"data": datetime.now().strftime("%H:%M:%S"), "autore": "Master", "testo": resp}])
    df_chat = pd.concat([df_chat, m_msg], ignore_index=True)
    
    conn.update(worksheet="messaggi", data=df_chat)
    st.rerun()
