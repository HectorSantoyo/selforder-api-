from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.routers import health, shops, categories, products
from app.core.errors import install_exception_handlers

from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Dev-only: crear tablas si no existen
    # async with engine.begin() as conn:
    #     await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)

# <<< registra los handlers globales de error (formato {error:{code,message,details}})
install_exception_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix=settings.API_V1)
app.include_router(shops.router, prefix=settings.API_V1)
app.include_router(categories.router, prefix=settings.API_V1)
app.include_router(products.router, prefix=settings.API_V1)
