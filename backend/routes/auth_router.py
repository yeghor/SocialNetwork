from fastapi import APIRouter

auth = APIRouter()

@auth.get("/")
def test() -> int:
    return 42