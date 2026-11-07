# Data source evaluation

- **Status:** Evaluation v0.1; pending spike and legal review
- **Version:** 0.1
- **Date:** 2026-11-04
- **Stage:** E0

This document evaluates candidate sources before implementing ingestion. It is not legal advice. Terms of use may change and must be reviewed before publishing the product.

## 1. Decision summary

| Source | Role | Decision |
|---|---|---|
| MusicBrainz | Entities, MBID, albums, editions, recordings, relationships and credits | **Primary source; validated by the E0 spike** |
| Wikidata | External identifiers and links between entities | **Complementary for IDs** |
| Wikipedia | Historical context and credits when MusicBrainz is insufficient | **Future complementary source**, subject to CC BY-SA |
| Discogs | Additional credits | **Deferred**; incompatible with a historical snapshot under its terms |
| Encyclopaedia Metallum | Metal-specific data | **Excluded** until review and authorization |

## 2. Evaluation criteria

| Criterion | Question |
|---|---|
| Coverage | Does it contain the artists, albums and credits we need? |
| Structure | Does it offer stable entities and identifiers, or only text? |
| License | Does it allow storing, transforming and displaying the data? |
| Access | Does it have an API, clear limits and stable terms? |
| Stability | Do identifiers and the schema change frequently? |
| Traceability | Can we record URL, date, version and license? |
| Effort | How much work does extraction and normalization require? |
| Risk | What legal, technical or maintenance risk does it introduce? |

## 3. Comparison matrix

| Dimension | MusicBrainz | Wikidata | Wikipedia | Discogs | Metallum |
|---|---|---|---|---|---|
| Music entities | High | Medium | Medium | High | High |
| MBID / stable IDs | Yes (MBID) | Yes (QID) | No | Yes (own IDs) | Own IDs |
| Production credits | Medium, variable | Low | Low/extraction | High | High |
| Release-group / editions | Yes | Partial | No | Master/release | No |
| Core license | CC0 (core) | CC0 (structured) | CC BY-SA 4.0 | CC0 + restricted data | Not verified |
| Official API | Yes | Yes | Yes (MediaWiki) | Yes | No |
| Access limit | 1 req/s | Wikimedia policies | Wikimedia policies | 60/min authenticated | Not applicable |
| Historical snapshot use | Yes | Yes | Yes, with attribution | Restricted | No |
| Normalization effort | Medium | Low for IDs | High | Medium | High |

## 4. MusicBrainz

### Role

Primary source for:

- Artists and groups.
- Release-groups and releases.
- Relationships between artists, releases, places and others.
- Production credits when documented.
- MBID as the canonical key.

### License

The database is split into two components:

- **Core data:** CC0. Free use, no restrictions.
- **Supplementary data:** CC BY-NC-SA 3.0, with attribution and share-alike.
- **Live Data Feed:** CC BY-NC-SA 3.0.
- **Documentation:** CC BY-NC-SA 3.0.
- **Cover art:** not part of the database; served by the Cover Art Archive under its own licenses.

Do not assume that all content is CC0. Each record must preserve its applicable license and provenance. The MVP prioritizes core data and avoids supplementary content that complicates redistribution.

### API and limits

- REST API v2, XML or JSON responses.
- Root: `https://musicbrainz.org/ws/2/`.
- **Maximum one request per second.** Exceeding the limit may result in an IP block.
- **Meaningful and mandatory User-Agent.**
- Free non-commercial use; commercial use requires contacting MetaBrainz.
- Linked entities in a lookup are limited (25 by default); browse with pagination is used for the rest.
- Browse supports `limit` up to 100 and `offset`; for releases the effective limit may be lower because of track count.
- The API may change; it must be versioned and monitored.

### Coverage and risks

- Production credit coverage is uneven. Some albums have complete credits; others have none.
- Roles may appear as free text or as relationship types; a mapping is required.
- Genre tags are collaborative and noisy; they are not an objective taxonomy.
- Dates may have year, month or day precision; they may also be missing.
- Artists may have aliases, name changes and merges.
- Release-groups and releases are not always complete or correctly linked.
- The absence of a credit does not prove absence of participation.

### Decision

Use MusicBrainz as the MVP's primary source. Measure coverage before expanding scope. For large volumes, evaluate the official data dumps instead of relying only on the API; dumps also require license and storage management.

## 5. Wikidata

### Role

- External identifiers (QID).
- Links between entities from different sources.
- Occasional metadata when backed by references.

