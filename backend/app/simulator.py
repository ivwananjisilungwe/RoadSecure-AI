import asyncio
import logging
from contextlib import suppress

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import delete

from .auth import Administrator, CurrentUser, Database, log_action
from .detection import simulate
from .models import Alert, Incident, IncidentHistory, SecurityEvent
from .monitoring import event_data, save_event
from .schemas import EventInput, LiveSimulationInput, SimulationInput, SimulationReset

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/simulator", tags=["Simulator"])


def generate_batch(db, detector, scenario, source_system, count):
    return [
        save_event(db, detector, EventInput.model_validate(simulate(scenario, source_system)))
        for _ in range(count)
    ]


class LiveSimulator:
    def __init__(self, session_factory, detector):
        self.session_factory = session_factory
        self.detector = detector
        self.config = None
        self.stop_event = asyncio.Event()
        self.task = None
        self.generated = 0
        self.error = None

    def status(self):
        return {
            "running": bool(self.task and not self.task.done()),
            "scenario": self.config.scenario if self.config else None,
            "source_system": self.config.source_system if self.config else None,
            "interval_seconds": self.config.interval_seconds if self.config else None,
            "generated": self.generated,
            "error": self.error,
        }

    def start(self, config):
        if self.task and not self.task.done():
            raise HTTPException(409, "The simulator is already running")
        self.config = config
        self.generated = 0
        self.error = None
        self.stop_event.clear()
        self.task = asyncio.create_task(self._run(config))

    async def stop(self):
        self.stop_event.set()
        if self.task:
            await self.task

    def _write_event(self, config):
        with self.session_factory.begin() as db:
            generate_batch(db, self.detector, config.scenario, config.source_system, 1)

    async def _run(self, config):
        try:
            while not self.stop_event.is_set():
                await asyncio.to_thread(self._write_event, config)
                self.generated += 1
                with suppress(TimeoutError):
                    await asyncio.wait_for(self.stop_event.wait(), config.interval_seconds)
        except Exception:
            logger.exception("Live synthetic simulation stopped")
            self.error = "An event could not be stored. Check the local backend logs."


@router.post("/generate", status_code=201)
def generate_events(payload: SimulationInput, request: Request, db: Database, user: CurrentUser):
    records = generate_batch(
        db, request.app.state.detector, payload.scenario, payload.source_system, payload.count,
    )
    log_action(db, user.id, "SIMULATION_GENERATED", f"{payload.scenario}: {len(records)} events")
    db.commit()
    return {"events": [event_data(record) for record in records]}


@router.post("/start")
async def start_live(payload: LiveSimulationInput, request: Request, db: Database, user: CurrentUser):
    live = request.app.state.live_simulator
    if live.status()["running"]:
        raise HTTPException(409, "The simulator is already running")
    log_action(db, user.id, "SIMULATION_STARTED", payload.scenario)
    db.commit()
    live.start(payload)
    return live.status()


@router.post("/stop")
async def stop_live(request: Request, db: Database, user: CurrentUser):
    live = request.app.state.live_simulator
    await live.stop()
    log_action(db, user.id, "SIMULATION_STOPPED", f"{live.generated} events")
    db.commit()
    return live.status()


@router.get("/status")
async def get_status(request: Request, user: CurrentUser):
    return request.app.state.live_simulator.status()


@router.post("/reset")
async def reset_simulation(payload: SimulationReset, request: Request, db: Database, admin: Administrator):
    if request.app.state.live_simulator.status()["running"]:
        raise HTTPException(409, "Stop the live simulator before resetting")
    db.execute(delete(IncidentHistory))
    counts = {
        "deleted_incidents": db.execute(delete(Incident)).rowcount,
        "deleted_alerts": db.execute(delete(Alert)).rowcount,
        "deleted_events": db.execute(delete(SecurityEvent)).rowcount,
    }
    log_action(db, admin.id, "SIMULATION_RESET", ", ".join(f"{key}: {value}" for key, value in counts.items()))
    db.commit()
    return counts
