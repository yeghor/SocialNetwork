from fastapi import APIRouter, Depends
from databases_manager.postgres_manager.database_utils import get_session_depends
from databases_manager.main_databases_manager import MainService
from sqlalchemy.ext.asyncio import  AsyncSession

auth = APIRouter()

@auth.get("/")
async def test(session: AsyncSession = Depends(get_session_depends)):
    service = await MainService.initialize(postgres_session=session)
                                    
    users = await service.get_all_users()