It is not used as the primary source of credits: production music coverage is limited and heterogeneous.

### License

- Structured data (main, Property, Lexeme and EntitySchema namespaces): CC0.
- Text in other pages: CC BY-SA 4.0.

### Access

- Wikidata API and Query Service.
- Identifiable User-Agent.
- Serial, moderate requests.
- Avoid expensive SPARQL queries in the MVP; use the API for specific IDs.

### Decision

Use Wikidata as a complementary identifier source. Record QID, retrieval date and provenance. Do not assume that a QID and an MBID are the same entity without an explicit relationship.

## 6. Wikipedia

### Role

- Historical and biographical context.
- Credits that do not appear in MusicBrainz, only if primary-source coverage is insufficient.
- Links to discographies and references.

### License

- Text: CC BY-SA 4.0 and GFDL.
- Media: variable licenses; images are not used in the MVP.
- Reuse requires attribution and, where applicable, share-alike.

### Access

- MediaWiki API, not HTML scraping by default.
- User-Agent with contact information.
- Serial requests; do not parallelize.
- Use `maxlag` for non-interactive tasks and gzip compression.
- Respect Wikimedia limits and policies.

### Risks

- Extracting credits from text or tables is fragile.
- The share-alike license may affect redistribution of derived text.
- Information may be incomplete or outdated.
- A dedicated parser and maintenance are required.

### Decision

Do not use Wikipedia in the MVP unless the spike shows that MusicBrainz is insufficient. If it is used, extract only factual data with references and keep the original text out of the product, or strictly comply with CC BY-SA attribution.

## 7. Discogs

### Potential role

Very rich production credits, especially for physical editions, and a master/release structure.

### License and terms

- Part of the content is **CC0 Data** (titles, dates, formats, tracklists, credits, versions, artist names, labels, etc.).
- Another part is **Restricted Data** (user data, marketplace, images), with a limited, non-commercial license.
- API use is subject to the API Terms of Use.
- Limits: 60 requests/minute authenticated; 25/minute unauthenticated. Unauthenticated access is being retired.
- The API requires an identifiable User-Agent.
- The terms state that content more than six hours older than Discogs may not be displayed, and it may not be stored longer than necessary to provide the service.
- Attribution notices and a link to Discogs are required.

### Why it is deferred

The freshness requirement and the prohibition on storing content longer than necessary are incompatible with a **historical snapshot** and with reproducible long-term analyses. Separating CC0 from Restricted Data and complying with attribution also adds legal and product complexity.

### Decision

Do not use Discogs in the MVP. If it is incorporated later, do so with legal review, probably only for CC0 data and with a design that respects the terms. Scraping will not be used.

## 8. Encyclopaedia Metallum

### Potential role

Metal-specific data, discographies and credits.

### Access

- No official public API was found.
- The terms page returned HTTP 403 to an automated request.
- Automated access is not clearly authorized.
- Forum posts confirm that no official API exists.

### Decision

Excluded from the MVP. No scraping will be performed. It will only be reconsidered if explicit authorization or an official data-access path exists that respects the site's terms.

## 9. Provenance model

Every ingested record must preserve:

| Field | Description |
|---|---|
| `source` | `musicbrainz`, `wikidata`, `wikipedia`, etc. |
| `source_entity_type` | Entity type in the source |
| `external_id` | MBID, QID or other identifier |
| `source_url` | Exact consulted URL |
| `fetched_at` | Retrieval date and time |
| `payload_hash` | Content hash to detect changes |
| `raw_location` | Path or reference to the raw payload |
| `http_status` | Response code |
| `license` | License applicable to the record |
| `api_version` | API or schema version |
| `ingest_run_id` | Run that produced the record |

Raw data is preserved so it can be reprocessed without calling the source again. It is never edited by hand.

## 10. Feasibility spike (E0)

> The E0 spike evaluated 1980–2000 only. Coverage for the planned 1960–2026 corpus is not yet measured.

### Objective

Measure whether MusicBrainz contains enough information to answer the MVP questions before investing in the full pipeline.

### Sample

- 28 bands (4 per subgenre).
- Stratified by subgenre, decade and country.
- With a verifiable MBID.
- Includes difficult cases: bands with many albums, lineup changes, aliases, multiple editions and live or compilation albums.

### Data to collect per band

