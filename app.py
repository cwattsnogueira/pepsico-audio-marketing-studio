import os
import gradio as gr
from google import genai
from google.cloud import texttospeech

# =====================================================
# Cloud Run Port
# =====================================================
PORT = int(os.environ.get("PORT", 8080))

# =====================================================
# Environment & Credentials
# =====================================================
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise RuntimeError("Missing GOOGLE_API_KEY")

client = genai.Client(api_key=GOOGLE_API_KEY)

SERVICE_ACCOUNT_JSON = os.getenv("GCP_VI_SERVICE_ACCOUNT_JSON")
if not SERVICE_ACCOUNT_JSON:
    raise RuntimeError("Missing GCP_VI_SERVICE_ACCOUNT_JSON")

with open("tts_credentials.json", "w") as f:
    f.write(SERVICE_ACCOUNT_JSON)

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "tts_credentials.json"
tts_client = texttospeech.TextToSpeechClient()

# =====================================================
# PepsiCo Product Catalog
# =====================================================
PEPSICO_PRODUCTS = {
    "Pepsi": "bold, refreshing, confident",
    "Gatorade": "performance-driven, motivational",
    "Lay's": "joyful, warm, social",
    "Doritos": "bold, playful, energetic",
}

AUDIO_FORMATS = {
    "Radio 15s": 15,
    "Radio 30s": 30,
    "Spotify Ad 30s": 30,
    "Spotify Ad 60s": 60,
}

LANGUAGES = {
    "English (US)": ("en-US", "en-US-Neural2-D"),
    "Spanish (LATAM)": ("es-US", "es-US-Neural2-B"),
    "Portuguese (BR)": ("pt-BR", "pt-BR-Neural2-B"),
}

# =====================================================
# Script Generation (Gemini NEW SDK)
# =====================================================
def generate_script(product, tone, duration, language, context):
    prompt = f"""
You are a senior PepsiCo brand copywriter.

Product: {product}
Brand voice: {tone}
Target duration: {duration} seconds
Language: {language}

Rules:
- Adult audience only
- No health or medical claims
- Natural spoken language
- Brand-safe and accurate
- No emojis, no titles

Context:
{context}

Return only the script text.
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )

    return response.text.strip()

# =====================================================
# Duration Enforcement
# =====================================================
def enforce_duration(text, target_seconds):
    words = text.split()
    max_words = int(target_seconds * 2.4)  # ~150 WPM
    return " ".join(words[:max_words])

# =====================================================
# Audio Generation
# =====================================================
def generate_audio(text, lang_code, voice_name):
    synthesis_input = texttospeech.SynthesisInput(text=text)

    voice = texttospeech.VoiceSelectionParams(
        language_code=lang_code,
        name=voice_name
    )

    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3,
        speaking_rate=1.0
    )

    response = tts_client.synthesize_speech(
        input=synthesis_input,
        voice=voice,
        audio_config=audio_config
    )

    output = "output.mp3"
    with open(output, "wb") as f:
        f.write(response.audio_content)

    return output

# =====================================================
# Full Pipeline
# =====================================================
def pipeline(product, audio_format, language, context):
    duration = AUDIO_FORMATS[audio_format]
    tone = PEPSICO_PRODUCTS[product]
    lang_code, voice_name = LANGUAGES[language]

    script = generate_script(
        product, tone, duration, language, context
    )

    script = enforce_duration(script, duration)
    audio = generate_audio(script, lang_code, voice_name)

    return script, audio

# =====================================================
# Gradio App
# =====================================================
app = gr.Interface(
    fn=pipeline,
    inputs=[
        gr.Dropdown(PEPSICO_PRODUCTS.keys(), label="Product"),
        gr.Dropdown(AUDIO_FORMATS.keys(), label="Audio Format"),
        gr.Dropdown(LANGUAGES.keys(), label="Language"),
        gr.Textbox(label="Campaign Context", lines=3),
    ],
    outputs=[
        gr.Textbox(label="Marketing Script", lines=10),
        gr.Audio(label="Generated Audio"),
    ],
    title="PepsiCo Audio Marketing Studio",
    description="Generate brand-safe marketing audio using Gemini and Google Cloud."
)

if __name__ == "__main__":
    app.launch(
        server_name="0.0.0.0",
        server_port=PORT
    )
