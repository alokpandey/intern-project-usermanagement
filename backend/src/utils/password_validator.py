import re

def validate_password(password: str):
    if len(password) < 8:
        return False
    if len(password) > 128:
        return False
    if " " in password:
        return False
    if not re.search(r"[A-Z]", password):
        return False

    if not re.search(r"[a-z]", password):
        return False

    if not re.search(r"[0-9]", password):
        return False
     
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return False
    return True