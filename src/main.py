from fastapi import FastAPI
from src.app.routes.query_route import router as query_router


app = FastAPI()
app.include_router(query_router)