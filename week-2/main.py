import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import config
from database import init_db
from router import router
from logging_setup import logger

app = FastAPI(
    title="Classic Models API",
    description="A FastAPI application for managing classic model cars data",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.on_event("startup")
def startup_event():
    logger.info("Starting FastAPI application")
    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")


@app.on_event("shutdown")
def shutdown_event():
    logger.info("Shutting down FastAPI application")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=config.API_HOST,
        port=config.API_PORT,
        reload=True
    )