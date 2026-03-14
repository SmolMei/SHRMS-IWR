import sys
import os
from contextlib import asynccontextmanager

# Ensure the project root is on the path so workflow_router can be imported
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, Depends
from workflow_router import WorkflowRouter
from api.schemas import IPCRRequest, LeaveRequest
from api.auth import require_api_key
from api.data_loader import load_from_hrms


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_from_hrms()  # fetch live data from Smart-HRMS before first request
    yield


app = FastAPI(
    title="IWR API",
    description="Intelligent Workflow Routing — SHRMS integration layer",
    lifespan=lifespan,
)

# Singleton: models loaded once at startup, reused for every request
_router = WorkflowRouter()


@app.get("/api/health")
def health():
    return {"status": "ok", "models_loaded": True}


@app.post("/api/ipcr/route", dependencies=[Depends(require_api_key)])
def route_ipcr(req: IPCRRequest):
    return _router.route_ipcr(req.model_dump())


@app.post("/api/leave/route", dependencies=[Depends(require_api_key)])
def route_leave(req: LeaveRequest):
    form = req.model_dump()
    form["start_date"] = req.start_date  # keep as date object, not string
    return _router.route_leave(form)
