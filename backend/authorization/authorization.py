from fastapi import HTTPException, Header

async def authorize_depends(jwt_token: str = Header()):
    pass