from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import delete

from hmde.models import Artist, ArtistSubgenre, SourceRecord


def test_list_bands_returns_seed_dataset(api_client) -> None:
    response = api_client.get("/api/v1/bands")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 14
    assert body["limit"] == 20
    assert body["offset"] == 0
    assert len(body["items"]) == 14
    assert all(item["subgenre"] for item in body["items"])
    assert all(item["album_count"] >= 2 for item in body["items"])


def test_search_and_subgenre_filter(api_client) -> None:
    search_response = api_client.get("/api/v1/bands", params={"q": "maiden"})
    assert search_response.status_code == 200
    assert [item["name"] for item in search_response.json()["items"]] == ["Iron Maiden"]

    filter_response = api_client.get(
        "/api/v1/bands",
        params={"subgenre": "thrash-metal"},
    )
    assert filter_response.status_code == 200
    names = {item["name"] for item in filter_response.json()["items"]}
    assert names == {"Metallica", "Slayer"}


def test_list_pagination(api_client) -> None:
    first_page = api_client.get("/api/v1/bands", params={"limit": 2, "offset": 0})
    second_page = api_client.get("/api/v1/bands", params={"limit": 2, "offset": 2})

    assert first_page.status_code == 200
    assert second_page.status_code == 200
    assert first_page.json()["total"] == 14
    assert len(first_page.json()["items"]) == 2
    assert len(second_page.json()["items"]) == 2
    assert first_page.json()["items"] != second_page.json()["items"]


def test_invalid_pagination_returns_422(api_client) -> None:
    response = api_client.get("/api/v1/bands", params={"limit": 0})

    assert response.status_code == 422


def test_band_detail_returns_albums_and_credits(api_client) -> None:
    bands = api_client.get("/api/v1/bands", params={"q": "Iron Maiden"}).json()
    band_id = bands["items"][0]["id"]

    response = api_client.get(f"/api/v1/bands/{band_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Iron Maiden"
    assert body["subgenre"] == "Heavy Metal"
    assert len(body["albums"]) == 3
    assert body["albums"][0]["title"] == "Iron Maiden"
    assert body["albums"][0]["year"] == 1980
    assert any(
        credit["role"] in {"producer", "co-producer"}
        for album in body["albums"]
        for credit in album["credits"]
    )
    assert all(
        credit["supporting_recording_count"] <= credit["recording_count"]
        for album in body["albums"]
        for credit in album["credits"]
    )


def test_band_detail_unknown_id_returns_404(api_client) -> None:
    response = api_client.get("/api/v1/bands/00000000-0000-0000-0000-000000000000")

    assert response.status_code == 404
    assert response.json()["detail"] == "Band not found"


def test_band_graph_returns_producer_nodes_and_edges(api_client) -> None:
    bands = api_client.get("/api/v1/bands", params={"q": "Iron Maiden"}).json()
    band_id = bands["items"][0]["id"]

    response = api_client.get(f"/api/v1/bands/{band_id}/graph")

    assert response.status_code == 200
    body = response.json()
    node_types = {node["type"] for node in body["nodes"]}
    assert node_types == {"band", "producer"}
    assert body["nodes"][0] == {
        "id": band_id,
        "label": "Iron Maiden",
        "type": "band",
    }
    assert body["edges"]
    node_ids = {node["id"] for node in body["nodes"]}
    assert all(edge["source"] == band_id for edge in body["edges"])
    assert all(edge["target"] in node_ids for edge in body["edges"])
    assert all(edge["album_count"] >= 1 for edge in body["edges"])
    assert body["meta"]["fixture_version"] == "e2-v0.1.0"


def test_band_graph_unknown_id_returns_404(api_client) -> None:
    response = api_client.get("/api/v1/bands/00000000-0000-0000-0000-000000000000/graph")

    assert response.status_code == 404
    assert response.json()["detail"] == "Band not found"


def test_band_graph_without_credits_returns_band_node_only(
    api_client,
    seeded_session_factory,
) -> None:
    source_id = uuid.uuid4()
    artist_id = uuid.uuid4()

    with seeded_session_factory() as session:
        session.add(
            SourceRecord(
                id=source_id,
                source="test",
                source_entity_type="artist",
                external_id="no-credit-band",
                source_url="https://example.test/no-credit-band",
                fetched_at=datetime.now(UTC),
                license="test",
                payload_hash="test",
                fixture_version="test",
            )
        )
        session.commit()

    with seeded_session_factory() as session:
        session.add(
            Artist(
                id=artist_id,
                mbid=str(uuid.uuid4()),
                name="No Credit Test Band",
                sort_name="No Credit Test Band",
                type="group",
                country="XX",
                disambiguation="",
                source_record_id=source_id,
            )
        )
        session.add(
            ArtistSubgenre(
                artist_id=artist_id,
                subgenre_code="heavy-metal",
                is_primary=True,
                confidence=1.0,
                source_record_id=source_id,
            )
        )
        session.commit()

    try:
        response = api_client.get(f"/api/v1/bands/{artist_id}/graph")

        assert response.status_code == 200
        body = response.json()
        assert body["nodes"] == [
            {
                "id": str(artist_id),
                "label": "No Credit Test Band",
                "type": "band",
            }
        ]
        assert body["edges"] == []
    finally:
        with seeded_session_factory() as session:
            session.execute(delete(ArtistSubgenre).where(ArtistSubgenre.artist_id == artist_id))
            session.execute(delete(Artist).where(Artist.id == artist_id))
            session.execute(delete(SourceRecord).where(SourceRecord.id == source_id))
            session.commit()
