import random
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from services.llm_service import generate_smart_lesson

app = FastAPI(
    title="IoT English Listening Device API",
    description="Backend chính thức cho thiết bị học tiếng Anh IoT",
    version="1.0.0"
)

class LessonRequest(BaseModel):
    topic_detail: str
    cefr_level: str = "A2"
    target_duration: str = "1 min"
    lesson_type: str = "random"  # Mặc định hoặc bắt buộc là random theo ý bạn

@app.post("/api/generate-lesson")
async def generate_lesson_endpoint(request: LessonRequest):
    try:
        # Xử lý logic random hoàn toàn trước khi gọi AI (không phụ thuộc nút bấm client)
        chosen_type = request.lesson_type
        if chosen_type == "random":
            chosen_type = random.choice(["dialogue", "podcast"])
            
        print(f"🎲 [System] Đã random loại bài học: {chosen_type.upper()} cho chủ đề: '{request.topic_detail}'")

        # Gọi "bộ não" llm_service đã được tối ưu đa tầng
        result = await generate_smart_lesson(
            topic_detail=request.topic_detail,
            cefr_level=request.cefr_level,
            target_duration=request.target_duration,
            lesson_type=chosen_type
        )
        
        return {
            "status": "success",
            "lesson_type": chosen_type,
            "level": request.cefr_level,
            "duration": request.target_duration,
            "content": result["script"]
        }
        
    except Exception as e:
        print(f"❌ Lỗi tại endpoint generate-lesson: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    return {"message": "IoT English Listening Device Backend is running smoothly!"}