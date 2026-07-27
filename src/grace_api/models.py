from dataclasses import dataclass
from typing import Optional


@dataclass
class ApiError:
    message: str
    status_code: int = 400
