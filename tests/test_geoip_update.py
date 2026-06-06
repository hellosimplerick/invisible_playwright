"""Unit tests for the intelligent geoip mmdb auto-update in `download.py`.

daijro/geoip-all-in-one rebuilds weekly; `ensure_geoip_mmdb` keeps the cache
fresh without a download (or API call) on every launch. These tests mock the
cache root, the latest-tag API, and the per-tag download so nothing touches the
network.
"""
import os
import time

import pytest

import invisible_playwright.download as dl


@pytest.fixture
def cache(tmp_path, monkeypatch):
    """Point the cache at tmp_path and clear the env override."""
    monkeypatch.setattr(dl, "cache_root", lambda: tmp_path)
    monkeypatch.delenv("STEALTHFOX_GEOIP_MMDB", raising=False)
    return tmp_path


def _make_cached(root, tag, name=dl.GEOIP_MMDB_NAME):
    d = root / "geoip" / tag
    d.mkdir(parents=True, exist_ok=True)
    f = d / name
    f.write_bytes(b"FAKE-MMDB")
    return f


def _set_marker_age(root, days):
    m = root / "geoip" / ".last_check"
    m.parent.mkdir(parents=True, exist_ok=True)
    m.touch()
    old = time.time() - days * 86400
    os.utime(m, (old, old))


# ──────────────────────────────────────────────────────────────────────
#  env override
# ──────────────────────────────────────────────────────────────────────
@pytest.mark.unit
def test_env_override_returns_file(tmp_path, monkeypatch):
    f = tmp_path / "mine.mmdb"
    f.write_bytes(b"X")
    monkeypatch.setenv("STEALTHFOX_GEOIP_MMDB", str(f))
    assert dl.ensure_geoip_mmdb() == f


@pytest.mark.unit
def test_env_override_missing_raises(tmp_path, monkeypatch):
    monkeypatch.setenv("STEALTHFOX_GEOIP_MMDB", str(tmp_path / "nope.mmdb"))
    with pytest.raises(RuntimeError):
        dl.ensure_geoip_mmdb()


# ──────────────────────────────────────────────────────────────────────
#  freshness window
# ──────────────────────────────────────────────────────────────────────
@pytest.mark.unit
def test_fresh_cache_no_network(cache, monkeypatch):
    f = _make_cached(cache, "2026.06.03")
    _set_marker_age(cache, 0)  # just checked

    def boom():
        raise AssertionError("latest-tag API must NOT be called within the window")

    monkeypatch.setattr(dl, "_latest_geoip_tag", boom)
    assert dl.ensure_geoip_mmdb(max_age_days=7) == f


@pytest.mark.unit
def test_stale_same_tag_no_download(cache, monkeypatch):
    f = _make_cached(cache, "2026.06.03")
    _set_marker_age(cache, 30)  # stale → will re-check
    monkeypatch.setattr(dl, "_latest_geoip_tag", lambda: "2026.06.03")
    # real _download_geoip_tag runs but target exists, so no actual download:
    monkeypatch.setattr(dl, "_download_file", lambda *a, **k: (_ for _ in ()).throw(
        AssertionError("must not download when tag already cached")))
    assert dl.ensure_geoip_mmdb(max_age_days=7) == f


@pytest.mark.unit
def test_stale_new_tag_downloads_and_prunes(cache, monkeypatch):
    old = _make_cached(cache, "2026.06.03")
    _set_marker_age(cache, 30)
    monkeypatch.setattr(dl, "_latest_geoip_tag", lambda: "2026.06.10")

    def fake_download(tag):
        return _make_cached(cache, tag)  # simulate fetch+extract of the new tag

    monkeypatch.setattr(dl, "_download_geoip_tag", fake_download)
    got = dl.ensure_geoip_mmdb(max_age_days=7)
    assert got.parent.name == "2026.06.10"
    assert not old.parent.exists()  # old tag pruned
    assert got.exists()


# ──────────────────────────────────────────────────────────────────────
#  offline resilience
# ──────────────────────────────────────────────────────────────────────
@pytest.mark.unit
def test_api_down_with_cache_uses_cache(cache, monkeypatch):
    f = _make_cached(cache, "2026.06.03")
    _set_marker_age(cache, 30)

    def boom():
        raise OSError("offline")

    monkeypatch.setattr(dl, "_latest_geoip_tag", boom)
    assert dl.ensure_geoip_mmdb(max_age_days=7) == f  # stale cache reused, no raise


@pytest.mark.unit
def test_cold_cache_api_down_falls_back_to_pinned(cache, monkeypatch):
    # no cache at all + API unreachable → pinned GEOIP_MMDB_VERSION fallback.
    def boom():
        raise OSError("offline")

    monkeypatch.setattr(dl, "_latest_geoip_tag", boom)
    captured = {}

    def fake_download(tag):
        captured["tag"] = tag
        return _make_cached(cache, tag)

    monkeypatch.setattr(dl, "_download_geoip_tag", fake_download)
    got = dl.ensure_geoip_mmdb(max_age_days=7)
    assert captured["tag"] == dl.GEOIP_MMDB_VERSION
    assert got.exists()
