import os
import io
from flask import Flask, request, send_file, jsonify, render_template
from flask_cors import CORS
import azure.cognitiveservices.speech as speechsdk
from docx import Document
from pydub import AudioSegment

app = Flask(__name__)
CORS(app)

print("🚀 APP STARTING...")

# ===== CONFIG =====
SPEECH_KEY = os.environ.get("SPEECH_KEY")
SPEECH_REGION = os.environ.get("SPEECH_REGION")
VOICE_NAME = "vi-VN-HoaiMyNeural"

# 🔥 CHECK ENV (QUAN TRỌNG)
if not SPEECH_KEY or not SPEECH_REGION:
    print("❌ Missing Azure ENV")

# ===== GLOBAL CONFIG (TỐI ƯU) =====
speech_config = None
if SPEECH_KEY and SPEECH_REGION:
    speech_config = speechsdk.SpeechConfig(
        subscription=SPEECH_KEY,
        region=SPEECH_REGION
    )

# ===== READ FILE =====
def read_file(file):
    if file.filename.endswith(".txt"):
        return file.read().decode("utf-8")
    elif file.filename.endswith(".docx"):
        doc = Document(file)
        return "\n".join([p.text for p in doc.paragraphs])
    else:
        raise Exception("Unsupported file format")

# ===== SPLIT =====
def split_paragraphs(text):
    return [p.strip() for p in text.split("\n") if p.strip()]

# ===== BUILD SSML =====
def build_ssml(text):
    return f"""
    <speak version='1.0' xml:lang='vi-VN'>
        <voice name='{VOICE_NAME}'>
            <prosody rate='0.92'>{text}</prosody>
        </voice>
    </speak>
    """

# ===== TTS =====
def synthesize_segment(text):
    if not speech_config:
        raise Exception("Missing Azure config")

    synthesizer = speechsdk.SpeechSynthesizer(
        speech_config=speech_config,
        audio_config=None
    )

    result = synthesizer.speak_ssml_async(build_ssml(text)).get()

    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        return AudioSegment.from_file(io.BytesIO(result.audio_data), format="wav")
    return None

# ===== MAIN =====
def synthesize_full(text):
    paragraphs = split_paragraphs(text)
    final_audio = AudioSegment.empty()

    for i, para in enumerate(paragraphs):
        print(f"🔊 Processing {i}")

        audio = synthesize_segment(para)

        if audio:
            final_audio += audio
            final_audio += AudioSegment.silent(duration=400)
        else:
            final_audio += AudioSegment.silent(duration=1000)

    return final_audio

# ===== API =====
@app.route("/api/tts", methods=["POST"])
def tts():
    try:
        file = request.files["file"]

        text = read_file(file)
        audio = synthesize_full(text)

        output = io.BytesIO()
        audio.export(output, format="mp3")
        output.seek(0)

        return send_file(output, mimetype="audio/mpeg")

    except Exception as e:
        print("ERROR:", str(e))
        return jsonify({"error": str(e)}), 500

# ===== HOME (SAFE MODE) =====
@app.route("/")
def home():
    return render_template("index.html")
    
# ===== RUN =====
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
