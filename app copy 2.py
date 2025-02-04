import streamlit as st


# CSS를 사용하여 우측 고정 박스 생성
st.markdown(
    """
    <style>
        .fixed-box {
            position: fixed;
            top: 100px;
            right: 20px;
            width: 300px;
            height: 200px;
            background-color: #f1f1f1;
            padding: 15px;
            border-radius: 10px;
            box-shadow: 2px 2px 10px rgba(0,0,0,0.1);
            z-index: 100;
        }
    </style>
    <div class="fixed-box">
        <h4>고정된 박스</h4>
        <p>여기에 원하는 내용을 입력하세요.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# 세션 상태에 대화 내역 초기화 (리스트 형태로 저장)
if "chat_session" not in st.session_state:
    st.session_state.chat_session = []

# 저장된 대화 내역을 화면에 표시
for message in st.session_state.chat_session:
    with st.chat_message(message["role"]):
        st.markdown(message["text"])

# 사용자 입력창 (메시지를 입력하면 바로 처리)
prompt = st.chat_input("메시지를 입력하세요.")
if prompt:
    # 사용자 메시지 저장 및 표시
    st.session_state.chat_session.append({"role": "user", "text": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 에코 응답: 사용자 입력을 그대로 챗봇 응답으로 사용
    response = prompt
    st.session_state.chat_session.append({"role": "ai", "text": response})
    with st.chat_message("ai"):
        st.markdown(response)
