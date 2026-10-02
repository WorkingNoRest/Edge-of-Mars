python
from fastapi import FastAPI, UploadFile, File
import whisper
import shutil
import os

app = FastAPI()

# تحميل الموديل مرة واحدة عند تشغيل السيرفر (tiny أو base للسرعة)
model = whisper.load_model("tiny")

@app.post("/ask_npc_voice")
async def ask_npc_voice(file: UploadFile = File(...)):
    # 1. حفظ ملف الصوت المؤقت
    temp_filename = f"temp_{file.filename}"
    with open(temp_filename, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    # 2. تحويل الصوت إلى نص عبر Whisper
    result = model.transcribe(temp_filename)
    player_text = result.get("text", "")
    
    # حذف الملف المؤقت
    if os.path.exists(temp_filename):
        os.remove(temp_filename)
        
    # 3. البحث في NASA Data وتوليد الإجابة
    nasa_info = fetch_nasa_data(player_text)
    ai_answer = generate_ai_response(player_text, nasa_info)
    
    return {
        "status": "success",
        "transcribed_text": player_text,
        "answer": ai_answer
    }
