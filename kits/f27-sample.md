# The F27 sample: a protocol for freezing it by 31 December 2026

*Paper: Section 11.4 and Table A6 (prediction F27, agent-built products outlive the forecast).*
*For: whoever collects and freezes the F27 sample before 31 December 2026, and anyone who checks the scorecards.*

F27 is registered with a date that falls before its first check. Its frozen words (`predictions/predictions.csv`):
"A sample of at least 300 public products built mainly with coding agents, launched October to December 2026,
frozen on Zenodo by 31 December 2026; liveness checked by the companion script. Came true if fewer than 50% are
retired (unreachable or not updated for 12 months) on 31 December 2028." It is unresolved if "the sample was not
frozen by 31 December 2026", and its fallback source is "Wayback Machine snapshots of each product". The forecast
it bets against is Gartner's: 60% of vibe-coded applications retired by 2028 (Tyagi, 2026).

## What the registration leaves open, and the default taken here

Each line is one decision, to be confirmed or changed before the first candidate is collected.

| Question | Default | Why |
|---|---|---|
| Where candidates come from | Three strata: (1) public GitHub repositories created in the window whose commits carry an agent trailer of `predictions/resolve/F30.md`; (2) products launched in the window on a public launch site (Product Hunt, Show HN) whose makers say they were built with a coding agent or an agent app builder; (3) products published in the window in the public showcase of an agent app builder | Three routes by which agent-built products reach the public; no single source holds them all |
| Built mainly with coding agents | (1) at least half of the repository's commits in its first month carry a trailer; (2) the maker's own words on the launch page, quoted in `evidence`; (3) the showcase presents the product as made with the builder | One rule per stratum that someone else can check from the evidence column |
| Launched | (1) the date of the first commit; (2) the launch date on the launch site; (3) the date the showcase gives | The earliest public date of each route |
| What is not a product | Forks, templates and starter kits; repositories with fewer than five commits; tutorials and course exercises; products of the paper's author | They were never released for users to rely on |
| Key of the draw | Commit, then reveal: the SHA-256 of the closed pool of eligible candidates (`--digest`) is registered on OSF first; the key is then the randomness of a public beacon round, drand's default chain (League of Entropy, https://docs.drand.love), whose round number the protocol names: the first round published at least 24 hours after that registration | Nobody can know a product's key while collecting, so nobody can pick which products to enter, and a list changed after the registration no longer matches the registered digest; election audits draw their samples the same way (a public seed after the manifest is published) |
| Size | 100 per stratum, 300 in all, the least F27 allows; more if collection allows, the same number in each stratum | F27's minimum; equal strata keep one route from outweighing the others |
| Retired on 31 December 2028 | `tools/liveness.py` with its default of 365 days, following F27's words only: unreachable (404, 410, 451, or no server answers after the retries), or, for a GitHub repository, not pushed to for 12 months; being archived is written in its own column and does not retire a product. An answer that says nothing about the product (403, 429, 5xx, a rate limit that never lifts) is "unknown": it leaves the share and goes to the hand check, as does every address outside GitHub, checked against its Wayback Machine snapshots for an update within the 12 months | F27's words, "unreachable or not updated for 12 months", and its fallback source |

## Steps

1. **Fix the protocol before collecting.** Copy this file, confirm or change each default, date it, hash it
   (`shasum -a 256 f27-protocol.md`) and register it on OSF as an addition to the registration: Appendix D says
   that anything added later is registered separately and carries its own date.
2. **Collect candidates** into one CSV with the columns `name`, `url`, `stratum`, `launched` (YYYY-MM-DD) and
   `evidence`, plus any others you keep (for example how the product was found). Collect more than you draw: at
   least 150 per stratum.
   - Stratum 1, without cost: GitHub's commit search, one query per day of the window and per trailer of F30
     (for example `"Co-Authored-By: Claude" committer-date:2026-10-01..2026-10-01`), since one query returns at
     most 1,000 results. Keep repositories created in the window that pass the rules above, and put the share of
     commits with a trailer in `evidence`.
   - Stratum 2: Product Hunt's daily lists and Hacker News "Show HN" posts of the window. Keep a product when its
     maker says it was built with a coding agent or an agent app builder, and quote the words in `evidence`.
   - Stratum 3: the public showcases or galleries of agent app builders, products dated in the window.
3. **Close the pool and register its digest:**

   ```sh
   python3 tools/freeze_sample.py candidates.csv --digest
   ```

   It leaves out every row the protocol does not admit, says how many and why, and prints the pool digest, the
   SHA-256 of the candidates file and of `freeze_sample.py`. Register the three hashes on OSF (with the candidates
   file attached), and name in the same registration the drand round that will give the key.
4. **Draw, once that round is published** (its randomness is at `https://api.drand.sh/public/<round>`):

   ```sh
   python3 tools/freeze_sample.py candidates.csv --beacon <randomness of the round> --per-stratum 100 --out f27-sample.csv
   ```

   It keeps one row per product, written one way, draws by the key and prints the SHA-256 of the sample.
5. **Seal by 31 December 2026:** deposit on Zenodo the sample, the candidates file, the protocol and the printed
   output, and register on OSF, in the same week and no later than 31 December 2026, the SHA-256 of the sample, of
   the candidates file, of the protocol and of `freeze_sample.py`, with the Zenodo DOI. A Zenodo record can have its
   files changed for 30 days after publication without a new DOI; the OSF registration cannot be changed, so it is
   the registered hash, not the deposit alone, that a scorecard checks against.
6. **On every scoring date** (the scorecard of October 2027, and 31 December 2028 for the verdict):

   ```sh
   python3 tools/freeze_sample.py --check f27-sample.csv --sha256 <the hash registered in step 5>
   GITHUB_TOKEN=<optional> python3 tools/liveness.py f27-sample.csv --out liveness-2028-12-31.csv --as-of 2028-12-31
   ```

   Without a token GitHub allows 60 calls an hour, and the script waits for each reset (about two hours for 100
   repositories); a token raises the limit to 5,000. Then do the hand check of every row marked unknown and of the
   addresses outside GitHub against their snapshots. Keep every dated output: the series of files is the evidence.
   Run it on the scoring date: the column `checked` is the day of the run, and a push after `as_of` is sent to the
   hand check, not counted as alive.

## What the draw guarantees

Each candidate's key is the SHA-256 of the pool digest, the beacon value and its address written one way (scheme,
case, `www`, a trailing slash, a fragment and tracking parameters do not count; on GitHub only owner/repository, so
`/tree/main` or `.git` do not count either), and each stratum gives the candidates with the smallest keys. The pool
is closed and registered before the beacon round exists, so no key can be known while candidates are collected, and
entering or dropping a product afterwards changes the registered digest. Anyone holding the candidates file and the
round can recompute every key and see why each product is in the sample and each other one is not; the order of the
file and the version of Python change nothing (dates are read by one rule on every version). The sample is as wide as
the collection: a route of agent-built products that the candidates miss is missing from the sample too, which is
why the strata, their sources and the search queries are written down before collection.
