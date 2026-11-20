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

The SPEC-019 performance probe (`frontend/test-results/performance-performance-probe-chromium/performance-report.json`, ignored by Git) measured the v0.3.0 full-corpus views on 2026-11-20:

- API p95: bands list 14 ms, albums list 57 ms, producers list 244 ms, band detail 10 ms, album detail 9 ms, producer detail 169 ms, search 12 ms, ego graph 156 ms, all bands 1,034 ms, default 500 albums 1,030 ms, all albums 1,196 ms.
- Browser: all bands 3.95 s; default 500 albums 4.27 s; explicit all albums 6.04 s; view-switch acknowledgement 1.43 s; full view switch settle 1.60 s; panel toggle 654 ms; ego navigation 851 ms.
- The overview producer control accepts a typed 1–1000 limit or All. The overview defaults to the static bipartite layout for both views. Force is an explicit opt-in. Selection is stable and does not restart the layout; isolated producers are hidden by default. The recorded browser timings use the pre-revision 1,944-node API view; the default canvas now has 1,401 visible nodes.
- All bands is 509 bands / 1,708 nodes / 1,700 edges. Default albums is 500 albums / 1,944 API nodes / 1,717 edges with 1,775 omitted; the canvas hides 543 out-of-subset producers, leaving 1,401 visible nodes. All albums is 2,275 graph albums / 3,719 nodes / 4,217 edges.
- CoSE did not complete within 30 s and fCoSE completed in 34.1 s when Force was selected; both remain documented finite-layout observations.

The all-albums view and view-switch acknowledgement are the measured exceptions. The all-bands and default-album views meet the five-second target. See the [QA report](../01-architecture/qa-report.md#14-spec-019-v030-full-corpus-performance-review).