- Release-groups of type album between 1980 and 2000.
- Associated releases and dates.
- Credits for producer, co-producer, executive producer, engineer, mix and mastering.
- Associated places/studios.
- Tags and genres.
- Wikidata identifiers.
- Issues: ambiguous roles, duplicate data, incomplete dates, unresolved artists.

### Metrics

| Metric | Use |
|---|---|
| Albums per band | Volume and dispersion |
| % of albums with at least one producer/co-producer | Core viability |
| % with engineer, mix or mastering | Extended role scope |
| % with studio/place | Studio analysis viability |
| Date precision distribution | Temporal analysis quality |
| Distinct producers and credits per album | Network density |
| % of entities with a QID | Wikidata coverage |
| Duplicates and conflicts found | Identity effort |
| Requests and total time | Ingestion cost |
| Unmapped roles | Normalization work |

### Provisional decision criteria

| Result | Decision |
|---|---|
| ≥ 60% of albums with producer/co-producer | MusicBrainz viable as primary source |
| 30–60% | Viable with limitations; evaluate Wikipedia as a complement or adjust scope |
| < 30% | Do not build the MVP on this coverage; rethink sources or scope |
| < 30% of albums with a studio | Studios will not be a central MVP axis |
| < 80% of dates with year or better precision | Temporal analysis will be limited and must be declared |

The thresholds are working hypotheses, not truths. They were evaluated against the spike results.

### Results (2026-11-05)

| Metric | Result |
|---|---:|
| Bands analyzed | 28 |
| Album candidates | 206 |
| Producer/co-producer coverage | 86.4% |
| Producer/co-producer coverage, excluding low-confidence albums | 89.0% |
| Co-producer coverage | 9.7% |
| Executive producer coverage | 10.2% |
| Extended credit coverage | 83.0% |
| Studio/place coverage | 80.1% |
| Bands with Wikidata QID | 100% |
| Dates with year or better precision | 100% |
| Albums whose producer credit exists only at recording level | 105 of 178 covered albums (59.0%) |
| Low-confidence album candidates | 6 |
| Initial full fetch | 409 requests, 859.5 seconds |

Coverage varies by subgenre: Heavy Metal 97.7% producer coverage, Thrash Metal 93.8%, Death Metal 88.0%, Power Metal 93.3%, Progressive Metal 88.9%, Doom Metal 72.0% and Black Metal 58.3%. This is a material limitation for cross-subgenre comparisons.

The complete report is in [spike-report.md](spike-report.md). The main finding is that production credits are frequently attached to recordings, not releases; the credit model must support recording-level scope and album-level aggregation. See [ADR-0007](../01-architecture/adr/ADR-0007-credit-scope-and-recording-level-aggregation.md).

### Outputs

- Report with tables and examples.
- List of queries and URLs used.
- List of issues and pending decisions.
- Scope recommendation for SPEC-002 and SPEC-003.
- Confirmation or revision of ADR-0002 and ADR-0004.
- New credit-scope decision in ADR-0007.

## 11. Attribution and licenses in the product

- Attribution page with links to MusicBrainz, Wikidata and, if applicable, Wikipedia.
- Statement of the license for each dataset.
- Snapshot date.
- Link to the original entry when the license requires it.
- No redistribution of images or restricted data.
- Derived data must declare its provenance and limitations.

## 12. Legal note

This evaluation is technical, not legal. Before publishing the product:

- Review the current terms of each source.
- Confirm which data is CC0 and which has restrictions.
- Verify attribution and share-alike obligations.
- Document the final decision in an ADR or in this document.

## 13. References

- [MusicBrainz API](https://musicbrainz.org/doc/MusicBrainz_API), accessed 2026-11-04.
- [MusicBrainz Data License](https://musicbrainz.org/doc/About/Data_License), accessed 2026-11-04.
- [Wikidata Licensing](https://www.wikidata.org/wiki/Wikidata:Licensing), accessed 2026-11-04.
- [MediaWiki API Etiquette](https://www.mediawiki.org/wiki/API:Etiquette), accessed 2026-11-04.
- [Wikimedia Terms of Use](https://foundation.wikimedia.org/wiki/Policy:Terms_of_Use), accessed 2026-11-04.
- [Discogs API Documentation](https://www.discogs.com/developers), accessed 2026-11-04.
- [Discogs API Terms of Use](https://support.discogs.com/hc/articles/360009334593-API-Terms-of-Use), accessed 2026-11-04.
- [Encyclopaedia Metallum](https://www.metal-archives.com/), accessed 2026-11-04; terms not verifiable due to HTTP 403.
