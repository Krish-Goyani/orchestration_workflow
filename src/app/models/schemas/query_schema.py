from pydantic import BaseModel

class QueryEndPointRequest(BaseModel):
    query: str