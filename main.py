import os
import shutil
import requests
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import whisper
from gtts import gTTS

app = FastAPI(title="NASA AI NPC Backend")

# 1. إعدادات CORS للسماح لاتصالات Unity بدون مشاكل
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. تحميل موديل Whisper للـ STT (استخدام tiny للسرعة والملاءمة لـ Render Free Tier)
print("Loading Whisper Model...")
whisper_model = whisper.load_model("tiny")
print("Whisper Model Loaded Successfully!")

class QuestionRequest(BaseModel):
    player_text: str

# 3. دالة البحث في NASA Open Data API
def fetch_nasa_data(query: str) -> str:
    if not query or len(query.strip()) == 0:
        return "No specific query provided."
        
    try:
        url = f"https://images-api.nasa.gov/search?q={query}&media_type=image,video"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            items = data.get("collection", {}).get("items", [])
            descriptions = []
            for item in items[:2]: # أخذ أول نتيجتين
                data_list = item.get("data", [])
                if data_list and "description" in data_list[0]:
                    descriptions.append(data_list[0]["description"])
            
            if descriptions:
                # اقتطاع النص لتجنب الإطالة
                combined = " ".join(descriptions)
                return combined[:400]
    except Exception as e:
        print(f"NASA API Error: {e}")
        
    return "No direct NASA records found for this query."

# 4. دالة توليد إجابة الـ AI NPC
def generate_npc_response(question: str, nasa_context: str) -> str:
    # يمكنك استبدال هذا الجزء باستدعاء Gemini API أو OpenAI API مستقبلاً
    clean_question = question.strip()
    
    if "No direct NASA records" in nasa_context:
        answer = f"I checked our space database regarding {clean_question}, but I couldn't find detailed records. As an astronaut, I recommend exploring further."
    else:
        answer = f"According to NASA data about {clean_question}: {nasa_context[:150]}... Stay curious, explorer!"
        
    return answer

# 5. Endpoint الاختبار للتأكد من عمل السيرفر
@app.get("/")
def home():
    return {"status": "NASA AI NPC Backend is online!"}

# 6. Endpoint معالجة النص المباشر (Text Input Endpoint)
@app.post("/ask_text")
async def ask_text(req: QuestionRequest):
    nasa_info = fetch_nasa_data(req.player_text)
    ai_answer = generate_npc_response(req.player_text, nasa_info)
    
    # تحويل الإجابة لصوت
    audio_filename = "npc_response.mp3"
    tts = gTTS(text=ai_answer, lang='en')
    tts.save(audio_filename)
    
    return FileResponse(
        audio_filename, 
        media_type="audio/mpeg", 
        filename="npc_response.mp3"
    )

# 7. Endpoint المعالجة الصوتية الكاملة (Voice Input Endpoint)
@app.post("/ask_npc_voice")
async def ask_npc_voice(file: UploadFile = File(...)):
    temp_wav = f"temp_{file.filename}"
    
    try:
        # أ) حفظ ملف الـ WAV المؤقت القادم من Unity
        with open(temp_wav, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # ب) Speech-to-Text باستخدام Whisper
        stt_result = whisper_model.transcribe(temp_wav)
        player_text = stt_result.get("text", "").strip()
        print(f"Transcribed Player Speech: '{player_text}'")
        
        if not player_text:
            player_text = "space exploration" # قيمة افتراضية لو التسجيل مكتوم

        # ج) جلب بيانات NASA وتوليد إجابة الـ NPC
        nasa_info = fetch_nasa_data(player_text)
        ai_answer = generate_npc_response(player_text, nasa_info)
        
        # د) Text-to-Speech تحويل الإجابة إلى MP3
        output_audio_path = "npc_response.mp3"
        tts = gTTS(text=ai_answer, lang='en')
        tts.save(output_audio_path)
        
        # هـ) إرجاع ملف الصوت لـ Unity
        return FileResponse(
            output_audio_path, 
            media_type="audio/mpeg", 
            filename="npc_response.mp3"
        )

    except Exception as e:
        print(f"Error processing voice request: {e}")
        raise HTTPException(status_code=500, detail=str(e))
        
    finally:
        # تنظيف الملفات المؤقتة
        if os.path.exists(temp_wav):
            os.remove(temp_wav)
