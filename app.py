import streamlit as st
from openai import OpenAI

st.set_page_config(page_title="Apocrypha RPG", page_icon="⚔️")

if "OPENAI_API_KEY" in st.secrets:
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
else:
    st.error("Inserisci la API Key nei Secrets di Streamlit!")
    st.stop()

if "fase" not in st.session_state:
    st.session_state.fase = "login"

# 1. LOGIN
if st.session_state.fase == "login":
    st.title("🛡️ Accesso ad Apocrypha")
    pwd = st.text_input("Password del Regno:", type="password")
    if st.button("Entra"):
        if pwd == "apocrypha2026":
            st.session_state.fase = "creazione_pg"
            st.rerun()
        else:
            st.error("Password errata.")
    st.stop()

# 2. CREAZIONE PERSONAGGIO
if st.session_state.fase == "creazione_pg":
    st.title("🖋️ Crea il tuo Eroe")
    nome = st.text_input("Nome del Personaggio:")
    razza = st.selectbox("Razza:", ["Fenrithar", "Elling", "Elpide", "Minotauro", "Narun", "Feyrin", "Primaris", "Inferis"])
    classe = st.selectbox("Classe:", ["Orrenai", "Armagister", "Mago"])
    
    if st.button("Inizia l'Avventura"):
        if nome:
            st.session_state.pg = {"nome": nome, "razza": razza, "classe": classe, "hp": 100}
            st.session_state.fase = "chat"
            st.rerun()
        else:
            st.warning("Dai un nome al tuo personaggio!")
    st.stop()

# 3. GIOCO E CHAT
if st.session_state.fase == "chat":
    pg = st.session_state.pg
    
    with st.sidebar:
        st.header("📜 Scheda Personaggio")
        st.markdown(f"**Nome:** {pg['nome']}")
        st.markdown(f"**Razza:** {pg['razza']}")
        st.markdown(f"**Classe:** {pg['classe']}")
        
        # Barra della Salute
        st.write(f"❤️ Salute: {pg['hp']}/100")
        st.progress(pg['hp'] / 100)
        
        if st.button("Reset / Nuovo PG"):
            st.session_state.fase = "login"
            st.session_state.messages = []
            st.rerun()

    st.title(f"⚔️ Apocrypha: {pg['nome']}")

    PROMPT_SISTEMA = f"""
    Sei il Master di Apocrypha. Il giocatore è {pg['nome']}, un {pg['razza']} {pg['classe']}.
    Salute attuale: {pg['hp']}/100.
    REGOLE:
    1. Parla solo italiano, tono dark fantasy e crudo.
    2. Se il giocatore subisce danni, scrivi alla fine del messaggio: [DANNO: X] dove X è il numero di punti persi.
    3. Se il giocatore beve una pozione o si cura, scrivi: [CURA: X].
    4. Non decidere mai le azioni del giocatore.
    """

    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "system", "content": PROMPT_SISTEMA}]
        st.session_state.messages.append({"role": "assistant", "content": f"L'oscurità ti avvolge, {pg['nome']}. Sei pronto?"})

    for msg in st.session_state.messages:
        if msg["role"] != "system":
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

    if prompt := st.chat_input("Cosa fai?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)

        with st.chat_message("assistant"):
            stream = client.chat.completions.create(model="gpt-4o", messages=st.session_state.messages, stream=True)
            response = st.write_stream(stream)
            
            # Controllo automatico dei danni nel testo dell'IA
            if "[DANNO:" in response:
                try:
                    valore = int(response.split("[DANNO:")[1].split("]")[0].strip())
                    st.session_state.pg['hp'] = max(0, st.session_state.pg['hp'] - valore)
                    st.rerun()
                except: pass
            if "[CURA:" in response:
                try:
                    valore = int(response.split("[CURA:")[1].split("]")[0].strip())
                    st.session_state.pg['hp'] = min(100, st.session_state.pg['hp'] + valore)
                    st.rerun()
                except: pass

        st.session_state.messages.append({"role": "assistant", "content": response})
