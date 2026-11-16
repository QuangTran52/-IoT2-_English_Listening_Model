from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel

from config import STORAGE_DIR
from services.llm_service import generate_smart_lesson
from services.tts_service import text_to_speech_multivoice
from services.variation_service import dynamic_speech_rate

app = FastAPI(
    title="IoT English Listening Device API",
    description="Backend chính thức cho thiết bị học tiếng Anh IoT",
    version="1.0.0"
)

app.state.lesson_counter = 0


class LessonRequest(BaseModel):
    topic_detail: str
    cefr_level: str = "A2"
    target_duration: str = "1 min"
    lesson_type: str = "random"
    speech_rate: float = 1.0


@app.post("/api/generate-lesson")
async def generate_lesson_endpoint(request: LessonRequest):
    try:
        chosen_type = request.lesson_type
        if chosen_type == "random":
            import random
            chosen_type = random.choice(["dialogue", "podcast"])

        app.state.lesson_counter += 1
        variation_step = app.state.lesson_counter

        result = await generate_smart_lesson(
            topic_detail=request.topic_detail,
            cefr_level=request.cefr_level,
            target_duration=request.target_duration,
            lesson_type=chosen_type,
            variation_step=variation_step
        )

        dynamic_rate = dynamic_speech_rate(
            base_rate=request.speech_rate,
            step=variation_step,
            spread=0.18,
            phase=0.25
        )

        return {
            "status": "success",
            "lesson_type": chosen_type,
            "level": request.cefr_level,
            "duration": request.target_duration,
            "speech_rate": dynamic_rate,
            "content": result["script"],
            "sentence_count": result.get("sentence_count", 0)
        }

    except Exception as e:
        print(f"❌ Lỗi tại endpoint generate-lesson: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/generate-lesson-audio")
async def generate_lesson_audio_endpoint(request: LessonRequest):
    try:
        chosen_type = request.lesson_type
        if chosen_type == "random":
            import random
            chosen_type = random.choice(["dialogue", "podcast"])

        app.state.lesson_counter += 1
        variation_step = app.state.lesson_counter

        result = await generate_smart_lesson(
            topic_detail=request.topic_detail,
            cefr_level=request.cefr_level,
            target_duration=request.target_duration,
            lesson_type=chosen_type,
            variation_step=variation_step
        )

        dynamic_rate = dynamic_speech_rate(
            base_rate=request.speech_rate,
            step=variation_step,
            spread=0.18,
            phase=0.25
        )

        script = result["script"]
        audio_bytes = await text_to_speech_multivoice(
            script_text=script,
            is_dialogue=(chosen_type == "dialogue"),
            speech_rate=dynamic_rate
        )

        return Response(content=audio_bytes, media_type="audio/mpeg")

    except Exception as e:
        print(f"❌ Lỗi audio endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/audio/current")
async def get_current_audio():
    storage_dir = Path(STORAGE_DIR)
    if not storage_dir.is_absolute():
        storage_dir = Path(__file__).resolve().parent / storage_dir

    file_path = storage_dir / "current.mp3"

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Current audio not found")

    return FileResponse(file_path, media_type="audio/mpeg")


@app.get("/")
async def root():
    return {
        "status": "ok",
        "message": "IoT English Listening Device Backend is running."
    }