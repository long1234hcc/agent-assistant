"""
Voice interface cho Personal AI Assistant
Dùng Gemini Live API để nói chuyện trực tiếp với agent

Flow:
    Mic → Gemini Live (transcript) → agent.run() → tools → Gemini Live đọc kết quả → Speaker

Requirements:
    pip install pyaudio

Usage:
    python main_voice.py
    → Nói vào mic, agent trả lời bằng giọng nói
    → Ctrl+C để thoát
"""

import asyncio
import os
from datetime import datetime
from dotenv import load_dotenv

import pyaudio
from google import genai
from google.genai import types
from websockets.exceptions import ConnectionClosedError

# ── Import agent components ───────────────────────────────────────────────────
from agents.core.agent import Agent
from agents.core.history import History
from agents.core.session import Session
from agents.models.base import GenAIModel
from agents.mcp.registry import Registry
from agents.prompts.builder import PromptBuilder
from agents.tools.researchs.tool import (
    search_github_repositories,
    get_readme,
    research_trending_repositories,
)

load_dotenv()

# ── Audio constants ───────────────────────────────────────────────────────────
FORMAT = pyaudio.paInt16
CHANNELS = 1
SEND_SAMPLE_RATE = 16000   # mic: 16kHz PCM mono
RECV_SAMPLE_RATE = 24000   # speaker: 24kHz
CHUNK_SIZE = 1024

LIVE_MODEL = "gemini-2.5-flash-native-audio-preview-12-2025"

pya = pyaudio.PyAudio()

# ── Init Agent ────────────────────────────────────────────────────────────────
session = Session(session_id="voice_session")
history = History(max_length=50)
builder = PromptBuilder()

text_llm = GenAIModel(
    model_name="gemini-3-flash-preview",
    api_key=os.environ.get("GEMINI_API_KEY"),
)

registry = Registry()
registry.register("search_github_repositories",     search_github_repositories)
registry.register("get_readme",                     get_readme)
registry.register("research_trending_repositories",
                  research_trending_repositories)

prompt_params = {
    "agent_name": "Personal Assistant",
    "persona": (
        "You are a concise, insightful personal assistant. "
        "Keep voice responses short and natural — no bullet points, no markdown. "
        "Speak like a human."
    ),
    "date":     datetime.now().strftime("%Y-%m-%d"),
    "language": "Vietnamese",
}

agent = Agent(
    session=session,
    history=history,
    prompt_builder=builder,
    llm=text_llm,
    tools_registry=registry,
    prompt_params=prompt_params,
)

# ── Live API config ───────────────────────────────────────────────────────────
# Chỉ dùng TEXT response — Gemini Live nhận transcript, agent xử lý, Live đọc lại
LIVE_CONFIG = {
    "response_modalities": ["AUDIO"],
    "input_audio_transcription": {},   # ← bật transcript input của user
    "output_audio_transcription": {},  # ← bật transcript output để log
    "system_instruction": (
        "You are a voice interface. "
        "When you receive a processed result from the AI agent, read it naturally in Vietnamese. "
        "Keep it conversational and human. No markdown, no bullet points."
    ),
}


# ── Voice Assistant ───────────────────────────────────────────────────────────

