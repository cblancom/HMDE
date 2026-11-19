# Analysis corpus v0.3.0

- **Status:** Active
- **Date:** 2026-11-19
- **Stage:** E13 — E6/E7 analysis
- **Dataset:** `mb-20261119T004940Z-9d5e75fdc1b9`
- **Normalization run:** `ed8e7e12-c181-4041-ba39-42b2bf655453`
- **Quality run:** `288b11ac-9a90-4b4f-bf58-fdd50e1a51ad`
- **EDA report:** `eda-bd2ef42a54786c67`
- **Network run:** `613a597e-242c-44ab-add3-a95381d23ec3` (`net-78a54051ff047f86`)
- **Taxonomy:** 0.2.0
- **Metric catalogue:** 0.1.0

## 1. Corpus coverage

| Entity | E3 canonical dataset | E6/E7 observation |
|---|---:|---:|
| Bands | 509 | 509 |
| Release groups | 4,826 | 4,827 |
| Releases | 31,629 | 31,630 |
| Recordings | 82,228 | 82,233 |
| Credits | 106,981 | 110,071 |

The difference is a known shared-table limitation: the canonical PostgreSQL tables retain one legacy v0.2 release group, one release, five recordings and 3,090 legacy credits outside the v0.3 canonical dataset. E6/E7 scope bands through active dataset membership; the residual rows are documented rather than silently removed. The v0.3 corpus itself remains the E3 dataset above.

Coverage denominators are recorded in the EDA report for every metric. The batch distribution is `42 + 15 + 151 + 151 + 150 = 509`; the final leaf distribution and country distribution are recorded in the EDA report and the seed-list document.

## 2. E6 exploratory analysis

- 927 metric rows, including coverage, temporal, taxonomy, role, country, batch and producer-concentration metrics.
- 900 album classifications remain in review; 0 albums are quarantined.
- 1,089 quality findings are medium/advisory; 0 are blocking.
- Producer concentration is descriptive and uses the documented producer/co-producer credit scope.
- The v0.2.0 EDA report remains `eda-1267fdcced62b7da` with 354 metric rows.

## 3. E7 producer network

| Layer | Nodes | Edges | Components |
|---|---:|---:|---:|
| Producer–album | 3,719 | 4,217 | 300 |
| Producer–band/artist | 1,570 | 1,700 | 111 |

- Communities: 325 Louvain communities.
- Support: full 1,224; partial 3,060; unknown 0.
- The v0.2.0 snapshot remains `net-a0b7c1f41ac5c92d`: producer–album 968 nodes / 1,134 edges / 67 components; producer–band 398 / 426 / 13; 78 communities.

Shared credits do not demonstrate affinity, influence or listener preference. Missing credits are not negative evidence.

## 4. Limitations

- The shared canonical tables retain the legacy rows described in section 1; corpus counts in E6/E7 are therefore one album/release, five recordings and 3,090 credits above the E3 canonical dataset.
- 900 album classifications are in review because tags are broad or absent; those albums use the documented band-seed fallback.
- The network is a descriptive producer–credit graph, not a causal or influence model.
- Coverage and concentration results apply to this purposive sample, not to the entire heavy metal scene.

## 5. Reproduction

The exact commands and run IDs are recorded in [`specs/016-corpus-expansion/tasks.md`](../../specs/016-corpus-expansion/tasks.md), T-008. The reports are generated under `data/analysis/` and `data/network/` and are ignored by Git.

## 6. Performance review

The E13 performance probe (`frontend/test-results/performance-performance-probe-chromium/performance-report.json`, ignored by Git) measured the v0.3.0 network on 2026-11-19:

- API p95: bands list 13 ms, albums list 73 ms, producers list 239 ms, band detail 12 ms, album detail 9 ms, producer detail 202 ms, search 16 ms, ego graph 181 ms, overview bands 411 ms, overview albums 486 ms.
- Browser: `/graph` navigation p95 2.96 s; view-switch acknowledgement p95 2.37 s (1 s target exception); full view settle p95 2.63 s; panel toggle 686 ms; ego navigation 681 ms.
- The overview keeps the 1,000-node/2,000-edge cap with explicit truncation: albums 1,000 nodes / 810 edges, bands 1,000 nodes / 1,125 edges.
- CoSE completed in 10.1 s; fCoSE completed in 2.0 s.
- The 26-test Playwright suite and nine axe scans passed.

The view-switch acknowledgement is the only performance exception. The full interaction settles within the 5-second target, so the cap and current UI remain.
