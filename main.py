import asyncio
import queue
import threading
import logging
from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import os
from typing import Optional

from src.core.generator import NewsGenerator
from src.audio.player import play_audio_from_queue

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('news.log'), logging.StreamHandler()]
)

app = FastAPI()
generator_task = None
audio_queue = queue.Queue()
generator = None

# Start audio player thread
player_thread = threading.Thread(target=play_audio_from_queue, args=(audio_queue,), daemon=True)
player_thread.start()

@app.get("/", response_class=HTMLResponse)
async def get_index():
    with open("index.html", "r") as f:
        return HTMLResponse(content=f.read())

@app.post("/start")
async def start_generator(
    background_tasks: BackgroundTasks,
    topic: Optional[str] = None,
    guidance: Optional[str] = None,
    fetch_interval: int = 15,
    persona: str = "objective.yaml",
):
    global generator, generator_task
    
    if generator_task:
        return JSONResponse({"status": "error", "message": "Generator is already running"})
    
    # Initialize the generator
    generator = NewsGenerator(
        audio_queue=audio_queue,
        topic=topic,
        guidance=guidance,
        persona_file=f"personas/{persona}" if not persona.startswith("personas/") else persona
    )
    
    # Start the generator in a background task
    generator_task = background_tasks.add_task(
        generator.run_continuous,
        fetch_interval_minutes=fetch_interval
    )
    
    return JSONResponse({"status": "success", "message": "Generator started"})

@app.post("/stop")
async def stop_generator():
    global generator_task, generator
    
    if not generator_task:
        return JSONResponse({"status": "error", "message": "Generator is not running"})
    
    if generator:
        await generator.stop()
        generator = None
        generator_task = None
    
    return JSONResponse({"status": "success", "message": "Generator stopped"})

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
