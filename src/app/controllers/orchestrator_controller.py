from fastapi import Depends
from src.app.models.schemas.query_schema import QueryEndPointRequest
from src.app.usecases.orchestrator_usecase import OrchestratorUsecase
class OrchestratorController:
    def __init__(self, orchestrator_usecase: OrchestratorUsecase = Depends()):
        self.orchestrator_usecase = orchestrator_usecase
        
        
    async def orchestrate(self, request: QueryEndPointRequest):
        return await self.orchestrator_usecase.execute(request)
        
        
        
        