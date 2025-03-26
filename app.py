import streamlit as st
from PIL import Image
import base64
from pathlib import Path
from docent import DocentBot

# Streamlit 페이지 설정
st.set_page_config(page_title="도슨트 봇", page_icon="🎭", layout="centered")

# CSS를 사용하여 메시지 너비 조절 & 우측 고정 박스 유지
st.markdown(
    """
    <style>        
        /* 채팅 메시지 컨테이너의 최대 너비 조정 */
        .stChatMessage {
            margin-left: -200px;
            width: 100%;
        }

        /* Streamlit 기본 입력창 스타일 조정 */
        .stChatInput {
            margin-left: -200px;
            padding-right: 100px;
            
            
        }

        /* 고정 박스 스타일 */
        .fixed-box {
            position: fixed;
            top: 60px;
            right: 0px;
            width: 480px;
            height: 73%;
            background-color: #f1f1f1;
            padding: 15px;
            border-radius: 0px;
            border: 10px solid white;
            box-shadow: 2px 2px 10px rgba(0,0,0,0.1);
            z-index: 100;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


def img_to_base64(img_path):
    with open(img_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode()


# 세션 상태에 대화 내역 초기화
if "docent_bot" not in st.session_state:
    st.session_state.docent_bot = DocentBot()
    docent_bot = st.session_state.docent_bot
else:
    docent_bot = st.session_state.docent_bot


# 이미지를 base64로 변환
def render_image():
    img_path = docent_bot.get_image_path()
    img_base64 = img_to_base64(img_path)

    # 고정 박스 생성 (base64 이미지 포함)
    st.markdown(
        f"""
        <div class="fixed-box">
            <img src="data:image/png;base64,{img_base64}" width="100%">
        </div>
        """,
        unsafe_allow_html=True,
    )


render_image()

# 저장된 대화 내역을 화면에 표시 (메시지 너비 조절)
for message in docent_bot.get_conversation():
    with st.chat_message(message["role"]):
        # st.markdown(
        #     f'<div class="chat-container">{message["text"]}</div>',
        #     unsafe_allow_html=True,
        # )
        st.markdown(message["text"].replace("[네]", "네,"))

# 사용자 입력창
user_message = st.chat_input("메시지를 입력하세요.")
if user_message:
    with st.chat_message("user"):
        st.markdown(user_message)

    # 사용자 메시지 저장 및 표시
    response_message = docent_bot.answer(user_message)
    if "[네]" in response_message:
        render_image()
        response_message = response_message.replace("[네]", "네,")

    # 에코 응답 (AI 응답도 동일한 스타일 적용)
    # response_message = f"AI 응답: {response_message}"

    with st.chat_message("assistant"):
        st.markdown(response_message)

# 사이드바 설정
with st.sidebar:
    st.title("🎭반가워요. 도슨트봇입니다.")
    st.markdown(
        """
    ### 사용 방법
    1. 작품에 대해 궁금한 점을 입력해주세요
    2. AI 도슨트가 전문적인 설명을 제공합니다
    
    ### 예시 질문
    - 이 작품의 작가는 누구인가요?
    - 작품의 제작 기법에 대해 설명해주세요
    - 작품의 역사적 배경은 무엇인가요?
    - 작품에 담긴 상징적 의미는 무엇인가요?
    """
    )
