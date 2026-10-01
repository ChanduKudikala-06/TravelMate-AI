from pathlib import Path
import uvicorn

from fastapi import FastAPI,Request
from fastapi.responses import HTMLResponse,JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from backend import run_travel_agent

BASE_DIR=Path(__file__).resolve().parent

app=FastAPI(
    title="AI Travel Planning System",
    description="Langgraph MultiAgent Travel Planner with FastAPI frontend",
    version="0.1.0"
)


app.mount("/static",StaticFiles(directory=str(BASE_DIR/"static")),name="static"),
templates=Jinja2Templates(directory=str(BASE_DIR/"templates"))

class TravelRequest(BaseModel):
    message:str
    thread_id:str|None=None
    
    
@app.get("/",response_class=HTMLResponse)
async def home(request:Request):
    return templates.TemplateResponse(
        request=request,
        template_name="index.html",
        context={}
    )