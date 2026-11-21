"""Phase 5 step 4: POST /v1/route (fake models, no network). The legacy endpoints keep their own tests."""
import json

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from router.config import RouterConfig
from router.fakes import FakeClient
from router.pipeline import Router
from router.policy import Policy, placeholder_policy
from src.api.routes import get_phase5_router
from src.main import app


class FixedLabeler:
    def __init__(self, cat, diff="easy"):
        self.cat, self.diff = cat, diff

    def label(self, prompt):
        return {"category": self.cat, "difficulty": self.diff, "path": "rule", "confidence": 1.0}


def make_router(handler, cat="sentiment", log=None):
    cfg = RouterConfig()
    cfg.log_path = log
    return Router(Policy(placeholder_policy()), FakeClient(handler), FixedLabeler(cat), cfg)


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture
async def key(client):
    r = await client.post("/v1/keys", json={"name": "route test"})
    return r.json()["key"]


@pytest.fixture(autouse=True)
def _clear_override():
    yield
    app.dependency_overrides.pop(get_phase5_router, None)


def use(router):
    app.dependency_overrides[get_phase5_router] = lambda: router


@pytest.mark.asyncio
async def test_route_local_answer_has_all_fields(client, key, tmp_path):
    log = tmp_path / "req.jsonl"
    use(make_router(lambda *a: "Fine.\nANSWER: positive", log=log))
    r = await client.post("/v1/route", json={"prompt": "What is the sentiment of: lovely"}, headers={"X-API-Key": key})
    assert r.status_code == 200
    d = r.json()
    assert d["answer"].endswith("ANSWER: positive") and d["category"] == "sentiment" and d["difficulty"] == "easy"
    assert d["layer"] == "local" and d["model"] == "gemma3:4b" and d["escalated"] is False
    assert d["cost_usd"] == 0 and d["savings_usd"] == d["b1_cost_usd"] > 0 and d["trace"]
    line = json.loads(log.read_text(encoding="utf-8").splitlines()[0])
    assert line["layer"] == "local" and "prompt" not in line and line["request_id"]


@pytest.mark.asyncio
async def test_route_escalates_and_reports_cost(client, key):
    use(make_router(lambda m, *a: "garbage" if m == "gemma3:4b" else "Fine.\nANSWER: negative"))
    r = await client.post("/v1/route", json={"prompt": "What is the sentiment of: awful"}, headers={"X-API-Key": key})
    d = r.json()
    assert r.status_code == 200 and d["layer"] == "api" and d["model"] == "kimi-k3p1-pro" and d["escalated"] and d["cost_usd"] > 0


@pytest.mark.asyncio
async def test_route_out_of_scope_goes_to_b1(client, key):
    use(make_router(lambda *a: "a poem", cat="out_of_scope"))
    d = (await client.post("/v1/route", json={"prompt": "Write a poem"}, headers={"X-API-Key": key})).json()
    assert d["category"] == "out_of_scope" and d["model"] == "kimi-k3p1-pro" and d["layer"] == "api"


@pytest.mark.asyncio
async def test_route_all_steps_failed_is_503(client, key):
    use(make_router(lambda *a: RuntimeError("down")))
    r = await client.post("/v1/route", json={"prompt": "What is the sentiment of: x"}, headers={"X-API-Key": key})
    assert r.status_code == 503


@pytest.mark.asyncio
async def test_route_requires_api_key_and_valid_body(client):
    use(make_router(lambda *a: "x"))
    assert (await client.post("/v1/route", json={"prompt": "hi"})).status_code == 401
    assert (await client.post("/v1/route", json={"prompt": "hi"}, headers={"X-API-Key": "smr_bad"})).status_code == 401
    r = await client.post("/v1/route", json={"prompt": ""}, headers={"X-API-Key": "smr_bad"})
    assert r.status_code in (401, 422)


@pytest.mark.asyncio
async def test_route_writes_request_log_table(client, key):
    from src.db import RequestLog, get_session
    use(make_router(lambda *a: "Fine.\nANSWER: positive"))
    import hashlib
    import uuid
    prompt = f"What is the sentiment of: {uuid.uuid4().hex}"      # unique: the dev DB persists between runs
    r = await client.post("/v1/route", json={"prompt": prompt}, headers={"X-API-Key": key})
    assert r.status_code == 200
    h = hashlib.sha256(prompt.encode()).hexdigest()
    async for s in get_session():
        rows = (await s.execute(select(RequestLog).where(RequestLog.prompt_hash == h))).scalars().all()
        assert len(rows) == 1 and rows[0].model_used == "gemma3:4b" and rows[0].estimated_cost == 0 and rows[0].cost_saved > 0
        break


@pytest.mark.asyncio
async def test_legacy_endpoints_still_listed_and_marked(client):
    spec = (await client.get("/openapi.json")).json()
    assert "/v1/route" in spec["paths"]
    for p in ("/v1/complete", "/v1/structure"):
        assert spec["paths"][p]["post"]["deprecated"] is True and "legacy" in spec["paths"][p]["post"]["summary"].lower()
    assert not spec["paths"]["/v1/route"]["post"].get("deprecated")
