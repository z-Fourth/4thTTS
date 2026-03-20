import os
import io
from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
import azure.cognitiveservices.speech as speechsdk
from docx import Document
from pydub import AudioSegment

app = Flask(__name__)
CORS(app)

# ===== CONFIG =====
SPEECH_KEY = os.environ.get("SPEECH_KEY")
SPEECH_REGION = os.environ.get("SPEECH_REGION")
VOICE_NAME = "vi-VN-HoaiMyNeural"

# ===== READ FILE =====
def read_file(file):
    if file.filename.endswith(".txt"):
        return file.read().decode("utf-8")

    elif file.filename.endswith(".docx"):
        doc = Document(file)
        return "\n".join([p.text for p in doc.paragraphs])

    else:
        raise Exception("Unsupported file format")

# ===== SPLIT PARAGRAPHS =====
def split_paragraphs(text):
    return [p.strip() for p in text.split("\n") if p.strip()]

# ===== BUILD SSML =====
def build_ssml(text):
    return f"""
    <speak version='1.0' xml:lang='vi-VN'>
        <voice name='{VOICE_NAME}'>
            <prosody rate='0.92'>
                {text}
            </prosody>
            <break time="500ms"/>
        </voice>
    </speak>
    """

# ===== SYNTHESIZE AUDIO =====
def synthesize(text):
    speech_config = speechsdk.SpeechConfig(
        subscription=SPEECH_KEY,
        region=SPEECH_REGION
    )

    final_audio = AudioSegment.empty()
    paragraphs = split_paragraphs(text)

    for i, para in enumerate(paragraphs):
        ssml = build_ssml(para)

        synthesizer = speechsdk.SpeechSynthesizer(
            speech_config=speech_config,
            audio_config=None
        )

        result = synthesizer.speak_ssml_async(ssml).get()

        if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
            audio = AudioSegment.from_file(
                io.BytesIO(result.audio_data),
                format="wav"
            )

            final_audio += audio
            final_audio += AudioSegment.silent(duration=300)

            print(f"✅ Paragraph {i}")
        else:
            print(f"❌ Error at paragraph {i}")

    return final_audio

# ===== API =====
@app.route("/api/tts", methods=["POST"])
def tts():
    try:
        file = request.files["file"]

        text = read_file(file)
        audio = synthesize(text)

        output = io.BytesIO()
        audio.export(output, format="mp3")
        output.seek(0)

        return send_file(
            output,
            mimetype="audio/mpeg",
            as_attachment=False
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ===== RUN =====
if __name__ == "__main__":
    app.run(debug=True)
