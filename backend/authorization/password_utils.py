import bcrypt
from exceptions.custom_exceptions import BcryptError

def hash_password(raw_pass: str) -> str:
    try:
        salt = bcrypt.gensalt()
        bytes = raw_pass.encode()
        hashed_password = bcrypt.hashpw(bytes, salt)
        return hashed_password.decode()
    except Exception as e:
        raise BcryptError(f"Bcrypt: password encoding failed.")

def check_password(entered_pass: str, hashed_pass: str) -> bool:
    try:
        return bcrypt.checkpw(entered_pass.encode(), hashed_pass.encode())
    except Exception as e:
        raise BcryptError("Bcrypt: check password failed.")