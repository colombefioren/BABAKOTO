"""LiveKit worker entrypoint: `python -m babakoto_agent.worker dev`."""

import asyncio
import json
import logging

from dotenv import load_dotenv
from livekit.agents import AgentServer, AgentSession, JobContext, cli
from livekit.agents.voice.events import ConversationItemAddedEvent
from livekit.plugins import silero

from babakoto_agent.config import AgentSettings
from babakoto_agent.latency import TOPIC, turn_latency
from babakoto_agent.session import BabakotoAgent, build_session

log = logging.getLogger("babakoto.agent")

server = AgentServer()


def _prewarm(proc: object) -> None:
    """Load the VAD model once per process, before any call arrives."""
    settings = AgentSettings()
    proc.userdata["vad"] = silero.VAD.load(  # type: ignore[attr-defined]
        min_silence_duration=settings.vad_min_silence_s
    )


server.setup_fnc = _prewarm


def _publish_latency(ctx: JobContext, session: AgentSession[None]) -> None:
    """Send each reply's latency to the room so the playground can show it."""

    pending: set[asyncio.Future[None]] = set()

    def on_item(event: ConversationItemAddedEvent) -> None:
        item = event.item
        if getattr(item, "role", None) != "assistant":
            return
        latency = turn_latency(getattr(item, "metrics", None))
        if latency is None:
            return
        log.info("turn latency e2e=%.3fs", latency.e2e)
        payload = json.dumps(latency.to_json()).encode()
        task = asyncio.ensure_future(
            ctx.room.local_participant.publish_data(payload, topic=TOPIC, reliable=True)
        )
        pending.add(task)
        task.add_done_callback(pending.discard)

    session.on("conversation_item_added", on_item)


@server.rtc_session()
async def entrypoint(ctx: JobContext) -> None:
    settings = AgentSettings()
    logging.getLogger().setLevel(settings.log_level)
    session = build_session(settings, vad=ctx.proc.userdata.get("vad"))
    _publish_latency(ctx, session)
    await session.start(agent=BabakotoAgent(settings), room=ctx.room)


def main() -> None:
    load_dotenv()
    cli.run_app(server)


if __name__ == "__main__":
    main()
