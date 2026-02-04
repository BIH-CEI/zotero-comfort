---
name: ceir-publication-sync
description: "CEIR team publication integration: fetch from Charité Forschungsdatenbank API, PubMed, and ORCID, deduplicate, filter by affiliation, and sync to Zotero group library. Use when: (1) Fetching team publications from forschungsdatenbank.charite.de, (2) Syncing publications to the CEI_Publications Zotero library (ID 5767153), (3) Deduplicating publications across team members, (4) Discovering API tokens for new team members, (5) Filtering out pre-affiliation clinical papers, (6) Enriching publication metadata from PubMed or ORCID."
---

# CEIR Publication Sync

## Sync Workflow

1. Fetch publications from Charité API for all team members with tokens
2. Enrich with PubMed metadata where DOI/abstract missing
3. Deduplicate by DOI (primary) then normalized title (fallback)
4. Filter out pre-affiliation papers (see filtering rules in references)
5. Compare against existing Zotero items (match DOI or title)
6. Create missing items in Zotero, assign to year collections

## Charité Forschungsdatenbank API

Primary source. No browser needed — call REST endpoints directly.

```
BASE = https://forschungsdatenbank.charite.de/experts/expert

GET /publications/pub_per_exp/{token}/FPS   → publications
GET /exp/co_per_exp/{token}/FPS             → co-authors
GET /exp/info_per_exp/{token}               → profile info
```

Use 0.3s delay between requests. Returns: title, authors, year, DOI, journal, volume/issue/pages, abstract, PubMed/PMC links, open access status, internal co-authors with tokens.

**Implementation:** `src/zotero_comfort/external/charite.py` — `ChariteClient` class, `CEIR_TEAM` roster.

## Other Sources

- **PubMed** (`src/zotero_comfort/external/pubmed.py`): Enrich metadata, verify DOIs, get PMIDs
- **ORCID** (not yet implemented): 5 members have ORCID only — see [references/roster.md](references/roster.md)
- **arXiv** (`src/zotero_comfort/external/arxiv.py`): Low priority, most team output is journals/conferences
- **BIH website**: Just links to Forschungsdatenbank profiles, no publications inline. Skip.

## Deduplication

Publications appear under multiple members. Deduplicate with:
1. DOI (case-insensitive, stripped) — strongest
2. Normalized title (lowercase, non-alnum removed, first 50 chars) — fallback

First occurrence wins. See `ChariteClient._deduplicate()`.

## Zotero Sync Target

- **Library:** CEI_Publications (ID 5767153), key at `~/.secret/ceir-os-zotero-token` (format: `library_id:api_key`)
- **Collections:** Year-based (2018–2026)
- **Item mapping:** See `workflows_external.py` → `_paper_to_zotero_item()`
- **Blocker (2026-02-04):** API key is read-only. Need write access.

## Reference Files

- **[references/roster.md](references/roster.md)** — Full team roster with tokens, ORCIDs, and coverage gaps. Read when discovering tokens or checking member coverage.
- **[references/filtering.md](references/filtering.md)** — Inclusion/exclusion rules, known false positives per member, keyword heuristic. Read when deciding which publications to include or exclude.
