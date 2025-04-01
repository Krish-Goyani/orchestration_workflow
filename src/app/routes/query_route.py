from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse

from src.app.utils.error_handler import handle_exceptions
from src.app.models.schemas.query_schema import QueryEndPointRequest
from src.app.controllers.orchestrator_controller import OrchestratorController

router = APIRouter()

@router.post("/query")
@handle_exceptions
async def make_query(
    request: QueryEndPointRequest, orchestrator_controller: OrchestratorController = Depends()
):

    response_data = await orchestrator_controller.orchestrate(request)

    return JSONResponse(
        content={
            "data": response_data,
            "statuscode": 200,
            "detail": "Query execution successful!",
            "error": "",
        },
        status_code=status.HTTP_200_OK,
    )