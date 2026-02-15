import streamlit as st
from openai import OpenAI

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="Apocrypha RPG", page_icon="⚔️")
client = OpenAI(api_key="LA_TUA_CHIAVE_QUI") # Metti la tua chiave tra le virgolette
PASSWORD_ACCESSO = "apocrypha2026" # Scegli la password per i tuoi amici

# --- LOGIN ---
if "autenticato" not in st.session_state:
    st.session_state.autenticato = False

if not st.session_state.autenticato:
    st.title("Benvenuto in Apocrypha")
    pwd = st.text_input("Inserisci la chiave del regno per entrare:", type="password")
    if st.button("Entra"):
        if pwd == PASSWORD_ACCESSO:
            st.session_state.autenticato = True
            st.rerun()
        else:
            st.error("Password errata, l'oscurità ti respinge.")
    st.stop()

# --- REGOLE DEL MONDO (Il tuo JSON trasformato in Prompt) ---
PROMPT_SISTEMA = """
Sei il Game Master di Apocrypha, un RPG dark fantasy. 
REGOLE FISSE:
1. Parla SEMPRE E SOLO in ITALIANO.
2. Non decidere mai le azioni dei giocatori.
3. Il mondo è crudo, la magia è pericolosa.
4. Razze: Fenrithar (vampiri), Elling (ibridi), Elpide (volpi), Minotauro, Narun (ombre), Feyrin (fati), Primaris, Inferis.
5. Location: Abisso di Ossidiana (dungeon senziente).
6. Se avviene un combattimento, descrivilo in modo narrativo e cruento.
"""

# --- GESTIONE CHAT ---
st.title("⚔️ Apocrypha: L'Abisso di Ossidiana")

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "system", "content": PROMPT_SISTEMA}]
    # Messaggio di inizio
    st.session_state.messages.append({"role": "assistant", "content": "L'aria nell'Abisso è pesante. Siete davanti al grande portone di ossidiana. Chi siete e cosa fate?"})

# Mostra i messaggi precedenti
for msg in st.session_state.messages:
    if msg["role"] != "system":
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

# Input del giocatore
if prompt := st.chat_input("Cosa fai?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Risposta dell'IA
    with st.chat_message("assistant"):
        stream = client.chat.completions.create(
            model="gpt-4o", # Il modello più cazzuto
            messages=st.session_state.messages,
            stream=True,
        )
        response = st.write_stream(stream)
    st.session_state.messages.append({"role": "assistant", "content": response})