class VoiceAssistant:
    def __init__(self):
        self.client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
        self.audio_in_queue = None
        self.audio_out_queue = None
        self.live_session = None
        self.mic_stream = None
        self._running = True
        self._processing = False   # tránh gọi agent 2 lần cùng lúc

    async def listen_mic(self):
        """Capture mic audio liên tục → đưa vào queue."""
        mic_info = pya.get_default_input_device_info()
        self.mic_stream = await asyncio.to_thread(
            pya.open,
            format=FORMAT,
            channels=CHANNELS,
            rate=SEND_SAMPLE_RATE,
            input=True,
            input_device_index=mic_info["index"],
            frames_per_buffer=CHUNK_SIZE,
        )
        print("🎤 Đang lắng nghe... (Ctrl+C để thoát)\n")

        while self._running:
            try:
                chunk = await asyncio.to_thread(
                    self.mic_stream.read,
                    CHUNK_SIZE,
                    exception_on_overflow=False,
                )
                # Không gửi audio khi đang xử lý tool — tránh feedback
                if not self._processing:
                    await self.audio_in_queue.put(chunk)
            except Exception:
                break

    async def send_audio(self):
        """Lấy audio từ queue → gửi lên Gemini Live."""
        while self._running:
            try:
                chunk = await self.audio_in_queue.get()
                await self.live_session.send_realtime_input(
                    audio=types.Blob(
                        data=chunk,
                        mime_type=f"audio/pcm;rate={SEND_SAMPLE_RATE}",
                    )
                )
            except ConnectionClosedError as e:
                print(f"\n[Voice] Connection closed: {e}")
                self._running = False
                break
            except Exception as e:
                print(f"\n[Voice] Send error: {e}")
                self._running = False
                break

    async def receive_response(self):
        """
        Nhận response từ Gemini Live:
        - input_transcription → gọi agent.run() → gửi kết quả lại cho Live đọc
        - audio chunks → play ra speaker
        """
        try:
            async for response in self.live_session.receive():

                # ── User transcript → gọi agent ──────────────────────────────
                if (
                    response.server_content
                    and response.server_content.input_transcription
                ):
                    user_text = response.server_content.input_transcription.text
                    if user_text and user_text.strip() and not self._processing:
                        print(f"\n👤 Bạn: {user_text}")
                        self._processing = True

                        try:
                            # Gọi agent trong thread riêng — không block event loop
                            result = await asyncio.to_thread(agent.run, user_text)

                            if result:
                                print(f"[Agent] Kết quả: {result[:100]}...")

                                # Gửi kết quả text lại cho Gemini Live đọc thành audio
                                await self.live_session.send_client_content(
                                    turns=types.Content(
                                        role="user",
                                        parts=[types.Part(text=result)]
                                    ),
                                    turn_complete=True,
                                )
                        except Exception as e:
                            print(f"[Agent] Error: {e}")
                        finally:
                            self._processing = False

                # ── Audio output chunks → play ─────────────────────────────
                if (
                    response.server_content
                    and response.server_content.model_turn
                ):
                    for part in response.server_content.model_turn.parts:
                        if part.inline_data:
                            await self.audio_out_queue.put(part.inline_data.data)

                # ── Output transcript → log terminal ──────────────────────
                if (
                    response.server_content
                    and response.server_content.output_transcription
                ):
                    transcript = response.server_content.output_transcription.text
                    if transcript:
                        print(f"🤖 Assistant: {transcript}")

        except ConnectionClosedError as e:
            print(f"\n[Voice] Connection closed: {e}")
            self._running = False
        except Exception as e:
            print(f"\n[Voice] Receive error: {e}")
            self._running = False

    async def play_audio(self):
        """Lấy audio từ output queue → phát ra speaker."""
        speaker_stream = await asyncio.to_thread(
            pya.open,
            format=FORMAT,
            channels=CHANNELS,
            rate=RECV_SAMPLE_RATE,
            output=True,
        )
        while self._running:
            try:
                chunk = await asyncio.wait_for(
                    self.audio_out_queue.get(),
                    timeout=1.0,
                )
                await asyncio.to_thread(speaker_stream.write, chunk)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                print(f"\n[Voice] Play error: {e}")
                break

    async def run(self):
        """Main async loop."""
        self.audio_in_queue = asyncio.Queue(maxsize=10)
        self.audio_out_queue = asyncio.Queue()

        print("🚀 Connecting to Gemini Live API...")

        try:
            async with self.client.aio.live.connect(
                model=LIVE_MODEL,
                config=LIVE_CONFIG,
            ) as live_session:
                self.live_session = live_session
                print("✅ Connected! Đeo tai nghe và bắt đầu nói.\n")

                async with asyncio.TaskGroup() as tg:
                    tg.create_task(self.listen_mic())
                    tg.create_task(self.send_audio())
                    tg.create_task(self.receive_response())
                    tg.create_task(self.play_audio())

        except ConnectionClosedError as eg:
            print(f"\n[Voice] Connection dropped: {eg.exceptions[0]}")
        except asyncio.CancelledError:
            pass
        finally:
            self._running = False
            if self.mic_stream:
                self.mic_stream.close()
            pya.terminate()
            print("\n👋 Đã ngắt kết nối.")


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    assistant = VoiceAssistant()
    try:
        asyncio.run(assistant.run())
    except KeyboardInterrupt:
        print("\n👋 Thoát.")
