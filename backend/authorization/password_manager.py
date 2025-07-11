import bcrypt

def hash_password(raw_pass: str) -> str:
    salt = bcrypt.gensalt()
    bytes = raw_pass.encode()
    hashed_password = bcrypt.hashpw(bytes, salt)
    return hashed_password.decode()

def check_password(entered_pass: str, hashed_pass: str) -> bool:
    return bcrypt.checkpw(entered_pass.encode(), hashed_pass.encode())