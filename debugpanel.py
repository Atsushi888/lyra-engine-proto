class DebugPanel:
    """直近の LLM 呼び出しメタ情報を表示するための小さなヘルパ"""
    def __init__(self, state_key: str = "_last_call_meta"):
        self.state_key = state_key

    def set_meta(self, meta: dict) -> None:
        if meta:
            st.session_state[self.state_key] = meta

    def clear(self) -> None:
        st.session_state.pop(self.state_key, None)

    def render(self) -> None:
        show_dbg = st.checkbox("デバッグを表示", False)
        if not show_dbg:
            return
        if self.state_key not in st.session_state:
            st.info("まだ LLM 呼び出し情報はありません。")
            return
        st.markdown("###### 最後の呼び出し情報")
        st.json(st.session_state[self.state_key])
