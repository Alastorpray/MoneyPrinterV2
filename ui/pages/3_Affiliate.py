import sys
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

import streamlit as st
from uuid import uuid4
from cache import get_accounts, get_products, add_product

st.set_page_config(page_title="Affiliate - MoneyPrinter V2", page_icon="🛒", layout="wide")

st.markdown("# 🛒 Affiliate Marketing")
st.markdown("---")

# --- Tabs ---
tab_products, tab_campaign = st.tabs(["📦 Productos", "🚀 Ejecutar Campana"])

# ============================
# TAB: Productos
# ============================
with tab_products:
    products = get_products()

    if products:
        st.markdown("### Productos registrados")
        for idx, prod in enumerate(products):
            with st.container():
                cols = st.columns([1, 3, 2])
                cols[0].markdown(f"**#{idx + 1}**")
                cols[1].markdown(f"🔗 `{prod['affiliate_link'][:50]}...`")
                cols[2].markdown(f"🐦 UUID: `{prod['twitter_uuid'][:8]}...`")
            st.markdown("---")
    else:
        st.info("No hay productos registrados. Agrega uno abajo.")

    with st.expander("➕ Agregar producto", expanded=len(products) == 0):
        twitter_accounts = get_accounts("twitter")

        if not twitter_accounts:
            st.warning("Necesitas al menos una cuenta de Twitter configurada. Ve a la seccion Twitter primero.")
        else:
            with st.form("add_product"):
                affiliate_link = st.text_input("Link de afiliado (Amazon)", placeholder="https://amazon.com/dp/...")
                tw_names = [f"{acc['nickname']} ({acc['topic']})" for acc in twitter_accounts]
                tw_idx = st.selectbox("Cuenta de Twitter", range(len(twitter_accounts)),
                                       format_func=lambda i: tw_names[i])

                if st.form_submit_button("Agregar producto", type="primary"):
                    if not affiliate_link:
                        st.error("El link de afiliado es requerido.")
                    else:
                        selected_tw = twitter_accounts[tw_idx]
                        add_product({
                            "id": str(uuid4()),
                            "affiliate_link": affiliate_link,
                            "twitter_uuid": selected_tw["id"],
                        })
                        st.success("Producto agregado exitosamente!")
                        st.rerun()

# ============================
# TAB: Ejecutar Campana
# ============================
with tab_campaign:
    products = get_products()
    twitter_accounts = get_accounts("twitter")

    if not products:
        st.warning("Primero agrega un producto en la pestana 'Productos'.")
    elif not st.session_state.get("model_ready"):
        st.warning("Selecciona un modelo Ollama en la barra lateral primero.")
    else:
        prod_names = [f"#{i+1} - {p['affiliate_link'][:50]}..." for i, p in enumerate(products)]
        prod_idx = st.selectbox("Seleccionar producto", range(len(products)),
                                 format_func=lambda i: prod_names[i])
        selected_product = products[prod_idx]

        # Find linked Twitter account
        linked_account = None
        for acc in twitter_accounts:
            if acc["id"] == selected_product["twitter_uuid"]:
                linked_account = acc
                break

        if linked_account is None:
            st.error("La cuenta de Twitter vinculada no fue encontrada. Verifica la configuracion.")
        else:
            st.markdown(f"**Producto:** {selected_product['affiliate_link'][:60]}")
            st.markdown(f"**Cuenta Twitter:** {linked_account['nickname']} ({linked_account['topic']})")

            if st.button("🚀 Generar Pitch y Compartir", type="primary"):
                try:
                    with st.status("Ejecutando campana...", expanded=True) as status:
                        st.write("🔧 Iniciando navegador y scraping del producto...")
                        from classes.AFM import AffiliateMarketing

                        afm = AffiliateMarketing(
                            selected_product["affiliate_link"],
                            linked_account["firefox_profile"],
                            linked_account["id"],
                            linked_account["nickname"],
                            linked_account["topic"],
                        )

                        try:
                            st.write("📝 Generando pitch con IA...")
                            afm.generate_pitch()

                            if hasattr(afm, "pitch"):
                                st.write("**Pitch generado:**")
                                st.info(afm.pitch)

                            st.write("📤 Compartiendo en Twitter...")
                            afm.share_pitch("twitter")

                            status.update(label="Campana ejecutada!", state="complete")
                            st.success("Pitch generado y compartido exitosamente!")
                            st.balloons()
                        finally:
                            try:
                                afm.browser.quit()
                            except Exception:
                                pass
                except Exception as e:
                    st.error(f"Error: {e}")
