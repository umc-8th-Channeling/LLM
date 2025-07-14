from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/reports", tags=["reports"])


@router.post("")
async def create_report() -> int:
    """
    리포트 생성을 시작합니다.
    parameters:
        None
    returns:
        task_id: int
    """
    ...