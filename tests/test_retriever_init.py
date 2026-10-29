"""Retriever initialisation: the index singleton must never cache a half-built
instance.

Keyless and serverless. Regression cover for the defect where get_retriever()
published an unbuilt FAISSRetriever before build() finished, so an interrupted
or failed build left every later call raising "Index not built" until the
process restarted. These tests read engine._retriever directly because the
cache itself is what is under test. Run from the repo root with:
python -m pytest tests/ -v
"""

import threading

import pytest

import engine


@pytest.fixture(autouse=True)
def reset_singleton():
    """Isolate each test from the process-wide retriever cache."""
    original = engine._retriever
    engine._retriever = None
    yield
    engine._retriever = original


class _StubRetriever:
    """Stands in for a built retriever without loading an embedding model."""


# ─── A failed build must not be cached ───────────────────────────────────────

def test_failed_build_is_not_cached(monkeypatch):
    """Patches FAISSRetriever.build, not build_retriever, so this holds whatever
    shape get_retriever() takes internally."""
    def boom(self, documents) -> None:
        raise RuntimeError("embedding model unavailable")

    monkeypatch.setattr(engine.FAISSRetriever, "build", boom)

    with pytest.raises(RuntimeError, match="embedding model unavailable"):
        engine.get_retriever()

    assert engine._retriever is None


def test_retry_after_failed_build_succeeds(monkeypatch):
    attempts = []

    def boom() -> engine.FAISSRetriever:
        attempts.append("fail")
        raise RuntimeError("embedding model unavailable")

    monkeypatch.setattr(engine, "build_retriever", boom)
    with pytest.raises(RuntimeError):
        engine.get_retriever()

    stub = _StubRetriever()
    monkeypatch.setattr(engine, "build_retriever", lambda: stub)

    assert engine.get_retriever() is stub
    assert len(attempts) == 1


# ─── A successful build is cached exactly once ───────────────────────────────

def test_successful_build_is_cached(monkeypatch):
    builds = []

    def build() -> _StubRetriever:
        stub = _StubRetriever()
        builds.append(stub)
        return stub

    monkeypatch.setattr(engine, "build_retriever", build)

    first  = engine.get_retriever()
    second = engine.get_retriever()

    assert first is second
    assert len(builds) == 1


def test_concurrent_first_callers_build_once(monkeypatch):
    builds  = []
    results = []
    barrier = threading.Barrier(8)

    def build() -> _StubRetriever:
        stub = _StubRetriever()
        builds.append(stub)
        return stub

    monkeypatch.setattr(engine, "build_retriever", build)

    def worker() -> None:
        barrier.wait(timeout=10)
        results.append(engine.get_retriever())

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=20)

    assert len(builds) == 1
    assert len(results) == 8
    assert all(r is builds[0] for r in results)
