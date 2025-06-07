# 🎨 AI 도슨트 챗봇

미술 작품에 대한 전문적인 설명을 제공하는 AI 도슨트 챗봇입니다.

## 기능

- 작품에 대한 상세한 설명 제공
- 작가와 작품의 역사적 배경 설명
- 작품의 기법과 상징적 의미 해석
- 대화형 인터페이스로 자연스러운 상호작용

## 설치 방법

1. 저장소 클론
```bash
git clone [repository-url]
cd docent
```

2. 가상환경 활성화
```bash
python -m venv dcnt_venv
source dcnt_venv/Scripts/activate  # Windows
# source dcnt_venv/bin/activate  # Mac/Linux
```

3. 필요한 패키지 설치
```bash
pip install -r requirements.txt
```

4. 환경 변수 설정
- `.env` 파일을 생성하고 Anthropic API 키를 설정
```
ANTHROPIC_API_KEY=your_api_key_here
```

## 실행 방법

```bash
streamlit run app.py
```

## 기술 스택

- Python 3.12.1
- Streamlit
- Anthropic Claude API
- python-dotenv

## 라이선스

MIT License 