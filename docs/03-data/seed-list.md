# MVP seed list

- **Status:** Approved v0.1.0
- **Date:** 2026-11-05
- **Stage:** E0
- **Machine-readable source:** [`data/seed-list.json`](../../data/seed-list.json)
- **Criteria:** [`docs/00-vision/scope.md#9-seed-list`](../00-vision/scope.md#9-seed-list)

## 1. Purpose

This is the purposive, stratified list of 42 bands used to build the MVP dataset. It is not a ranking and is not statistically representative of the entire heavy metal scene. It is designed to cover the seven MVP subgenres, the 1980s and 1990s, and multiple countries while remaining small enough to ingest and validate.

The JSON file is the machine-readable source of truth for ingestion. This document records the selection rationale, verification and limitations.

## 2. Composition

| Dimension | Distribution |
|---|---|
| Total bands | 42 |
| Per subgenre | 6 each in Heavy, Thrash, Death, Black, Power, Doom and Progressive Metal |
| Period | Studio albums released between 1980 and 2000 |
| Countries | GB 8, US 15, SE 7, DE 5, NO 4, BR 1, FI 1, GR 1 |
| Verification | 42 unique MBIDs; 100% with Wikidata QID; 100% with at least one studio album in the period |

Every band has at least three studio albums in the period according to MusicBrainz. The minimum is three (HammerFall, Mayhem and Pain of Salvation); the maximum is twelve (Iron Maiden and Motörhead).

## 3. Selection method

The list is a **purposive stratified sample**, not a random sample. The selection frame combines:

- MusicBrainz artist records, MBIDs and release-group metadata.
- MusicBrainz genre tags and the curated subgenre taxonomy in the scope.
- Canonical discographies and documented relevance within each subgenre.
- Deliberate coverage of the 1980s and 1990s, multiple countries and difficult cases (long discographies, lineup changes, aliases, many editions and short names).

The list started with a 28-band feasibility sample and added two bands per subgenre to reach six per subgenre. The final list is versioned; additions or removals require a version bump and a note in this document.

## 4. Inclusion and exclusion

Included when:

1. The artist is primarily associated with one of the seven MVP subgenres.
2. At least one studio album was first released between 1980 and 2000.
3. A stable MusicBrainz MBID exists and was verified on 2026-11-05.
4. The band adds coverage by subgenre, decade or country.

Excluded when:

- No studio album exists in the period.
- The artist is not associated with heavy metal or its subgenres.
- The entity is a duplicate or cannot be resolved deterministically.
- The artist has only demos, live releases or compilations in the period.

## 5. Seed list

| # | Band | Subgenre | Country | MBID | Studio albums 1980–2000 |
|---:|---|---|---|---|---:|
| 1 | Iron Maiden | Heavy Metal | GB | `ca891d65-d9b0-4258-89f7-e6ba29d83767` | 12 |
| 2 | Judas Priest | Heavy Metal | GB | `6b335658-22c8-485d-93de-0bc29a1d0349` | 8 |
| 3 | Motörhead | Heavy Metal | GB | `57961a97-3796-4bf7-9f02-a985a8979ae9` | 12 |
| 4 | Black Sabbath | Heavy Metal | GB | `5182c1d9-c7d2-4dad-afa0-ccfeada921a8` | 11 |
| 5 | Dio | Heavy Metal | US | `c55193fb-f5d2-4839-a263-4c044fca1456` | 8 |
| 6 | Accept | Heavy Metal | DE | `41f4d85a-0bd7-4602-a3e3-8c47f36efb0a` | 10 |
| 7 | Metallica | Thrash Metal | US | `65f4f0c5-ef9e-490c-aee3-909e7ae6b2ab` | 7 |
| 8 | Slayer | Thrash Metal | US | `bdacc37b-8633-4bf8-9dd5-4662ee651aec` | 8 |
| 9 | Megadeth | Thrash Metal | US | `a9044915-8be3-4c7e-b11f-9e2d2ea0a91e` | 9 |
| 10 | Sepultura | Thrash Metal | BR | `1d93c839-22e7-4f76-ad84-d27039efc048` | 8 |
| 11 | Testament | Thrash Metal | US | `05106775-5d45-4131-aecc-1177f813ba11` | 8 |
| 12 | Kreator | Thrash Metal | DE | `39822e8d-f24e-4f07-b51b-28b22e59fbdb` | 9 |
| 13 | Death | Death Metal | US | `dbb3b771-ae77-4381-b61c-758b5b7898ec` | 7 |
| 14 | Cannibal Corpse | Death Metal | US | `af8e4cc5-ef54-458d-a194-7b210acf638f` | 7 |
| 15 | Morbid Angel | Death Metal | US | `4355a36d-805e-478d-8589-64f0292724b2` | 7 |
| 16 | At the Gates | Death Metal | SE | `35f92c4a-69d0-4ed1-ab9e-05259db89d14` | 4 |
| 17 | Obituary | Death Metal | US | `2e8ac3ed-2a89-4377-ba80-790106aba554` | 5 |
| 18 | Entombed | Death Metal | SE | `61b99cc4-06cd-4ad5-9bac-950b2daef9cc` | 6 |
| 19 | Bathory | Black Metal | SE | `d292b4cd-37bd-4a88-a823-8710f273cc31` | 9 |
| 20 | Mayhem | Black Metal | NO | `c5f9e699-7b0d-4030-86dd-7acc8250d147` | 3 |
| 21 | Emperor | Black Metal | NO | `d9951785-7906-4daf-9a60-21753bf64aa9` | 4 |
| 22 | Darkthrone | Black Metal | NO | `af8fd97c-db72-4e30-b2aa-30ebd0c4f1a0` | 8 |
| 23 | Immortal | Black Metal | NO | `b863cf80-19c6-4a87-8e42-6cff7ac8f18f` | 7 |
| 24 | Rotting Christ | Black Metal | GR | `2d576cfe-7669-4af0-a66a-86c8362f47c5` | 6 |
| 25 | Helloween | Power Metal | DE | `765774a0-2060-469b-8b7d-612eea48579b` | 10 |
| 26 | Blind Guardian | Power Metal | DE | `7fa7fc04-1011-4876-8095-ecd232edea87` | 6 |
| 27 | Stratovarius | Power Metal | FI | `c3d6fdd5-67c5-453e-87e3-d17a00a52879` | 8 |
| 28 | Gamma Ray | Power Metal | DE | `8766cdd6-066c-4b14-ba53-c7958e613bad` | 6 |
| 29 | Iced Earth | Power Metal | US | `8a0e10a9-80c7-40e0-bf5b-89f1d57f9537` | 5 |
| 30 | HammerFall | Power Metal | SE | `abf5f674-dbad-4219-b3ad-dbd6fb163c8e` | 3 |
| 31 | Candlemass | Doom Metal | SE | `7dba6614-d0bd-4950-8b7b-841b31c413c2` | 7 |
| 32 | Paradise Lost | Doom Metal | GB | `10bf95b6-30e3-44f1-817f-45762cdc0de0` | 7 |
| 33 | My Dying Bride | Doom Metal | GB | `2f04ad1f-9f97-41d0-a09c-59c40dfe9cd1` | 6 |
| 34 | Cathedral | Doom Metal | GB | `e659c09d-8ec1-43d8-ab3f-72630b926157` | 5 |
| 35 | Trouble | Doom Metal | US | `2bfd6269-90a6-405e-8ce2-db6ad23a489c` | 6 |
| 36 | Anathema | Doom Metal | GB | `20aa23e3-3532-42ca-acf6-e8c2e9df2688` | 5 |
| 37 | Dream Theater | Progressive Metal | US | `28503ab7-8bf2-4666-a7bd-2644bfc7cb1d` | 5 |
| 38 | Fates Warning | Progressive Metal | US | `17fbada3-6dac-42f3-8a6c-8c1c1484f730` | 9 |
| 39 | Queensrÿche | Progressive Metal | US | `deeea939-7f89-4762-b09f-79269cd70d3b` | 9 |
| 40 | Opeth | Progressive Metal | SE | `c14b4180-dc87-481e-b17a-64e4150f90f6` | 4 |
| 41 | Symphony X | Progressive Metal | US | `b669c53e-5a1f-4adc-80be-755e64e8115e` | 5 |
| 42 | Pain of Salvation | Progressive Metal | SE | `f7c65346-9631-4220-9188-5e90baae58d5` | 3 |

## 6. Known limitations

- The sample over-represents well-documented, canonical bands.
- Production-credit coverage was measured on the 28-band spike sample; the 14 added bands were verified for MBID and studio-album existence, not full credit coverage.
- Black Metal has lower production-credit coverage in the spike (58.3% producer coverage vs 97.7% for Heavy Metal). Cross-subgenre comparisons must report this.
- The list is not a measure of importance, quality or influence.
- MusicBrainz data changes over time; MBIDs and album counts reflect the 2026-11-05 verification.
- The list is intentionally small for the MVP; expansion to 200–500 bands is E13.

## 7. Change control

- The JSON version and this document's version move together.
- Additions or removals require a version bump, a rationale and a MusicBrainz verification.
- Do not silently replace a band or MBID during ingestion.
- Ingestion datasets must record the seed-list version used.
