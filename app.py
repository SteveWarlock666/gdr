# --- LOGICA IMMAGINE AMBIENTE (Versione Corretta) ---
curr_pos = str(pg['posizione']).strip()
if curr_pos != str(pg['last_pos']).strip() or not pg['img_luogo']:
    # Pulizia estrema del nome luogo per l'URL
    safe_place = urllib.parse.quote(curr_pos.replace(" ", "%20"))
    seed = int(hashlib.sha256(curr_pos.encode('utf-8')).hexdigest(), 16) % 10**8
    
    # Costruzione URL robusta
    new_url = f"https://image.pollinations.ai/prompt/dark-fantasy-scenery-{safe_place}?width=1200&height=600&nologo=true&seed={seed}"
    
    # Aggiornamento Database
    df_p.at[pg_index, 'img_luogo'] = new_url
    df_p.at[pg_index, 'last_pos'] = curr_pos
    conn.update(worksheet='personaggi', data=df_p)
    
    # Messaggio Master per la cronaca
    new_m = pd.concat([df_m, pd.DataFrame([{
        'data': datetime.now().strftime('%H:%M'), 
        'autore': 'Master', 
        'testo': f"IMG|{curr_pos}|{new_url}"
    }])], ignore_index=True)
    conn.update(worksheet='messaggi', data=new_m)
    
    st.cache_data.clear()
    st.rerun()

# --- CHAT (Visualizzazione Immagine Robusta) ---
st.title('📜 Cronaca dell\'Abisso')
for _, r in df_m.tail(20).iterrows():
    with st.chat_message("assistant" if r['autore'] == 'Master' else "user"):
        if str(r['testo']).startswith('IMG|'):
            try:
                parts = str(r['testo']).split('|')
                if len(parts) >= 3:
                    st.write(f"***{parts[1]}***")
                    # Se l'immagine fallisce, mostra un avviso invece della thumb rotta
                    st.image(parts[2], use_container_width=True)
            except Exception:
                st.warning("L'immagine di questa zona è in fase di evocazione...")
        else:
            st.markdown(r['testo'], unsafe_allow_html=True)
