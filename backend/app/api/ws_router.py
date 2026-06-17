from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, HTTPException
import json
import logging
import asyncio
import time
from typing import Optional, List

from app.core.realtime_engine import realtime_simulator
from app.models.schemas import FactorWorkflow

logger = logging.getLogger(__name__)
router = APIRouter(tags=["realtime"])


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, session_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[session_id] = websocket
        logger.info(f"WebSocket connected: {session_id}")

    def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]
            logger.info(f"WebSocket disconnected: {session_id}")

    async def send_message(self, session_id: str, message: dict):
        if session_id in self.active_connections:
            try:
                await self.active_connections[session_id].send_text(json.dumps(message, default=str))
            except Exception as e:
                logger.error(f"Failed to send message to {session_id}: {e}")
                self.disconnect(session_id)

    async def broadcast(self, message: dict):
        for session_id in list(self.active_connections.keys()):
            await self.send_message(session_id, message)


manager = ConnectionManager()


@router.websocket("/realtime")
async def websocket_endpoint(
    websocket: WebSocket,
    dataset_name: str = Query(..., description="数据集名称"),
    workflow: str = Query(..., description="工作流JSON字符串"),
    push_interval: float = Query(1.0, ge=0.1, le=60.0, description="推送间隔秒数")
):
    try:
        workflow_dict = json.loads(workflow)
        wf = FactorWorkflow(**workflow_dict)
    except Exception as e:
        await websocket.close(code=4001, reason=f"Invalid workflow JSON: {str(e)}")
        return

    session = None
    session_id = None

    try:
        session = await realtime_simulator.create_session(dataset_name, wf, push_interval)
        session_id = session.session_id

        await manager.connect(session_id, websocket)

        await manager.send_message(session_id, {
            "type": "session_start",
            "data": {
                "session_id": session_id,
                "dataset": dataset_name,
                "workflow_name": wf.name,
                "n_dates": len(session._dates) if session._dates else 0,
                "push_interval": push_interval
            },
            "timestamp": time.time()
        })

        async def on_data(message):
            await manager.send_message(session_id, message)

        session.add_callback(on_data)

        while True:
            try:
                data = await websocket.receive_text()
                msg = json.loads(data)

                if msg.get("type") == "ping":
                    await manager.send_message(session_id, {
                        "type": "pong",
                        "data": {"server_time": time.time()},
                        "timestamp": time.time()
                    })
                elif msg.get("type") == "control":
                    action = msg.get("action")
                    if action == "pause":
                        if session._task:
                            session._task.cancel()
                        session._running = False
                        await manager.send_message(session_id, {
                            "type": "status",
                            "data": {"status": "paused"},
                            "timestamp": time.time()
                        })
                    elif action == "resume":
                        session._running = True
                        session._task = session._task = asyncio.create_task(session._push_loop())
                        await manager.send_message(session_id, {
                            "type": "status",
                            "data": {"status": "running"},
                            "timestamp": time.time()
                        })

            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"WebSocket message error: {e}")
                break

    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        if websocket.client_state != 3:
            try:
                await websocket.close(code=4002, reason=str(e))
            except Exception:
                pass
    finally:
        if session_id:
            manager.disconnect(session_id)
        if session_id:
            try:
                await realtime_simulator.close_session(session_id)
            except Exception:
                pass
        logger.info(f"WebSocket cleaned up: {session_id}")
