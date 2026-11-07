from __future__ import annotations

from pathlib import Path

import pytest

from hmde.etl.musicbrainz.raw_store import (
    RawPayloadCorruptionError,
    RawPayloadMissingError,
    build_request_key,
    hash_payload,
    read_raw_payload,
    write_raw_payload,
)


def test_request_key_is_deterministic_and_param_order_independent() -> None:
    first = build_request_key(
        "get",
        "https://musicbrainz.org/ws/2/artist/abc",
        {"inc": "url-rels", "fmt": "json"},
        "2",
    )
    second = build_request_key(
        "GET",
        "https://musicbrainz.org/ws/2/artist/abc",
        {"fmt": "json", "inc": "url-rels"},
        "2",
    )

    assert first == second


def test_request_key_changes_with_request_semantics() -> None:
    base = build_request_key(
        "GET",
        "https://musicbrainz.org/ws/2/artist/abc",
        {"fmt": "json"},
        "2",
    )

    assert base != build_request_key(
        "POST",
        "https://musicbrainz.org/ws/2/artist/abc",
        {"fmt": "json"},
        "2",
    )
    assert base != build_request_key(
        "GET",
        "https://musicbrainz.org/ws/2/artist/xyz",
        {"fmt": "json"},
        "2",
    )
    assert base != build_request_key(
        "GET",
        "https://musicbrainz.org/ws/2/artist/abc",
        {"fmt": "json"},
        "3",
    )


def test_write_raw_payload_is_content_addressed_and_idempotent(tmp_path: Path) -> None:
    payload = b'{"artist": "Iron Maiden"}'

    digest, relative_path = write_raw_payload(tmp_path, payload)
    second_digest, second_relative_path = write_raw_payload(tmp_path, payload)

    assert digest == hash_payload(payload)
    assert (digest, relative_path) == (second_digest, second_relative_path)
    assert (tmp_path / relative_path).read_bytes() == payload
    assert list(tmp_path.glob("*.tmp")) == []


def test_write_raw_payload_preserves_unrelated_files(tmp_path: Path) -> None:
    sentinel = tmp_path / "keep.txt"
    sentinel.write_text("keep", encoding="utf-8")

    write_raw_payload(tmp_path, b'{"x": 1}')

    assert sentinel.read_text(encoding="utf-8") == "keep"


def test_write_raw_payload_rejects_corrupt_existing_file(tmp_path: Path) -> None:
    payload = b'{"x": 1}'
    digest = hash_payload(payload)
    target = tmp_path / f"{digest}.json"
    target.write_bytes(b"tampered")

    with pytest.raises(RawPayloadCorruptionError):
        write_raw_payload(tmp_path, payload)

    assert target.read_bytes() == b"tampered"


def test_read_raw_payload_detects_missing_and_corrupt_files(tmp_path: Path) -> None:
    payload = b'{"x": 1}'
    digest, relative_path = write_raw_payload(tmp_path, payload)

    assert read_raw_payload(tmp_path, relative_path, digest) == payload

    (tmp_path / relative_path).unlink()
    with pytest.raises(RawPayloadMissingError):
        read_raw_payload(tmp_path, relative_path, digest)

    (tmp_path / relative_path).write_bytes(b"tampered")
    with pytest.raises(RawPayloadCorruptionError):
        read_raw_payload(tmp_path, relative_path, digest)
