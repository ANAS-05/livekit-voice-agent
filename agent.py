import logging

from dotenv import load_dotenv
from livekit import agents
from livekit.agents import Agent, AgentServer, AgentSession, JobContext, room_io
from livekit.plugins import noise_cancellation, silero
import httpx
from livekit.agents import function_tool, RunContext, ToolError
from livekit.agents import llm, stt, tts, inference
# Import the multilingual turn detection model
from livekit.plugins.turn_detector.multilingual import MultilingualModel


load_dotenv()


# Define your agent's behavior by extending the Agent class
class Assistant(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions=(
                "You are an upbeat, slightly sarcastic voice AI for tech support. "
                "Help the caller fix issues without rambling, and keep replies under 3 sentences. "
                "You can also look up the weather if asked."
            ),
        )

    # The @function_tool decorator registers this method as a tool the LLM can call
    @function_tool()
    async def lookup_weather(
        self,
        context: RunContext,  # Gives access to the session, speech handle, and user data
        location: str,  # Type hints help the LLM understand what arguments to pass
    ) -> dict:
        """Look up current weather for a location.
        
        Args:
            location: City name or location to get weather for.
        """
        # The docstring above becomes the tool description the LLM sees
        # when deciding which tool to call


        # Let the user know we're working on it
        await context.session.say("Let me search for that...")
        
        async with httpx.AsyncClient() as client:
            # First, geocode the location to get coordinates
            geo_response = await client.get(
                "https://geocoding-api.open-meteo.com/v1/search",
                params={"name": location, "count": 1}
            )
            geo_data = geo_response.json()
            
            if not geo_data.get("results"):
                raise ToolError(f"Could not find location: {location}")
            
            lat = geo_data["results"][0]["latitude"]
            lon = geo_data["results"][0]["longitude"]
            place_name = geo_data["results"][0]["name"]
            
            # Get current weather for those coordinates
            weather_response = await client.get(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    "latitude": lat,
                    "longitude": lon,
                    "current": "temperature_2m,weather_code",
                    "temperature_unit": "fahrenheit"
                }
            )
            weather = weather_response.json()
            
            # Return a dict with the weather data
            # The LLM will use this to form a natural response
            return {
                "location": place_name,
                "temperature_f": weather["current"]["temperature_2m"],
                "conditions": weather["current"]["weather_code"]
            }


server = AgentServer()


# The entrypoint function runs when a participant joins the room
@server.rtc_session()
async def entrypoint(ctx: JobContext):
   
    vad = silero.VAD.load()

    # Configure the voice pipeline with STT, LLM, TTS, and VAD providers
    session = AgentSession(
    # LLM with fallback: OpenAI primary, Gemini backup
    llm=llm.FallbackAdapter(
        [
            inference.LLM(model="openai/gpt-4.1-mini"),
            inference.LLM(model="google/gemini-2.5-flash"),
        ]
    ),
    # STT with fallback: AssemblyAI primary, Deepgram backup
    stt=stt.FallbackAdapter(
        [
            inference.STT.from_model_string("assemblyai/universal-streaming:en"),
            inference.STT.from_model_string("deepgram/nova-3"),
        ]
    ),
    # TTS with fallback: Cartesia primary, Inworld backup
    tts=tts.FallbackAdapter(
        [
            inference.TTS.from_model_string("cartesia/sonic-3:9626c31c-bec5-4cca-baa8-f8ba9e84c8bc"),
            inference.TTS.from_model_string("inworld/inworld-tts-1"),
        ]
    ),
    vad=vad,
    turn_detection=MultilingualModel(),
    )
    # Start the session with noise cancellation enabled
    await session.start(
        agent=Assistant(),
        room=ctx.room,
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(
                noise_cancellation=noise_cancellation.BVC(),  # Background voice cancellation
            ),
        ),
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    agents.cli.run_app(server)