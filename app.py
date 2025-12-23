import os
import asyncio
import json
import gradio as gr
import google.generativeai as genai

from google.cloud import texttospeech
from pydub import AudioSegment

# =====================================================
# Environment & Credentials
# =====================================================

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise RuntimeError("Missing GOOGLE_API_KEY")

genai.configure(api_key=GOOGLE_API_KEY)

SERVICE_ACCOUNT_JSON = os.getenv("GCP_VI_SERVICE_ACCOUNT_JSON")
if not SERVICE_ACCOUNT_JSON:
    raise RuntimeError("Missing GCP_VI_SERVICE_ACCOUNT_JSON")

with open("tts_credentials.json", "w") as f:
    f.write(SERVICE_ACCOUNT_JSON)

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "tts_credentials.json"
tts_client = texttospeech.TextToSpeechClient()

# =====================================================
# PepsiCo Product Catalog (Controlled)
# =====================================================

PEPSICO_PRODUCTS = {
    "Pepsi": {
        "launch_year": 1893,
        "voice": "bold, refreshing, confident",
    },
    "Gatorade": {
        "launch_year": 1965,
        "voice": "performance-driven, motivational, credible",
    },
    "Lay's": {
        "launch_year": 1932,
        "voice": "joyful, warm, social",
    },
    "Doritos": {
        "launch_year": 1964,
        "voice": "bold, playful, energetic",
    }
}

STORY_MODES = [
    "Brand Origin Story",
    "How It's Made",
    "Lifestyle & Social Moments",
    "Party & Celebration",
    "Food Pairing & Recipes",
    "Sports & Performance"
]

AUDIO_FORMATS = {
    "Radio 15s": 15,
    "Radio 30s": 30,
    "Spotify Ad 30s": 30,
    "Spotify Ad 60s": 60,
    "Podcast Mid-roll 45s": 45
}

LANGUAGES = {
    "English (US)": ("en-US", "en-US-Neural2-D"),
    "Spanish (LATAM)": ("es-US", "es-US-Neural2-B"),
    "Portuguese (BR)": ("pt-BR", "pt-BR-Neural2-B")
}

# =====================================================
# Gemini Marketing Prompt (Brand-Safe)
# =====================================================

def build_marketing_prompt(product, story_mode, duration, language):
    product_data = PEPSICO_PRODUCTS[product]

    return f"""
You are a senior brand copywriter working at PepsiCo.

Create a professional audio marketing script.

Product: {product}
Launch year: {product_data['launch_year']}
Brand voice: {product_data['voice']}
Story type: {story_mode}
Target duration: {duration} seconds
Language: {language}

Rules:
- Target adult consumers only
- No health, medical, or nutritional claims
- No exaggeration or false claims
- Script must sound natural when spoken
- Avoid slang unless brand-appropriate
- Do NOT use emojis
- Do NOT include titles or formatting
- Respect the time limit strictly

Output only the final script text.
"""

# =====================================================
# Script Generation (Gemini)
# =====================================================

def generate_script(prompt):
    model = genai.GenerativeModel("gemini-2.5-flash")
    response = model.generate_content(
        prompt,
        generation_config={"temperature": 0.85, "max_output_tokens": 1024}
    )
    return response.text.strip()

# =====================================================
# Audio Generation with Duration Enforcement
# =====================================================

def estimate_speech_duration(text, wpm=150):
    words = len(text.split())
    return (words / wpm) * 60

def enforce_duration(script, target_seconds):
    estimated = estimate_speech_duration(script)
    if estimated <= target_seconds:
        return script

    ratio = target_seconds / estimated
    new_word_count = int(len(script.split()) * ratio)
    return " ".join(script.split()[:new_word_count])

def generate_audio(script, language_code, voice_name, output="audio.mp3"):
    synthesis_input = texttospeech.SynthesisInput(text=script)
    voice = texttospeech.VoiceSelectionParams(
        language_code=language_code,
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

    with open(output, "wb") as f:
        f.write(response.audio_content)

    return output

# =====================================================
# Full Pipeline
# =====================================================

def pipeline(product, story_mode, audio_format, language, campaign_context):
    duration = AUDIO_FORMATS[audio_format]
    lang_code, voice_name = LANGUAGES[language]

    prompt = build_marketing_prompt(
        product, story_mode, duration, language
    )

    if campaign_context:
        prompt += f"\nCampaign context: {campaign_context}"

    script = generate_script(prompt)
    script = enforce_duration(script, duration)

    audio_path = generate_audio(
        script, lang_code, voice_name
    )

    return script, audio_path

# =====================================================
# Gradio UI
# =====================================================

app = gr.Interface(
    fn=pipeline,
    inputs=[
        gr.Dropdown(list(PEPSICO_PRODUCTS.keys()), label="Product"),
        gr.Dropdown(STORY_MODES, label="Story Type"),
        gr.Dropdown(list(AUDIO_FORMATS.keys()), label="Audio Format"),
        gr.Dropdown(list(LANGUAGES.keys()), label="Language"),
        gr.Textbox(label="Campaign Context (Optional)")
    ],
    outputs=[
        gr.Textbox(label="Marketing Script", lines=12),
        gr.Audio(label="Generated Audio")
    ],
    title="PepsiCo Audio Marketing Studio",
    description="Generate brand-safe audio ads for PepsiCo products using Gemini and Google Cloud."
)

if __name__ == "__main__":
    app.launch()
