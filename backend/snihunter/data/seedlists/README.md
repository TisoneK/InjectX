# Bundled SNI seed lists

Per-ISP starter lists of **candidate** SNI hostnames. They are *seed fuel* for
the SNI Host Hunter — a starting set to probe (`sni scan`) and to expand from
via Certificate Transparency discovery (`sni find <domain>`). A hostname being
in a seed list does **not** mean it currently works as a zero-rated bug host;
that is exactly what a scan verifies.

## Format

`.txt` — one hostname per line; `#` starts a comment; blank lines ignored.
The loader also accepts `.csv` (a `domain`/`hostname` column, optional
`cloudflare` column) and `.json` (array of strings or `{domain, cloudflare}`
objects) — see `../../sources/seedlist.py`.

## Provenance

Curated from **public** zero-rating documentation (Free Basics / internet.org
domains, operator self-care portals, zero-rated education portals) catalogued
in `.context/memory/features/sni-host-hunter.md` §3.4 and §11.5. These are
public hostnames — no secrets, no credentials (ADR-8).

## Responsible use

Probing public hosts is legitimate research and verification. Using a working
zero-rated host to avoid paying for data you would otherwise consume may
violate your ISP's terms of service in your jurisdiction — that decision, and
its consequences, are yours. See the project README's "Responsible Use"
section.

## Adding your own

Drop a new `<isp>-<cc>.txt` here (e.g. `mtn-za.txt`) and it appears in
`sni seedlists` automatically. Keep it to public hostnames only.
