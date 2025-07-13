from enum import Enum
from fastapi import status

class ErrorStatus(Enum):
    """
    에러 상태 코드 정의
    """

    # 일반적인 에러
    INTERNAL_SERVER_ERROR = (status.HTTP_500_INTERNAL_SERVER_ERROR,"COMMON500", "서버 에러, 관리자에게 문의 바랍니다.")
    BAD_REQUEST = (status.HTTP_400_BAD_REQUEST, "COMMON400", "잘못된 요청입니다.")
    UNAUTHORIZED = (status.HTTP_401_UNAUTHORIZED, "COMMON401", "인증이 필요합니다.")
    FORBIDDEN = (status.HTTP_403_FORBIDDEN, "COMMON403","금지된 요청입니다.")

    # 리포트 관련 에러
    REPORT_NOT_FOUND = (status.HTTP_404_NOT_FOUND, "REPORT404", "존재하지 않는 리포트입니다.")



    def get_reason(self):
        """
        에러 메시지 반환
        """
        return {
            "message": self.value[2],
            "code": self.value[1],
            "isSuccess": False,
            "status": self.value[0]
        }

    