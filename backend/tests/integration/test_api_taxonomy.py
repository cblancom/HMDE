from __future__ import annotations

from hmde.models import TaxonomyNode


def _seed_taxonomy(seeded_session_factory) -> None:
    with seeded_session_factory() as session:
        session.merge(
            TaxonomyNode(
                taxonomy_version="api-0.2.0",
                code="metal",
                name="Metal",
                parent_code=None,
                assignable=False,
                display_order=1,
            )
        )
        session.merge(
            TaxonomyNode(
                taxonomy_version="api-0.2.0",
                code="heavy-metal",
                name="Heavy Metal",
                parent_code="metal",
                assignable=True,
                display_order=2,
            )
        )
        from hmde.models import TaxonomyVersion

        version = session.get(TaxonomyVersion, "api-0.2.0")
        if version is not None:
            version.is_current = True
        session.commit()


def test_taxonomy_and_parent_filter(
    api_client, seeded_session_factory, network_analysis_run
) -> None:
    _seed_taxonomy(seeded_session_factory)
    response = api_client.get("/api/v1/taxonomy")
    assert response.status_code == 200
    body = response.json()
    assert body["version"] == "api-0.2.0"
    assert {node["code"] for node in body["nodes"]} >= {"metal", "heavy-metal"}

    try:
        bands = api_client.get("/api/v1/bands", params={"subgenre": "metal"})
        assert bands.status_code == 200
        assert bands.json()["total"] > 0
        assert all(item["subgenre"] == "Heavy Metal" for item in bands.json()["items"])
    finally:
        with seeded_session_factory() as session:
            from hmde.models import TaxonomyVersion

            version = session.get(TaxonomyVersion, "api-0.2.0")
            if version is not None:
                version.is_current = False
            session.commit()
