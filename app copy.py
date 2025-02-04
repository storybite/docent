import streamlit as st
import streamlit.components.v1 as components

# 레이아웃을 Wide 모드로 설정
st.set_page_config(page_title="Chat with an Image", layout="wide")

# 세션 상태 초기화
if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []
if "run_scroll" not in st.session_state:
    st.session_state["run_scroll"] = False

# 2단 컬럼 레이아웃
col_image, col_chat = st.columns([1, 2])

with col_image:
    st.image("images/그림1.png", use_container_width=True)

with col_chat:
    st.header("챗봇과 대화하기")

    # 채팅 UI 컨테이너
    chat_container = st.container()

    # 입력 UI
    user_input = st.text_input("질문을 입력하세요")
    if st.button("Send"):
        if user_input:
            st.session_state["chat_history"].append(("user", user_input))
            bot_reply = f"'{user_input}' 라고 하셨네요. (예시 답변)"
            st.session_state["chat_history"].append(("bot", bot_reply))
            # 스크롤 스크립트 실행을 위한 플래그 활성화
            st.session_state["run_scroll"] = True

    # 채팅 메시지 표시 영역
    with st.container():
        # CSS 스타일 적용
        st.markdown(
            """
            <style>
            .chat-container {
                height: 400px;
                overflow-y: auto;
                border: 1px solid #ccc;
                border-radius: 5px;
                padding: 15px;
                margin-bottom: 20px;
                background-color: #FAFAFA;
            }
            .message {
                margin: 10px 0;
                padding: 8px;
                border-radius: 5px;
            }
            .user-message {
                background-color: #E3F2FD;
            }
            .bot-message {
                background-color: #F5F5F5;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )

        # 채팅 내역 HTML 생성
        chat_html = '<div class="chat-container">'
        for role, msg in st.session_state["chat_history"]:
            if role == "user":
                chat_html += f'<div class="message user-message"><strong>사용자:</strong> {msg}</div>'
            else:
                chat_html += f'<div class="message bot-message"><strong>챗봇:</strong> {msg}</div>'
        chat_html += "</div>"

        st.markdown(chat_html, unsafe_allow_html=True)

    # 스크롤 스크립트를 플래그가 True일 때 실행 (고유 key를 주어 새 컴포넌트로 인식)
    if st.session_state.get("run_scroll"):
        dummy = len(st.session_state["chat_history"])
        scroll_script = f"""
        <script>
            // 부모 문서의 채팅 컨테이너 선택
            var chatContainer = parent.document.querySelector(".chat-container");
            if(chatContainer){{
                // 렌더링이 완료된 후 스크롤 이동 (100ms 지연)
                setTimeout(function(){{
                    chatContainer.scrollTop = chatContainer.scrollHeight;
                }}, 0);
            }}
        </script>
        """
        components.html(
            scroll_script,
            height=0,
        )
        # 실행 후 플래그 초기화
        st.session_state["run_scroll"] = False
