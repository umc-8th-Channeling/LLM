from dataclasses import dataclass

@dataclass
class ReasonDTO:
    message: str
    code: str
    isSuccess: bool
    status: int