from __future__ import annotations

import uuid

from hmde.etl.musicbrainz.traversal import (
    BandExtraction,
    CreditRecord,
    ExclusionRecord,
    ExternalIdRecord,
    ExtractedArtist,
    PlaceRelationshipRecord,
    RecordingRecord,
    ReleaseGroupRecord,
    ReleaseRecord,
    ReleaseRecordingRecord,
)

BAND = "11111111-1111-4111-8111-111111111111"
RELEASE_GROUP = "22222222-2222-4222-8222-222222222222"
EXCLUDED_GROUP = "33333333-3333-4333-8333-333333333333"
RELEASE = "44444444-4444-4444-8444-444444444444"
RECORDING_ONE = "55555555-5555-4555-8555-555555555555"
RECORDING_TWO = "66666666-6666-4666-8666-666666666666"
PRODUCER = "77777777-7777-4777-8777-777777777777"
ENGINEER = "88888888-8888-4888-8888-888888888888"
PLACE = "99999999-9999-4999-8999-999999999999"
RAW_ARTIST = uuid.UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
RAW_GROUP = uuid.UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
RAW_RELEASE = uuid.UUID("cccccccc-cccc-4ccc-8ccc-cccccccccccc")
RAW_RECORDING = uuid.UUID("dddddddd-dddd-4ddd-8ddd-dddddddddddd")


def sample_extraction() -> BandExtraction:
    return BandExtraction(
        band_mbid=BAND,
        subgenre="Heavy Metal",
        artist=ExtractedArtist(
            mbid=BAND,
            name="Test Band",
            sort_name="Test Band",
            type="Group",
            country="GB",
            disambiguation="",
            raw_response_id=RAW_ARTIST,
        ),
        external_ids=(
            ExternalIdRecord(
                entity_type="artist",
                entity_mbid=BAND,
                source="wikidata",
                external_id="Q12345",
                url="https://www.wikidata.org/wiki/Q12345",
                raw_response_id=RAW_ARTIST,
            ),
        ),
        release_groups=(
            ReleaseGroupRecord(
                mbid=RELEASE_GROUP,
                artist_mbid=BAND,
                title="Canonical Album",
                primary_type="Album",
                secondary_types=(),
                first_release_date="1985-05-01",
                date_precision="day",
                disambiguation="",
                tags=("heavy metal",),
                genres=("heavy metal",),
                raw_response_id=RAW_GROUP,
            ),
        ),
        releases=(
            ReleaseRecord(
                mbid=RELEASE,
                release_group_mbid=RELEASE_GROUP,
                title="Canonical Album",
                date="1985-05-01",
                country="GB",
                status="Official",
                disambiguation="",
                raw_response_id=RAW_RELEASE,
            ),
        ),
        recordings=(
            RecordingRecord(
                mbid=RECORDING_ONE,
                title="Track One",
                first_release_date="1985",
                disambiguation="",
                raw_response_id=RAW_RECORDING,
            ),
            RecordingRecord(
                mbid=RECORDING_TWO,
                title="Track Two",
                first_release_date="1985",
                disambiguation="",
                raw_response_id=RAW_RECORDING,
            ),
        ),
        release_recordings=(
            ReleaseRecordingRecord(
                release_mbid=RELEASE,
                recording_mbid=RECORDING_ONE,
                disc="1",
                position="1",
                track_number="1",
                raw_response_id=RAW_RELEASE,
            ),
            ReleaseRecordingRecord(
                release_mbid=RELEASE,
                recording_mbid=RECORDING_TWO,
                disc="1",
                position="2",
                track_number="2",
                raw_response_id=RAW_RELEASE,
            ),
        ),
        credits=(
            CreditRecord(
                scope="release_group",
                artist_mbid=PRODUCER,
                artist_name="Producer One",
                role="producer",
                attributes=("co",),
                release_group_mbid=RELEASE_GROUP,
                release_mbid=None,
                recording_mbid=None,
                credited_as=None,
                raw_response_id=RAW_GROUP,
            ),
            CreditRecord(
                scope="release",
                artist_mbid=PRODUCER,
                artist_name="Producer One",
                role="producer",
                attributes=(),
                release_group_mbid=RELEASE_GROUP,
                release_mbid=RELEASE,
                recording_mbid=None,
                credited_as=None,
                raw_response_id=RAW_RELEASE,
            ),
            CreditRecord(
                scope="recording",
                artist_mbid=ENGINEER,
                artist_name="Engineer One",
                role="engineer",
                attributes=(),
                release_group_mbid=None,
                release_mbid=None,
                recording_mbid=RECORDING_ONE,
                credited_as=None,
                raw_response_id=RAW_RECORDING,
            ),
        ),
        places=(
            PlaceRelationshipRecord(
                relation_type="recorded at",
                scope="release",
                place_mbid=PLACE,
                place_name="Studio One",
                release_group_mbid=RELEASE_GROUP,
                release_mbid=RELEASE,
                recording_mbid=None,
                raw_response_id=RAW_RELEASE,
            ),
        ),
        exclusions=(
            ExclusionRecord(
                release_group_mbid=EXCLUDED_GROUP,
                title="Live Collection",
                primary_type="Album",
                secondary_types=("Live",),
                first_release_date="1990",
                reason="secondary_type",
                raw_response_id=RAW_GROUP,
            ),
        ),
    )
