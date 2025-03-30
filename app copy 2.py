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
        .stSidebar {
            width: 380px !important;
        }
        
        /* 채팅 메시지 컨테이너의 최대 너비 조정 */
        .stChatMessage {
            margin-left: -270px;
            width: 100%;
        }

        /* Streamlit 기본 입력창 스타일 조정 */
        .stChatInput {
            margin-left: -270px;
            padding-right: 100px;            
        }
        
        /* 고정 박스 스타일 */
        .st-key-image-container {
            position: fixed;
            top: 60px;
            right: 0px;
            width: 420px;
            /*height: 650px;*/
            height: 100%;
            background-color: #f1f1f1;            
            z-index: 100;
            display: flex;
            flex-direction: column;
            align-items: center;
        }

        .image-title {
            font-weight: bold;
            font-size: 18px;
            margin: 15px 0;
            color: #333;
        }

        .disable_overlay {
            position: fixed;
            top: 0; 
            left: 0;
            width: 100%;
            height: 100%;
            z-index: 9998; 
            background-color: rgba(0,0,0,0);
            box-shadow: 2px 2px 10px rgba(0,0,0,0);
        }

        .stSpinner {
            position: fixed;
            left: 50%;
            top: 50%;
            transform: translate(-50%, -50%);            
            margin: 0 auto;
            width: 350px;
            font-size: 20px;
            font-weight: bold;
            z-index: 9999; /* 최상단에 위치 */
        }

        .intro-text {
            text-align: center; 
            padding: 2rem; 
            margin-top: 2rem; 
            border-radius: 0.5rem; 
            background-color: #f9f9f9; 
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
       
    </style>
    """,
    unsafe_allow_html=True,
)


def on_progress(func):

    overlay_placeholder = st.empty()
    # 다음 이미지로 이동
    overlay_placeholder.markdown(
        """
        <div class="disable_overlay"></div>
        """,
        unsafe_allow_html=True,
    )
    with st.spinner("잠시만 기다려주세요."):
        result = func()

    overlay_placeholder.empty()
    return result


# 세션 상태에 대화 내역 초기화
if "docent_bot" not in st.session_state:
    docent_bot = DocentBot()
    st.session_state.docent_bot = docent_bot
else:
    docent_bot = st.session_state.docent_bot

if docent_bot.visitor_status == "NotEntered":
    # 카드 형태의 안내문구
    st.markdown(
        """
        <div class="intro-text">
            <h2>도슨트 안내</h2>
            <p>안녕하세요! 저는 AI 도슨트봇입니다.</p>
            <p>이곳에서는 다양한 작품들의 역사와 배경, 흥미로운 이야기를 소개해 드려요.</p>
            <p>아래의 <strong>‘입장하기’</strong> 버튼을 눌러 투어를 시작해 보세요!</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    # '입장하기' 버튼
    # 3개의 컬럼으로 나눈 후 가운데에만 버튼을 배치하여 중앙 정렬
    col_left, col_center, col_right = st.columns([1, 2, 1])
    with col_center:
        if st.button("입장하기", use_container_width=True):
            docent_bot.first_relic()
            docent_bot.visitor_status = "Entered"
            on_progress(lambda: docent_bot.request_presentaion())
            st.rerun()
else:
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

    # 이미지 컨테이너 생성
    with st.container(key="image-container"):

        title, img_path = (
            docent_bot.get_current_relic()["title"],
            docent_bot.get_current_relic()["img"],
        )

        with open(img_path, "rb") as img_file:
            img_base64 = base64.b64encode(img_file.read()).decode()

        st.markdown(
            f'<div style="display:flex; flex-direction: column; align-items: center;">'
            f'<img src="data:image/png;base64,{img_base64}" style="width: 375px; height: 500px; object-fit: contain;">'
            f'<div class="image-title">{title}</div>'
            f"</div>",
            unsafe_allow_html=True,
        )

        # 3단계: 좌우 이동 버튼
        col1, col3 = st.columns([3, 3])
        with col1:
            if st.button("이전"):
                docent_bot.move(next=False)
                on_progress(lambda: docent_bot.request_presentaion())
                st.rerun()
        with col3:
            if st.button("다음"):
                docent_bot.move(next=True)
                on_progress(lambda: docent_bot.request_presentaion())
                st.rerun()

    for message in docent_bot.get_conversation():
        with st.chat_message(message["role"]):
            st.markdown(message["text"])

    user_message = st.chat_input("메시지를 입력하세요.")
    if user_message:
        with st.chat_message("user"):
            st.markdown(user_message)
        docent_answer = on_progress(lambda: docent_bot.answer(user_message))
        with st.chat_message("assistant"):
            st.markdown(docent_answer)
