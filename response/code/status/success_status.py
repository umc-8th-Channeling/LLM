from enum import Enum
from fastapi import status

class SuccessStatus(Enum):
    """
    성공 상태 코드 정의
    """
    
    # 일반적인 성공
    _OK = (status.HTTP_200_OK, "SUCCESS200", "요청이 성공적으로 처리되었습니다.")
    _CREATED = (status.HTTP_201_CREATED, "SUCCESS201", "리소스가 성공적으로 생성되었습니다.")
    

    # 리포트 관련 성공
    _REPORT_CREATED = (status.HTTP_201_CREATED, "REPORT201", "리포트가 성공적으로 생성되었습니다.")


    def get_reason(self):
        """
        성공 메시지 반환
        """
        return {
            "message": self.value[2],
            "code": self.value[1],
            "isSuccess": True,
            "status": self.value[0]
        }