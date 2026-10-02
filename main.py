import os
import shutil
import requests
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI
from gtts import gTTS

app = FastAPI(title="NASA AI NPC Backend")

# 1. إعدادات CORS للسماح لاتصالات Unity
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. إعداد client الـ OpenAI (بيقرأ المفتاح تلقائياً من الـ Environment Variables)
# تأكد من إضافة OPENAI_API_KEY في إعدادات Environment Variables على Render
openai_client = OpenAI(api_key=os.environ.get("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"))

class QuestionRequest(BaseModel):
    player_text: str

# 3. دالة جلب البيانات من NASA Open Data API
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
            for item in items[:2]:
                data_list = item.get("data", [])
                if data_list and "description" in data_list[0]:
                    descriptions.append(data_list[0]["description"])
            
            if descriptions:
                combined = " ".join(descriptions)
                return combined[:400]
    except Exception as e:
        print(f"NASA API Error: {e}")
        
    return "No direct NASA records found for this query."

# 4. دالة توليد إجابة الـ NPC (يمكنك ربط GPT-3.5/GPT-4 بدلاً من هذا السطر مستقبلاً)
def generate_npc_response(question: str, nasa_context: str) -> str:
    clean_question = question.strip()
    
    if "No direct NASA records" in nasa_context:
        answer = f"I checked our space database regarding '{clean_question}', but found no detailed records. Keep exploring, astronaut!"
    else:
        answer = f"According to NASA data about '{clean_question}': {nasa_context[:180]}... Safe travels out there!"
        
    return answer

# 5. Endpoint الاختبار
@app.get("/")
def home():
    return {"status": "NASA AI NPC Backend is running efficiently!"}

# 6. Endpoint المعالجة الصوتية بـ Whisper API
@app.post("/ask_npc_voice")
async def ask_npc_voice(file: UploadFile = File(...)):
    temp_wav = f"temp_{file.filename}"
    
    try:
        # أ) حفظ ملف الصوت القادم من Unity
        with open(temp_wav, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # ب) تحويل الصوت إلى نص عبر OpenAI Whisper API (بدون استهلاك RAM السيرفر)
        with open(temp_wav, "rb") as audio_file:
            transcript = openai_client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )
        
        player_text = transcript.text.strip()
        print(f"🎙️ Transcribed via Whisper API: '{player_text}'")
        
        if not player_text:
            player_text = "space exploration"

        # ج) جلب بيانات NASA وتوليد الإجابة
        nasa_info = fetch_nasa_data(player_text)
        ai_answer = generate_npc_response(player_text, nasa_info)
        
        # د) تحويل النص المرتجع إلى صوت MP3
        output_audio_path = "npc_response.mp3"
        tts = gTTS(text=ai_answer, lang='en')
        tts.save(output_audio_path)
        
        # هـ) إرجاع الملف لـ Unity
        return FileResponse(
            output_audio_path, 
            media_type="audio/mpeg", 
            filename="npc_response.mp3"
        )

    except Exception as e:
        print(f"❌ Error processing request: {e}")
        raise HTTPException(status_code=500, detail=str(e))
        
    finally:
        # تنظيف الملفات المؤقتة
        if os.path.exists(temp_wav):
            os.remove(temp_wav)
