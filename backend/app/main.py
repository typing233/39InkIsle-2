from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings
from app.auth.router import router as auth_router
from app.users.router import router as users_router
from app.books.router import router as books_router
from app.reader.router import router as reader_router
from app.importer.router import router as importer_router
from app.admin.router import router as admin_router
from app.reviews.router import router as reviews_router
from app.collections.router import router as collections_router
from app.enrichment.router import router as enrichment_router
from app.opds.router import router as opds_router


def create_app() -> FastAPI:
    settings = get_settings()

    application = FastAPI(
        title="InkIsle",
        description="Private book library and reader",
        version="0.2.0",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins.split(","),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.include_router(auth_router, prefix="/api/v1")
    application.include_router(users_router, prefix="/api/v1")
    application.include_router(books_router, prefix="/api/v1")
    application.include_router(reader_router, prefix="/api/v1")
    application.include_router(importer_router, prefix="/api/v1")
    application.include_router(admin_router, prefix="/api/v1")
    application.include_router(reviews_router, prefix="/api/v1")
    application.include_router(collections_router, prefix="/api/v1")
    application.include_router(enrichment_router, prefix="/api/v1")
    application.include_router(opds_router)

    @application.get("/api/v1/health")
    async def health():
        return {"status": "ok"}

    return application


app = create_app()
