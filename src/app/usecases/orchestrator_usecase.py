from fastapi import Depends
from src.app.models.schemas.query_schema import QueryEndPointRequest
from src.app.services.planning_service import PlanningService
from src.app.services.workers_factory import WorkersFactory
import asyncio
import json
from src.app.models.schemas.history_schema import History
from src.app.models.schemas.worker_schema import Worker
from src.app.models.schemas.history_schema import Stage
from src.app.config.settings import settings

class OrchestratorUsecase:
    def __init__(self):
        self.history = History(user_query="", status="in_progress", total_iterations=0, history=[])
         
         
    async def execute(self, request: QueryEndPointRequest):
        while self.history.status in ["completed", "failed"] or self.history.total_iterations < settings.MAX_ITERATIONS:
            self.history.total_iterations += 1
            self.history.user_query = request.query
            response = await self
            