"""Integration tests for WebSocket functionality."""

import json

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect
from backend.api.app import create_app
from backend.api.websocket import manager


@pytest.fixture
def client():
    app = create_app()
    with TestClient(app) as c:
        yield c


class TestWebsocketConnect:
    def test_connect_to_valid_channel(self, client):
        with client.websocket_connect("/ws?channel=agent") as ws:
            msg = ws.receive_text()
            data = json.loads(msg)
            assert data["type"] == "connected"
            assert data["payload"]["channel"] == "agent"

    def test_connect_to_workflow_channel(self, client):
        with client.websocket_connect("/ws?channel=workflow") as ws:
            msg = ws.receive_text()
            data = json.loads(msg)
            assert data["type"] == "connected"
            assert data["payload"]["channel"] == "workflow"

    def test_connect_to_content_channel(self, client):
        with client.websocket_connect("/ws?channel=content") as ws:
            msg = ws.receive_text()
            data = json.loads(msg)
            assert data["type"] == "connected"
            assert data["payload"]["channel"] == "content"

    def test_connect_to_system_channel(self, client):
        with client.websocket_connect("/ws?channel=system") as ws:
            msg = ws.receive_text()
            data = json.loads(msg)
            assert data["type"] == "connected"
            assert data["payload"]["channel"] == "system"

    def test_connect_with_token(self, client):
        from backend.core.auth import create_access_token
        token = create_access_token({"sub": "user-123", "email": "test@example.com"})

        with client.websocket_connect(f"/ws?channel=agent&token={token}") as ws:
            msg = ws.receive_text()
            data = json.loads(msg)
            assert data["type"] == "connected"
            assert data["payload"]["user_id"] == "user-123"

    def test_connect_with_invalid_token(self, client):
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect("/ws?channel=agent&token=bad.token.here"):
                pass

    def test_connect_without_token(self, client):
        with client.websocket_connect("/ws?channel=agent") as ws:
            msg = ws.receive_text()
            data = json.loads(msg)
            assert data["type"] == "connected"
            assert data["payload"]["user_id"] is None


class TestWebsocketInvalidChannel:
    def test_invalid_channel_rejected(self, client):
        with pytest.raises(Exception):
            with client.websocket_connect("/ws?channel=invalid_channel"):
                pass

    def test_empty_channel_rejected(self, client):
        with pytest.raises(Exception):
            with client.websocket_connect("/ws?channel="):
                pass


class TestWebsocketBroadcast:
    def test_broadcast_message(self, client):
        with client.websocket_connect("/ws?channel=agent") as ws:
            ws.receive_text()

            ws.send_text(json.dumps({
                "type": "broadcast",
                "payload": {"text": "hello everyone"},
            }))
            msg1 = ws.receive_text()
            data1 = json.loads(msg1)
            msg2 = ws.receive_text()
            data2 = json.loads(msg2)
            types = {data1["type"], data2["type"]}
            assert "broadcast_sent" in types
            assert "message" in types
            for data in [data1, data2]:
                if data["type"] == "broadcast_sent":
                    assert data["payload"]["channel"] == "agent"
                    assert data["payload"]["recipient_count"] >= 1

    def test_broadcast_received_by_peer(self, client):
        with client.websocket_connect("/ws?channel=content") as ws1:
            ws1.receive_text()

            with client.websocket_connect("/ws?channel=content") as ws2:
                ws2.receive_text()

                ws1.send_text(json.dumps({
                    "type": "broadcast",
                    "payload": {"text": "hello from ws1"},
                }))
                ws1.receive_text()

                msg = ws2.receive_text()
                data = json.loads(msg)
                assert data["type"] == "message"
                assert data["payload"]["text"] == "hello from ws1"

    def test_ping_pong(self, client):
        with client.websocket_connect("/ws?channel=agent") as ws:
            ws.receive_text()

            ws.send_text(json.dumps({"type": "ping"}))
            msg = ws.receive_text()
            data = json.loads(msg)
            assert data["type"] == "pong"

    def test_invalid_json_handled(self, client):
        with client.websocket_connect("/ws?channel=agent") as ws:
            ws.receive_text()

            ws.send_text("not json at all")
            msg = ws.receive_text()
            data = json.loads(msg)
            assert data["type"] == "error"
            assert "Invalid JSON" in data["payload"]["message"]

    def test_message_broadcasts_to_all(self, client):
        with client.websocket_connect("/ws?channel=system") as ws1:
            ws1.receive_text()
            with client.websocket_connect("/ws?channel=system") as ws2:
                ws2.receive_text()
                with client.websocket_connect("/ws?channel=system") as ws3:
                    ws3.receive_text()

                    ws1.send_text(json.dumps({
                        "type": "broadcast",
                        "payload": {"data": "from ws1"},
                    }))
                    ws1.receive_text()

                    msg2 = ws2.receive_text()
                    msg3 = ws3.receive_text()
                    d2 = json.loads(msg2)
                    d3 = json.loads(msg3)
                    assert d2["type"] == "message"
                    assert d3["type"] == "message"
                    assert d2["payload"]["data"] == "from ws1"
                    assert d3["payload"]["data"] == "from ws1"


class TestConnectionManager:
    def test_channel_count(self):
        manager._channels.clear()
        manager._connections.clear()

        class FakeWS:
            client_state = "connected"

        ws1 = FakeWS()
        ws2 = FakeWS()
        manager._channels["test"] = {ws1, ws2}
        assert manager.get_channel_count("test") == 2

    def test_total_connections(self):
        manager._channels.clear()
        manager._connections.clear()

        class FakeWS:
            client_state = "connected"

        ws = FakeWS()
        manager._channels["ch1"] = {ws}
        manager._connections[ws] = {"ch1"}
        assert manager.get_total_connections() == 1

    def test_channel_stats(self):
        manager._channels.clear()
        manager._connections.clear()
        manager._channels["a"] = set()
        manager._channels["b"] = set()
        stats = manager.get_channel_stats()
        assert "a" in stats
        assert "b" in stats
