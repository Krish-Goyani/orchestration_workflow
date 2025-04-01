from pydantic import BaseModel

class Worker(BaseModel):
    name: str
    description: str
    