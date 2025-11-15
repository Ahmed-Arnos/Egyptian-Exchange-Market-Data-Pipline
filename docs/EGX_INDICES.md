EGX Indices — categories and notes
=================================

This document describes the EGX indices you mentioned and how we should treat them in the pipeline.

EGX30
------
- Description: The EGX30 is the headline blue‑chip index composed of the 30 most liquid and highly capitalized stocks listed on the Egyptian Exchange. Use EGX30 for large-cap benchmarking and market-leader analytics.

EGX70
------
- Description: EGX70 is a broader index made of mid‑ and small‑cap companies (70 constituents). It complements EGX30 to give coverage beyond the largest firms.

EGX100
-------
- Description: EGX100 is typically the combined universe of EGX30 + EGX70 (i.e., the top 100 by the exchange's selection criteria). It's an easy way to analyze the wider listed market while keeping reasonably sized universes.

EGX Sharia
----------
- Description: A Sharia‑compliant index composed of companies screened and selected to meet Islamic finance criteria. Useful for Islamic investment universe analyses.

How we will use these in the pipeline
-------------------------------------
- Store each index membership as a small CSV under `data/indices/<index>.csv` (symbol, name, weight, as_of_date).
- Keep a provenance field (source URL, scraped_at, or provider) and a small metadata JSON for refresh cadence.
- Build dbt sources/models to join trades/ticks to index membership (flag rows with egx30 boolean, etc.).

Next steps to populate members
-----------------------------
1. Scrape EGX official pages for index constituents and weights (or use a commercial API if available).
2. Store the CSVs in `data/indices/` and check them into the repo for small reference sets, or better: land them in Bronze storage and read from there for production.
3. Add a small extractor (script) that refreshes these lists on a schedule and records provenance.

Notes and caveats
----------------
- The exact constituents and definition may change over time; use an as_of_date for each CSV row and keep historical snapshots.
- Confirm the precise EGX pages and selectors before scraping; some indices are published in PDFs or via dynamic JS pages.
