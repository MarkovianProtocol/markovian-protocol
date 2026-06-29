"""
demo_agent — a minimal REAL A2A agent (a2a-sdk 1.1.0) that carries Markovian provenance.

- Declares the Markovian provenance extension in its AgentCard (capabilities.extensions[]).
- On every task, produces an output, STAMPs it on the live Markovian chain (burns 1 MKV),
  and attaches the canonical markovian-provenance/v1 object to Artifact.metadata,
  keyed by the extension URI (Artifact-primary). Also lists the URI in Artifact.extensions.

Run standalone:  /Users/colinwinter/neo_env/bin/python3 demo_agent.py
Binds: 127.0.0.1:8090   (JSON-RPC at /, AgentCard at /.well-known/agent-card.json)
"""

import asyncio
import sys
import uuid

sys.path.insert(0, "/Users/colinwinter/markovian/a2a")

import uvicorn
from starlette.applications import Starlette

import a2a.types as T
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes.agent_card_routes import create_agent_card_routes
from a2a.server.routes.jsonrpc_routes import create_jsonrpc_routes
from a2a.server.tasks import InMemoryTaskStore, TaskUpdater

import markovian_a2a as mp

HOST = "127.0.0.1"
PORT = 8090
STAMP_WALLET = "135nd7CXWJ8QRjuCDkXoM5oxx9MKc7YNjN"  # genesis demo wallet (~2700 MKV)


def build_agent_card() -> T.AgentCard:
    ext = T.AgentExtension(
        uri=mp.EXT_URI,
        description=("Outputs carry Markovian provenance (timestamped, chain-recorded, "
                     "independently verifiable). Proves provenance, not correctness."),
        required=False,
    )
    ext.params.update({
        "verifier": "https://api.quantsynth.net/verify/",
        "commitment": "bn128-pedersen",
    })

    caps = T.AgentCapabilities(streaming=False)
    caps.extensions.append(ext)

    card = T.AgentCard(
        name="Markovian Provenance Demo Agent",
        description="Demo A2A agent: every artifact it returns carries a verifiable Markovian STAMP.",
        version="1.0.0",
        capabilities=caps,
        default_input_modes=["text/plain"],
        default_output_modes=["text/plain"],
    )
    card.skills.append(T.AgentSkill(
        id="regime-read",
        name="Regime read",
        description="Returns a (demo) market-regime read, provenance-stamped.",
        tags=["demo", "provenance", "markovian"],
    ))
    card.supported_interfaces.append(T.AgentInterface(
        url=f"http://{HOST}:{PORT}/",
        protocol_binding="JSONRPC",  # TransportProtocol.JSONRPC value; field is a plain string
        protocol_version="1.0",
    ))
    return card


class ProvenanceAgentExecutor(AgentExecutor):
    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        # Activation signals the consumer sent (A2A-Extensions header / message.extensions).
        requested = list(getattr(context, "requested_extensions", None) or [])
        msg_ext = list(context.message.extensions) if context.message else []
        print(f"[agent] requested_extensions(header)={requested} message.extensions={msg_ext}",
              flush=True)

        task_id = context.task_id or str(uuid.uuid4())
        context_id = context.context_id or str(uuid.uuid4())
        updater = TaskUpdater(event_queue, task_id, context_id)
        if not context.current_task:
            # The aggregator requires a Task object enqueued before any status update.
            await event_queue.enqueue_event(T.Task(
                id=task_id,
                context_id=context_id,
                status=T.TaskStatus(state=T.TaskState.TASK_STATE_SUBMITTED),
            ))
        await updater.start_work()

        # 1. Produce the output.
        payload = {
            "answer": "QQQ regime: DISTRIBUTION (demo)",
            "confidence": 0.52,
            "agent": "Markovian Provenance Demo Agent",
            "task_id": task_id,
        }
        raw = mp.canon(payload)  # canonical bytes == what /stamp hashes

        # 2. STAMP it on the live Markovian chain (burns 1 MKV). Off the event loop.
        obj = await asyncio.to_thread(mp.stamp_output, payload, STAMP_WALLET,
                                      f"A2A demo artifact {task_id[:8]}")
        print(f"[agent] stamped merkle_root={obj['merkle_root']} block_height={obj['block_height']}",
              flush=True)

        # 3. Emit a real A2A Artifact with provenance in metadata (Artifact-primary).
        await updater.add_artifact(
            parts=[T.Part(text=raw)],
            name="result",
            metadata={mp.EXT_URI: obj},
            extensions=[mp.EXT_URI],
        )
        await updater.complete()

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        raise NotImplementedError("cancel not supported in demo")


def build_app() -> Starlette:
    card = build_agent_card()
    handler = DefaultRequestHandler(
        agent_executor=ProvenanceAgentExecutor(),
        task_store=InMemoryTaskStore(),
        agent_card=card,
    )
    routes = create_jsonrpc_routes(handler, "/") + create_agent_card_routes(card)
    return Starlette(routes=routes)


if __name__ == "__main__":
    uvicorn.run(build_app(), host=HOST, port=PORT, log_level="error")
