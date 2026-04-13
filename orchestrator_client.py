"""
orchestrator_client.py
=======================
HTTP client for the Audio Analysis MCP server.
Import this in your orchestrator model or plugin to call MCP tools
directly — no Claude required, no intermediary.

Your orchestrator reads from Qdrant for model inference.
This client handles writing TO the MCP server which keeps Qdrant current.

Quick start:
    from orchestrator_client import MCPClient
    client = MCPClient()

    # Before recording starts
    client.build_session_context()
    client.build_per_section_keys()
    client.detect_section_repetitions()
    client.write_context_to_qdrant()
    client.start_auto_sync()          # Ableton changes now auto-update Qdrant

    # During recording
    client.start_stt_listener(device_index=1)
    client.start_pitch_listener(device_index=1)

    # When moving to next section
    client.set_recording_section(1)
    client.update_section_heard(0, "verse_1")
    client.update_section_in_qdrant(0)
"""

import json
import urllib.request
import urllib.error
from typing import Any


class MCPClient:
    """Direct HTTP client for the Audio Analysis MCP server."""

    def __init__(self, host: str = "localhost", port: int = 8000):
        self.base_url = f"http://{host}:{port}"

    def call(self, tool_name: str, **kwargs) -> Any:
        """Call any MCP tool by name. Returns parsed JSON or raises on error."""
        url = f"{self.base_url}/tools/{tool_name}"
        payload = json.dumps(kwargs).encode("utf-8")
        req = urllib.request.Request(
            url, data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read().decode("utf-8")
                try:
                    return json.loads(raw)
                except json.JSONDecodeError:
                    return raw
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8") if e.fp else ""
            raise RuntimeError(f"MCP '{tool_name}' HTTP {e.code}: {body}")
        except urllib.error.URLError as e:
            raise RuntimeError(
                f"Cannot reach MCP server at {self.base_url} — is it running? ({e.reason})"
            )

    # ── Session context ───────────────────────────────────────────────────

    def build_session_context(self, vocal_file_path: str = "") -> dict:
        """Build full pre-session context. Call once before recording starts."""
        return self.call("build_session_context", vocal_file_path=vocal_file_path)

    def get_current_session_context(self) -> dict:
        """Get current session context with all updates."""
        return self.call("get_current_session_context")

    def get_song_context(self) -> dict:
        """Get full musical context for ML model initialization."""
        return self.call("get_song_context")

    # ── Key detection ─────────────────────────────────────────────────────

    def get_key_with_voting(self, vocal_file_path: str = "") -> dict:
        return self.call("get_key_with_voting", vocal_file_path=vocal_file_path)

    def get_key_from_midi(self, melodic_track_indices: list,
                          vocal_file_path: str = "") -> dict:
        return self.call("get_key_from_midi",
                         melodic_track_indices=melodic_track_indices,
                         vocal_file_path=vocal_file_path)

    def set_key_override(self, key: str = "") -> str:
        """Set global key override. Pass empty string to clear."""
        return self.call("set_key_override", key=key)

    def get_key_override(self) -> dict:
        return self.call("get_key_override")

    # ── Section structure ─────────────────────────────────────────────────

    def build_per_section_keys(self) -> dict:
        """Run key detection per section. Supports mid-song modulations."""
        return self.call("build_per_section_keys")

    def set_section_key_override(self, section_index: int,
                                  key: str, label: str = "") -> dict:
        """Override key for a specific section."""
        return self.call("set_section_key_override",
                         section_index=section_index, key=key, label=label)

    def detect_section_repetitions(self) -> dict:
        """Find verse/chorus patterns by MIDI fingerprinting."""
        return self.call("detect_section_repetitions")

    def update_section_heard(self, section_index: int,
                              section_label: str = "") -> dict:
        """Mark section complete. Updates prior confidence."""
        return self.call("update_section_heard",
                         section_index=section_index,
                         section_label=section_label)

    def set_recording_section(self, section_index: int) -> dict:
        """Tell STT and pitch listeners which section is active."""
        return self.call("set_recording_section", section_index=section_index)

    # ── Live listeners ────────────────────────────────────────────────────

    def start_stt_listener(self, device_index: int,
                            section_index: int = 0) -> str:
        """Start Whisper transcription. Writes lyrics to performed layer."""
        return self.call("start_stt_listener",
                         device_index=device_index, section_index=section_index)

    def stop_stt_listener(self) -> str:
        return self.call("stop_stt_listener")

    def start_pitch_listener(self, device_index: int,
                              section_index: int = 0) -> str:
        """Start vocal pitch tracking. Writes notes to performed layer."""
        return self.call("start_pitch_listener",
                         device_index=device_index, section_index=section_index)

    def stop_pitch_listener(self) -> str:
        return self.call("stop_pitch_listener")

    # ── Performed context ─────────────────────────────────────────────────

    def get_performed_context(self, section_index: int = -1) -> dict:
        """Get captured lyrics, notes, instrument data for a section."""
        return self.call("get_performed_context", section_index=section_index)

    # ── Instrument analysis ───────────────────────────────────────────────

    def analyze_instrument_audio(self, file_path: str,
                                  track_name: str = "unknown",
                                  section_index: int = -1) -> dict:
        """Run Basic-Pitch on polyphonic audio (piano, guitar, violin)."""
        return self.call("analyze_instrument_audio",
                         file_path=file_path, track_name=track_name,
                         section_index=section_index)

    # ── Vector database ───────────────────────────────────────────────────

    def write_context_to_qdrant(
        self,
        qdrant_url: str = "http://localhost:6333",
        collection_name: str = "backing_vocalist_context"
    ) -> dict:
        """Write full session context to Qdrant. One point per section."""
        return self.call("write_context_to_qdrant",
                         qdrant_url=qdrant_url,
                         collection_name=collection_name)

    def update_section_in_qdrant(
        self,
        section_index: int,
        qdrant_url: str = "http://localhost:6333",
        collection_name: str = "backing_vocalist_context"
    ) -> dict:
        """Update a single section in Qdrant after new data is captured."""
        return self.call("update_section_in_qdrant",
                         section_index=section_index,
                         qdrant_url=qdrant_url,
                         collection_name=collection_name)

    # ── Auto-sync ─────────────────────────────────────────────────────────

    def start_auto_sync(
        self,
        qdrant_url: str = "http://localhost:6333",
        collection_name: str = "backing_vocalist_context"
    ) -> dict:
        """
        Start event-driven Qdrant sync.
        Ableton changes (tempo, time sig, clips) automatically
        trigger re-analysis and Qdrant updates — no polling needed.
        Your models always read fresh data without doing anything.
        """
        return self.call("start_auto_sync",
                         qdrant_url=qdrant_url,
                         collection_name=collection_name)

    def stop_auto_sync(self) -> str:
        return self.call("stop_auto_sync")

    def get_auto_sync_status(self) -> dict:
        return self.call("get_auto_sync_status")

    # ── Mix analysis ──────────────────────────────────────────────────────

    def list_audio_devices(self) -> str:
        return self.call("list_audio_devices")

    def start_capture(self, device_index: int,
                      window_seconds: float = 8.0) -> str:
        return self.call("start_capture",
                         device_index=device_index,
                         window_seconds=window_seconds)

    def stop_capture(self) -> str:
        return self.call("stop_capture")

    def get_mix_analysis(self) -> dict:
        return self.call("get_mix_analysis")

    def get_mix_report(self) -> str:
        return self.call("get_mix_report")

    def get_frequency_report(self) -> str:
        """Focused frequency balance report with EQ suggestions."""
        return self.call("get_frequency_report")

    def get_stereo_analysis(self) -> dict:
        """Stereo width, mono compatibility, L/R balance."""
        return self.call("get_stereo_analysis")

    def capture_and_analyze_file(self, file_path: str) -> dict:
        return self.call("capture_and_analyze_file", file_path=file_path)

    def analyze_bounced_instrumental(self) -> dict:
        """Detect key from a session with only a bounced WAV/MP3 (no MIDI)."""
        return self.call("analyze_bounced_instrumental")

    def start_polyphonic_listener(self, device_index: int,
                                   track_name: str = "instrument",
                                   section_index: int = 0,
                                   window_seconds: float = 2.5) -> dict:
        """
        Start live polyphonic chord/harmony detection via Basic-Pitch.
        For piano, guitar, violin, or any instrument playing multiple notes.
        Use Ableton MIDI routing instead when available — zero latency and exact.
        """
        return self.call("start_polyphonic_listener",
                         device_index=device_index,
                         track_name=track_name,
                         section_index=section_index,
                         window_seconds=window_seconds)

    def stop_polyphonic_listener(self) -> str:
        return self.call("stop_polyphonic_listener")
