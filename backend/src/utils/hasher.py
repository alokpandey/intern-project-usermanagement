import bcrypt


def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    password_bytes = password.encode("utf-8")
    hashed_password = bcrypt.hashpw(password_bytes, salt)
    hashed_password = hashed_password.decode("utf-8")
    return hashed_password

def check_password(password: str, hashed_password: str) -> bool:
    password_bytes = password.encode("utf-8")
    hashed_password = hashed_password.encode("utf-8")
    return bcrypt.checkpw(password_bytes, hashed_password)
