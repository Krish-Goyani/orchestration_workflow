from typing import Callable

from pydantic import BaseModel


class Tool(BaseModel):
    name: str
    description: str
    func: Callable
    parameters: dict[str, dict[str, str]]
    return_type: str
    return_description: str
