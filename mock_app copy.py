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
            width: 40rem !important;
        }          
        
        .intro-text {
            text-align: center; 
            padding: 20px; 
            margin-top: 20px; 
            border-radius: 10px; 
            background-color: #f9f9f9; 
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        
        .image-box {
            display: flex;
            flex-direction: column;
            align-items: center;
        }

        .image-header {
            font-weight: bold;
            font-size: 18px;
            color: #333;
            margin-top: -20px;
        }

        .image-title {
            font-weight: bold;
            font-size: 18px;
            margin-bottom: 15px;
            color: #333;
        }

        /* 채팅 메시지 컨테이너의 최대 너비 조정 */
        .stChatInput {
            margin-left: -5rem;
        }

       
    </style>
    """,
    unsafe_allow_html=True,
)

how_to_use = """
### 사용 방법
1. 작품에 대해 궁금한 점을 입력해주세요
2. AI 도슨트가 전문적인 설명을 제공합니다

### 예시 질문
- 이 작품의 작가는 누구인가요?
- 작품의 제작 기법에 대해 설명해주세요
- 작품의 역사적 배경은 무엇인가요?
- 작품에 담긴 상징적 의미는 무엇인가요?
"""


def init_page():

    # 사이드바 설정
    with st.sidebar:
        st.markdown(how_to_use)

    # 카드 형태의 안내문구
    st.markdown(
        """
        <div class="intro-text">
            <h2>e-뮤지엄 도슨트 챗봇입니다</h2>
            <p>안녕하세요! 저희 e-뮤지엄에 오신 것을 환영합니다.<p>
            <p>
                저는 e-박물관에서 일하는 도슨트 챗봇이에요.
                이곳에서는 500여 여종의 대한민국 국보/보물 이미지를 보관하고 있습니다. 역사와 배경은 물론 저의 감상까지도 자세히 말씀드려요!
            </p>
            <p>
                아래의 <strong>‘입장하기’</strong> 버튼을 눌러 투어를 시작해 보세요!
            </p>            
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 3개의 컬럼으로 나눈 후 가운데에만 버튼을 배치하여 중앙 정렬
    col_left, col_center, col_right = st.columns([1, 2, 1])
    with col_center:
        if st.button("입장하기", use_container_width=True, type="primary"):
            # docent_bot.first_relic()
            print("입장하기 버튼이 클릭되었습니다.")
            st.rerun()


def main_page():

    def side_bar():
        # 사이드바 설정
        with st.sidebar:

            header, img_path, title = (
                st.session_state.current_relic["header"],
                st.session_state.current_relic["img_path"],
                st.session_state.current_relic["title"],
            )

            with open(img_path, "rb") as img_file:
                img_base64 = base64.b64encode(img_file.read()).decode()

            st.markdown(
                f'<div class="image-box">'
                f'<div class="image-header">{header}</div>'
                f'<img src="data:image/png;base64,{img_base64}" style="width:375px; height:500px; object-fit:contain;">'
                f'<div class="image-title">{title}</div>'
                f"</div>",
                unsafe_allow_html=True,
            )

            _, col_left, _, col_right, _ = st.columns(
                [5, 5, 1, 5, 5]
            )  # 네비게이션 버튼
            with col_left:
                if st.button("이전", use_container_width=True):
                    print("이전 버튼이 클릭되었습니다.")
                    st.session_state.current_relic = st.session_state.relics[0]
                    st.rerun()

            with col_right:
                if st.button("다음", use_container_width=True):
                    print("다음 버튼이 클릭되었습니다.")
                    st.session_state.current_relic = st.session_state.relics[1]
                    st.rerun()

            st.markdown("---")
            st.markdown(how_to_use)

    def chat_area():
        user_message = st.chat_input("메시지를 입력하세요.")
        if user_message:
            with st.chat_message("user"):
                st.markdown(user_message)
            with st.chat_message("assistant"):
                st.markdown("도슨트봇 테스트 메시지입니다.")

    side_bar()
    chat_area()


if "entered" not in st.session_state:
    init_page()
    st.session_state.entered = True
    st.session_state.relics = [
        {
            "header": "1번 전시물",
            "img_path": "images/relic1.png",
            "title": "100점 중 1번째 이미지",
        },
        {
            "header": "2번 전시물",
            "img_path": "images/relic2.png",
            "title": "100점 중 2번째 이미지",
        },
    ]
    st.session_state.current_relic = st.session_state.relics[0]
else:
    main_page()
    st.session_state.entered = False
