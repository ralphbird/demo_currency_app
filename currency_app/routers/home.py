"""Home page router for the Currency Conversion API."""

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
def home():
    """Serve the home page with links to all services and documentation."""
    template_path = Path(__file__).parent.parent / "templates" / "home.html"
    with open(template_path, encoding="utf-8") as file:
        return HTMLResponse(content=file.read())
