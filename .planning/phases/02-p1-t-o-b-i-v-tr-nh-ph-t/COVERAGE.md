# API Coverage — OpenAI REST API and YouTube (via yt-dlp)

> Full coverage by default. Opt-outs are explicit, reasoned decisions.
> Phase 2 calls OpenAI over httpx (D-23, no SDK) for key verification (SET-03, plan 02-11) and sentence translation (D-16, plan 02-16), and reads YouTube through yt-dlp (plans 02-03, 02-07, 02-12).

| capability | decision | reason |
|---|---|---|
| openai.models.list | INTEGRATE | |
| openai.responses.create (text in, structured JSON out) | INTEGRATE | |
| openai.audio.speech (TTS) | OPT-OUT | not needed yet — TTS đọc chậm is Phase 7 (REV-03) |
| openai.audio.transcriptions / translations | OPT-OUT | explicitly out of scope — CLAUDE.md: LLM never receives audio; ASR is local mlx-whisper |
| openai.realtime | OPT-OUT | explicitly out of scope — no audio to LLMs, no conversational mode in Step 1 |
| openai.embeddings | OPT-OUT | not needed — no retrieval or similarity search in the product |
| openai.images | OPT-OUT | not needed — no image generation in the product |
| openai.moderations | OPT-OUT | not needed — single local user, text comes from the video transcript |
| openai.files / batches | OPT-OUT | not needed — one short sentence per request, cached in lesson.json |
| openai.fine_tuning | OPT-OUT | explicitly out of scope — no custom models (CLAUDE.md: models locked) |
| openai.assistants / threads / vector_stores | OPT-OUT | not needed — stateless single-sentence translation |
| openai.responses tool calling | OPT-OUT | explicitly out of scope — translation runs without tools (prompt-injection mitigation T-02-44) |
| openai.structured tips from issues (LLM gợi ý) | OPT-OUT | not needed yet — Phase 8 (CAL-03) |
| youtube.video_metadata (title, duration, channel, live/availability) | INTEGRATE | |
| youtube.video_download (H.264/AAC ≤ 480p) | INTEGRATE | |
| youtube.thumbnail_url | INTEGRATE | |
| youtube.captions / auto-subtitles | OPT-OUT | explicitly out of scope — transcript comes from the speaker's audio (mlx-whisper), not from YouTube captions |
| youtube.playlists | OPT-OUT | explicitly out of scope — `noplaylist`; one lesson = one video range |
| youtube.channels | OPT-OUT | explicitly out of scope — channel links are rejected with `channel_url` (02-07) |
| youtube.livestreams | OPT-OUT | explicitly out of scope — live/upcoming videos rejected with `live_video` (02-07) |
| youtube.comments / likes / search | OPT-OUT | not needed — the app starts from a pasted video link |
| youtube.iframe_player_api | OPT-OUT | explicitly out of scope — D-17 / ADR 0004 drop the IFrame fallback in Step 1 |
| youtube.data_api_v3 (official API with key) | OPT-OUT | not needed — yt-dlp covers metadata without an API key (local-first, no extra key) |
