from fastapi import APIRouter
from backend.app.api.v1.assessments import router as assessments_router
from backend.app.api.v1.auth import router as auth_router
from backend.app.api.v1.authorizations import router as authorizations_router
from backend.app.api.v1.custody import router as custody_router
from backend.app.api.v1.executions import router as executions_router
from backend.app.api.v1.inspections import router as inspections_router
from backend.app.api.v1.pickups import router as pickups_router
from backend.app.api.v1.refunds import router as refunds_router
from backend.app.api.v1.reports import router as reports_router
from backend.app.api.v1.returns import router as returns_router

api_router = APIRouter()

api_router.include_router(auth_router)
api_router.include_router(returns_router)
api_router.include_router(pickups_router)
api_router.include_router(custody_router)
api_router.include_router(inspections_router)
api_router.include_router(assessments_router)
api_router.include_router(authorizations_router)
api_router.include_router(executions_router)
api_router.include_router(refunds_router)
api_router.include_router(reports_router)
