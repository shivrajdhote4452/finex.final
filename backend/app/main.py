"""FinEx FastAPI Server Application Entrypoint."""

from backend.app.factory import create_app

app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)
