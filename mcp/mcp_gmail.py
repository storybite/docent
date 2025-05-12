from mcp.server.fastmcp import FastMCP
import smtplib
from email.mime.text import MIMEText
from pydantic import Field

mcp = FastMCP()

body_template = """
안녕하세요? 요청하셨던 문화해설사 예약이 완료되었습니다.

일시: {meeting_date}
장소: {meeting_location}

1. 문화해설사 정보:
- 이름: {docent_name}
- 연락처: {docent_email}

2. 요청자 정보
- 이름: {visitor_name}
- 연락처: {visitor_email}

감사합니다.
""".strip()


@mcp.tool()
def confirm_meeting(
    meeting_date: str = Field(description="미팅 일시(YYYY-MM-DD HH:MM)"),
    meeting_location: str = Field(description="미팅 장소"),
    docent_name: str = Field(description="해설사 이름"),
    visitor_name: str = Field(description="요청자 이름"),
):
    """
    미팅 예약 확정 메일을 발송합니다.
    """
    ...


@mcp.tool()
def program_breifing(
    meeting_date: str = Field(description="미팅 일시(YYYY-MM-DD HH:MM)"),
    meeting_location: str = Field(description="미팅 장소"),
    docent_name: str = Field(description="해설사 이름"),
    visitor_name: str = Field(description="요청자 이름"),
):
    """
    미팅 브리핑 확정 메일을 발송합니다.
    """
    ...


@mcp.tool()
def program_breifing(
    meeting_date: str = Field(description="미팅 일시(YYYY-MM-DD HH:MM)"),
    meeting_location: str = Field(description="미팅 장소"),
    docent_name: str = Field(description="해설사 이름"),
    visitor_name: str = Field(description="요청자 이름"),
):
    """
    미팅 브리핑 확정 메일을 발송합니다.
    """
    ...


@mcp.tool()
def wrtie_mail_body(
    meeting_date: str = Field(description="미팅 일시(YYYY-MM-DD HH:MM)"),
    meeting_location: str = Field(description="미팅 장소"),
    docent_name: str = Field(description="해설사 이름"),
    docent_email: str = Field(description="해설사 이메일"),
    visitor_name: str = Field(description="요청자 이름"),
    visitor_email: str = Field(description="요청자 이메일"),
):
    """
    이메일 본문을 작성합니다.
    """
    body = body_template.format(
        meeting_date=meeting_date,
        meeting_location=meeting_location,
        docent_name=docent_name,
        docent_email=docent_email,
        visitor_name=visitor_name,
        visitor_email=visitor_email,
    )
    return body


@mcp.tool()
def send_mail(
    sender: str = Field(description="예약 에이전트 이메일"),
    receiver: str = Field(description="신청자 이메일"),
    body: str = Field(description="메일의 내용"),
    cc: str = Field(description="도슨트 이메일"),
):
    """
    신청자에게 이메일을 발송합니다. 도슨트에게는 참조로 발송합니다.
    """
    # sender = "bigblogger73@gmail.com"
    # receiver = "minjigobi@gmail.com"
    subject = "안녕하세요, 문화해설사 예약이 완료되었습니다."
    # body = _body
    # cc = "heyjin337@gmail.com"

    # 모든 수신자를 리스트에 포함
    recipients = [receiver, cc]
    msg = MIMEText(body)  # 단순 텍스트 본문
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = receiver
    msg["Cc"] = cc

    # Gmail SMTP: smtp.gmail.com, 포트 587(STARTTLS) 사용
    smtp_server = smtplib.SMTP("smtp.gmail.com", 587)
    smtp_server.ehlo()  # 서버 연결 식별
    smtp_server.starttls()  # TLS(보안) 연결 시작
    smtp_server.login(sender, "qgpe dlcj jfar peyc")

    smtp_server.sendmail(sender, recipients, msg.as_string())
    smtp_server.quit()
    print("메일 전송 완료")


if __name__ == "__main__":
    send_mail()
