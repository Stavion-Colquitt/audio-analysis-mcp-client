# audio-analysis-mcp-client

A Python HTTP client for calling the audio-analysis-mcp server from your own orchestrator model or plugin. Use this when you need to drive the MCP server programmatically without going through a Claude or MCP-compatible client.

## What it does

Provides a clean Python interface to every tool in the audio-analysis-mcp server. Your orchestrator imports `MCPClient`, calls methods on it, and the MCP server handles analysis, context building, and database writes. Your models read from Qdrant and never need to interact with this client directly — the data is already there.

## Setup

Make sure the audio-analysis-mcp server is running first, then install the client dependencies:

```bash
pip install qdrant-client
```

No additional dependencies — the client uses Python's built-in `urllib` for HTTP.

## Usage

```python
from orchestrator_client import MCPClient

client = MCPClient()  # defaults to localhost:8000

# Build context before recording starts
client.build_session_context()
client.build_per_section_keys()
client.detect_section_repetitions()

# Write to Qdrant so all models can read it
client.write_context_to_qdrant()

# Start event-driven sync — Ableton changes auto-update Qdrant
client.start_auto_sync()

# Start live listeners during recording
client.start_stt_listener(device_index=1, section_index=0)
client.start_pitch_listener(device_index=1, section_index=0)

# When moving to a new section
client.set_recording_section(1)
client.update_section_heard(0, section_label="verse_1")
client.update_section_in_qdrant(0)

# Override a key for a section that modulates
client.set_section_key_override(section_index=4, key="A minor", label="bridge")
```

## Connecting to a remote server

```python
client = MCPClient(host="192.168.1.100", port=8000)
```

## Calling any tool directly

Every MCP tool is available through the `call` method if you need something not covered by a named method:

```python
result = client.call("get_mix_report")
result = client.call("analyze_bounced_instrumental")
result = client.call("set_key_override", key="E minor")
```

## How it fits together

```
Ableton Live
    ↓  (socket, ableton-mcp Remote Script)
audio-analysis-mcp server
    ↓  (HTTP, this client)
Your orchestrator model
    ↓  (writes)
Qdrant vector database
    ↑  (reads)
Language model / Voice synthesis model
```

The orchestrator calls this client to keep Qdrant current. The language model and voice synthesis model query Qdrant directly — they never touch this client.

## Auto-sync

When `start_auto_sync()` is called, the MCP server opens a persistent connection to the Ableton Remote Script and listens for change events. Tempo changes, time signature changes, and clip modifications automatically trigger re-analysis and Qdrant updates. Your models always read current data without the orchestrator needing to poll or manually trigger updates.
