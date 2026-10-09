# Claims register

`claims.csv` lists every number and dated fact in the paper with the source it rests on, the date the
source was read, and an archived copy, so that any reader can check a claim without trusting the
author. A fast market changes its pages: press releases are edited, postings expire, blog posts move.

| Column | Meaning |
|---|---|
| claim_id | Stable identifier (C001, C002, ...); never reused |
| section | Section of the paper where the claim appears |
| claim | The claim as printed |
| source | The reference as cited in the paper |
| url | Where the source was read |
| accessed | Date it was read (YYYY-MM-DD) |
| archive_url | A dated copy in the Internet Archive (filled by `tools/archive_urls.py`) |
| quote_or_locator | Page, table or the exact words that carry the number |
| status | `verified` (read in the primary source), `secondary` (through a report of it), `licensed` (read in a licensed copy, as for some analyst reports) |
| note | Anything a checker needs: rounding, currency, which edition |

## Keeping it alive

- `python3 tools/archive_urls.py sources/claims.csv` saves a copy of every source that has none yet.
- `.github/workflows/archive-sources.yml` runs the same command on the first day of each month and
  commits the new links, so the register keeps itself current without anyone remembering.
- Found a claim that no longer matches its source? Open an issue with the `claim_id`.
