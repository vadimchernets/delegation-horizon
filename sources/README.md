# Claims register

`claims.csv` lists the numbers and quotations the paper rests on, with the source, the date the source was
read, an archived copy and the source's own words, so that a reader, or a checker from another model
family, can go from a sentence in the paper to its source without trusting the author. A fast market
changes its pages: press releases are edited, postings expire, blog posts move.

The register was filled on 9 October 2026. `Q1-*` rows are the figures rechecked against primary sources
that day; `FIG-*` rows are the key numbers drawn in the figures. It does not yet cover every number in the
paper; rows are added as claims are rechecked.

| Column | Meaning |
|---|---|
| claim_id | Stable identifier; never reused |
| section | Section (and figure) of the paper where the claim appears |
| claim | The claim as printed |
| source | The reference as cited in the paper |
| url | Where the source was read (the primary source where it could be reached) |
| accessed | Date it was read (YYYY-MM-DD) |
| archive_url | A dated copy in the Internet Archive (filled by `tools/archive_urls.py`); for archive.org items, the item itself |
| quote_or_locator | The source's own words, or page and table; a bracketed note means the quote is still to be copied |
| status | `verified` (read in the primary source), `secondary` (read in a report or summary of it), `licensed` (read in a licensed copy), `not-opened` (not reopened in the 9 October pass) |
| note | Anything a checker needs: rounding, currency, edition, population |
| period | The period the number covers |
| population | Who or what is counted |
| measure | The unit |
| checked_by | Who checked it; a check by a model of a different family from the one that wrote the claim is added here |

## Updating the register

1. Change a row only after opening the source.
2. Paste the quote verbatim.
3. Archive the page (`python3 tools/archive_urls.py sources/claims.csv`, or `https://web.archive.org/save/<url>`).
4. Set the status and add your name and the date.

## Keeping it alive

- `python3 tools/archive_urls.py sources/claims.csv` saves a copy of every source that has none yet.
- `.github/workflows/archive-sources.yml` runs the same command on the first day of each month and
  commits the new links, once the repository is public.
- Found a claim that no longer matches its source? Open an issue with the `claim_id`.

## Gaps as of 9 October 2026

- **No snapshot yet.** The Wayback Machine returned 429 or 523 for three pages: Celenza (2026), Esnaola et
  al. (DOI page) and the App Store count (reported by Gigazine, 2026, from Sensor Tower estimates). The
  monthly job retries them.
- **Gartner.** The full Gartner document 8068765 is for subscribers only, so the figures are cited as
  summarised by Tray.ai.
- **Quotes still to copy.** The four `FIG-*` rows marked `not-opened` still need their verbatim quotes.
