# PepsiCo Audio Marketing Studio

An internal AI-powered platform to generate brand-safe marketing audio content for PepsiCo products.

## Features
- Gemini-powered marketing storytelling
- Brand-safe prompts per product
- Multi-language support
- Audio duration enforcement
- Broadcast-ready Google TTS voices
- Cloud Run deployable

## Environment Variables
- GOOGLE_API_KEY
- GCP_VI_SERVICE_ACCOUNT_JSON

## Architecture Diagram 

```mermaid
flowchart LR
    User --> GradioUI
    GradioUI --> GeminiAPI
    GeminiAPI --> ScriptValidation
    ScriptValidation --> TTS
    TTS --> AudioAssets
    AudioAssets --> CloudRun

```

## Deployment (Google Cloud Run)

```bash
gcloud builds submit --tag gcr.io/PROJECT_ID/pepsico-audio-studio
gcloud run deploy pepsico-audio-studio \
  --image gcr.io/PROJECT_ID/pepsico-audio-studio \
  --region us-central1 \
  --platform managed
```





