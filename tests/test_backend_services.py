import asyncio

from web.backend.services.bangumi_api import PAGE_SIZE, fetch_user_subject_ids
from web.backend.services.birthday_svc import BirthdayService


class FakeRedis:
    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    async def get(self, key: str) -> str | None:
        return self.store.get(key)

    async def setex(self, key: str, ttl: int, value: str) -> None:
        self.store[key] = value


class FakeCollection:
    def find(self, *args, **kwargs):  # pragma: no cover
        raise AssertionError("database should not be touched in these tests")


class FakeDB(dict):
    def __missing__(self, key: str) -> FakeCollection:
        value = FakeCollection()
        self[key] = value
        return value


class DummyResponse:
    def __init__(self, payload: dict) -> None:
        self.status_code = 200
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._payload


class RecordingClient:
    def __init__(self, total: int) -> None:
        self.total = total
        self.offsets: list[int] = []
        self.concurrent = 0
        self.max_concurrent = 0

    async def get(self, url: str, *, params: dict) -> DummyResponse:
        offset = params["offset"]
        self.offsets.append(offset)
        self.concurrent += 1
        self.max_concurrent = max(self.max_concurrent, self.concurrent)
        try:
            await asyncio.sleep(0.01)
            if offset == 0:
                data = [{"subject_id": i} for i in range(PAGE_SIZE)]
                return DummyResponse({"total": self.total, "data": data})

            end = min(offset + PAGE_SIZE, self.total)
            data = [{"subject_id": i} for i in range(offset, end)]
            return DummyResponse({"total": self.total, "data": data})
        finally:
            self.concurrent -= 1


async def test_fetch_user_subject_ids_batches_remaining_pages() -> None:
    total = PAGE_SIZE * 4 + 25
    client = RecordingClient(total=total)

    ids = await fetch_user_subject_ids("alice", client=client)

    assert ids == list(range(total))
    assert client.offsets == [0, 100, 200, 300, 400]
    assert client.max_concurrent <= 4


async def test_birthday_service_deduplicates_inflight_subject_fetches() -> None:
    svc = BirthdayService(FakeDB(), FakeRedis())
    started = asyncio.Event()
    release = asyncio.Event()
    calls = 0

    async def fake_fetcher(
        username: str,
        *,
        client: object,
        subject_type: int | None = None,
    ) -> list[int]:
        nonlocal calls
        calls += 1
        started.set()
        await release.wait()
        return [1, 2, 3]

    async def invoke() -> list[int]:
        task = await svc._get_or_create_user_subject_task(  # type: ignore[attr-defined]
            cache_key="user_subjects:alice",
            username="alice",
            http_client=object(),
            subject_type=None,
            fetcher=fake_fetcher,
        )
        return await task

    task1 = asyncio.create_task(invoke())
    await started.wait()
    task2 = asyncio.create_task(invoke())
    await asyncio.sleep(0)
    release.set()

    result1, result2 = await asyncio.gather(task1, task2)

    assert result1 == [1, 2, 3]
    assert result2 == [1, 2, 3]
    assert calls == 1
    assert "user_subjects:alice" not in svc._user_subject_inflight  # type: ignore[attr-defined]
