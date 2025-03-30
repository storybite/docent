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
            right: 10px;
            width: 480px;
            height: 650px;
            background-color: #f1f1f1;
            padding: 15px;
            border-radius: 0px;
            border: 10px solid white;
            box-shadow: 2px 2px 10px rgba(0,0,0,0.1);
            z-index: 100;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
        }

        .image-title {
            font-weight: bold;
            font-size: 18px;
            margin: 15px 0;
            color: #333;
        }

        /* 이미지 래퍼: 왼쪽 정렬 */
        .image-wrapper {
            /* 가운데 정렬 안 하려면 flex 속성 제거 */
            margin: 10px 0;
        }
        
    </style>
    """,
    unsafe_allow_html=True,
)


def img_to_base64(img_path):
    with open(img_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode()


def render_image(title: str, img_path: str, is_presenting: bool):
    # 이미지 컨테이너 생성
    with st.container(key="image-container"):

        img_base64 = img_to_base64(img_path)

        # 2단계: 이미지 레이블/설명
        st.markdown(
            f'<div style="display: flex; flex-direction: column; align-items: center;">'
            f'<img src="data:image/png;base64,{img_base64}" style="width: 375px; height:500px; object-fit: contain; max-width: 100%;">'
            f'<div class="image-title">{title}</div>'
            f"</div>",
            unsafe_allow_html=True,
        )

        # 3단계: 좌우 이동 버튼
        col1, col3 = st.columns([3, 3])
        with col1:
            if st.button("◀ 이전"):
                docent_bot.previous_image()  # 이전 이미지로 이동하는 함수 호출
                st.rerun()
        with col3:
            if st.button("다음 ▶"):
                # 다음 이미지로 이동
                docent_bot.next_image()  # 다음 이미지로 이동하는 함수 호출
                # 작품 설명 생성 (이 작업 중에는 UI가 응답하지 않음)
                docent_bot.present_relic()
                # 페이지 새로고침 (버튼 상태 초기화)
                st.rerun()


# def render_door():
#     with st.container(key="image-container"):

#         img_base64 = img_to_base64("./scrap/relics/door.png")

#         # st.markdown(
#         #     f'<div style="display: flex; flex-direction: column; align-items: center;">'
#         #     f'<img src="data:image/png;base64,{img_base64}" style="width: 400px; height:550px">'
#         #     f"</div>",
#         #     unsafe_allow_html=True,
#         # )

#         # 수직 가운데 정렬을 위한 빈 공간 추가
#         st.markdown("<div style='height: 30vh;'></div>", unsafe_allow_html=True)

#         col1, col2, col3 = st.columns([1, 10, 1])
#         with col2:
#             if st.button("입장하기"):
#                 docent_bot.next_image()
#                 st.rerun()


# 세션 상태에 대화 내역 초기화
if "docent_bot" not in st.session_state:
    st.session_state.docent_bot = DocentBot()
    docent_bot = st.session_state.docent_bot
    # render_image(title="반갑습니다!", img_path="./scrap/relics/door.png", is_open=True)
    # render_door()
else:
    docent_bot = st.session_state.docent_bot


# # 이미지를 base64로 변환하고, 작품 이미지를 표시하는 함수
# def render_image():
#     img_path = docent_bot.get_image_path()  # 이미지 경로
#     img_base64 = img_to_base64(img_path)
#     title = docent_bot.get_label()  # 작품 제목 가져오기

#     with st.container(key="image-container"):
#         # 고정 박스 생성 (base64 이미지 + 제목 표시)
#         st.markdown(
#             f"""
#             <div class="fixed-box">
#                 <img src="data:image/png;base64,{img_base64}" width="100%">
#                 <p style="text-align: center; margin-top: 50px; font-weight: bold; font-size: 16px;">{title}</p>
#             </div>
#             """,
#             unsafe_allow_html=True,
#         )
#         st.button("◀ 이전", key="prev-btn")  # st.button default type is secondary
#         st.button("다음 ▶", key="next-btn")  # st.button default type is secondary
#         st.markdown(
#             f"""
#             </div>
#             """,
#             unsafe_allow_html=True,
#         )


# 저장된 대화 내역을 화면에 표시
for message in docent_bot.get_conversation():
    with st.chat_message(message["role"]):
        st.markdown(message["text"].replace("[네]", "네,"))


# # 메시지 입력 영역 위에 네비게이션 버튼 추가
# col1, col2, col3 = st.columns([1, 3, 1])
# # 사용자 정의 클래스로 감싸기
# with st.container():
#     if st.button("◀ 이전", use_container_width=True):
#         docent_bot.previous_image()
#     if st.button("다음 ▶", use_container_width=True):
#         docent_bot.next_image()

# st.button("b1", type="primary")  # st.button default type is secondary
# st.button("b2")

# # 메시지 입력 영역 위에 네비게이션 버튼 추가
# col1, col2, col3 = st.columns([1, 3, 1])
# with col1:
#     # 사용자 정의 클래스로 감싸기
#     with st.container():
#         st.markdown('<div class="prev-button">', unsafe_allow_html=True)
#         if st.button("◀ 이전", use_container_width=True):
#             docent_bot.previous_image()
#         st.markdown("</div>", unsafe_allow_html=True)

# with col3:
#     # 사용자 정의 클래스로 감싸기
#     with st.container(key="abc"):
#         st.markdown('<div class="next-button">', unsafe_allow_html=True)
#         if st.button("다음 ▶", use_container_width=True):
#             docent_bot.next_image()
#         st.markdown("</div>", unsafe_allow_html=True)

# # 컨테이너에 요소 추가하기
# container.write("이 텍스트는 컨테이너 안에 들어갑니다")
# container.button("컨테이너 내 버튼")

# 사용자 입력창
user_message = st.chat_input("메시지를 입력하세요.")
if user_message:
    with st.chat_message("user"):
        st.markdown(user_message)

    # 사용자 메시지 처리
    response_message = docent_bot.answer(user_message)
    # if "[네]" in response_message:
    #     render_image()
    #     response_message = response_message.replace("[네]", "네,")

    with st.chat_message("assistant"):
        st.markdown(response_message)


if "has_entered" not in st.session_state:
    col1, col2, col3 = st.columns([1, 10, 1])
    with col2:
        if st.button("입장하기"):
            st.session_state.has_entered = True
            # docent_bot.next_image()
            # title, img_path = docent_bot.get_relic_info()
            # render_image(title=title, img_path=img_path, is_presenting=True)
            docent_bot.next_image()  # 다음 이미지로 이동하는 함수 호출
            docent_bot.present_relic()
            title, img_path = docent_bot.get_relic_info()
            render_image(title=title, img_path=img_path, is_presenting=True)
            st.rerun()
else:
    title, img_path = docent_bot.get_relic_info()
    render_image(title=title, img_path=img_path, is_presenting=False)

#     title, img_path = docent_bot.get_relic_info()
#     response_message = docent_bot.present_relic()
#     render_image(title=title, img_path=img_path, is_open=False)
#     with st.chat_message("assistant"):
#         st.markdown(response_message)


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
