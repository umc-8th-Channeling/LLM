from response.code.status.success_status import SuccessStatus
from response.code.status.error_status import ErrorStatus
from typing import Dict, Any


class ApiResponse:
    """API 응답을 표준화하는 클래스"""
    
    @staticmethod
    def on_success(success_status: SuccessStatus, result: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        성공 응답을 생성합니다.
        
        :param success_status: 성공 상태 코드
        :param result: 추가 데이터 (선택 사항)
        :return: 성공 응답 딕셔너리
        """
        response = success_status.get_reason()
        if result:
            response["result"] = result
        return response

    @staticmethod
    def on_failure(error_status: ErrorStatus, result: Dict[str, Any] = None) -> Dict[str, Any]:
        """실패 응답 생성"""
        response = error_status.get_reason()
        if result:
            response["result"] = result
        return response