import smtplib
from email.message import EmailMessage
from src.utils.otp_genrator import generate_otp
import os 
from dotenv import load_dotenv
from ..session import redis_client

load_dotenv()

sender_email = os.getenv("SENDER_EMAIL")
email_password = os.getenv("EMAIL_PASSWORD")
print(email_password)

def send_email_verification(email: str, user_id: int):
    otp = generate_otp()
    FROM = sender_email
    PASSWORD=email_password
    TO = [email]
    TEXT = f"""The Below is you OTP for user registration 
            Please Do not share it with others.
            The otp is valid for 2 minutes only. 
            Your OTP is {otp} 
            If you did not request this, please ignore this email.
            Thank You."""
    
    SUBJECT = "Email Verification"
    message = EmailMessage()
    message.set_content(TEXT)
    message['Subject'] = SUBJECT
    message['From'] = FROM
    message['To'] = TO

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
                smtp.login(FROM, PASSWORD)
                smtp.send_message(message)
                redis_client.set(f"otp_{user_id}", otp, ex=120)
                return True
    except Exception as e:
        print(e)
        return False