"""
API routes for Answer Engine Analytics.
"""

from fastapi import APIRouter

from . import auth, brands, questions, analysis, reports

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(brands.router, prefix="/brands", tags=["Brands"])
api_router.include_router(questions.router, prefix="/questions", tags=["Questions"])
api_router.include_router(analysis.router, prefix="/analysis", tags=["Analysis"])
api_router.include_router(reports.router, prefix="/reports", tags=["Reports"])
