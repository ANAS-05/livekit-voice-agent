# livekit-voice-agent

A basic LiveKit voice agent implementation, built on [LiveKit Agents](https://docs.livekit.io/agents/). Includes two tool calls (current time, exam result lookup) for learning purposes.

## Setup

Requires Python 3.14+ and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
```

Copy your LiveKit and provider credentials into `.env` (see LiveKit docs for required keys).

## Run

Pre-download plugin assets (one-time, optional but speeds up the first run):

```bash
uv run agent.py download-files
```

Console mode (in-terminal mic/speaker):

```bash
uv run agent.py console
```

Dev mode (connect from LiveKit Playground or your own client):

```bash
uv run agent.py dev
```

## Project layout

```
agent.py    # Agent definition and session config
tools.py    # LLM-callable tools
parser.py   # HTML → typed model parsers
schemas.py  # Pydantic models
```

## Adding a tool

Add a `@function_tool()` async function in `tools.py` and include it in the `tools=[...]` list in `Assistant.__init__`.
