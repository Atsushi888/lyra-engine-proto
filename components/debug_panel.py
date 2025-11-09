# components/debug_panel.py

import streamlit as st


class DebugPanel:
    def render(self, llm_meta):
        st.subheader("🧠 LLM デバッグ")

        if not llm_meta:
            st.write("（まだレスポンスがありません）")
            return

        gpt4o = llm_meta.get("gpt4o")
        hermes = llm_meta.get("hermes")
        
        if gpt4o or hermes:
            st.markdown("### モデル比較：GPT-4o vs Hermes")
            col1, col2 = st.columns(2)
        
            with col1:
                st.markdown("#### GPT-4o")
                if gpt4o:
                    st.text_area("gpt4o_reply", gpt4o["reply"], height=240, label_visibility="collapsed")
                else:
                    st.text("（GPT-4o の結果なし）")
        
            with col2:
                st.markdown("#### Hermes")
                if hermes:
                    st.text_area("hermes_reply", hermes["reply"], height=240, label_visibility="collapsed")
                else:
                    st.text("（Hermes の結果なし）")
        else:
            st.write("（どちらのモデルの結果もありません）")
