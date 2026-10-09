# Codebook: what crosses over from programmers' conversations

*Paper: Section 9 and Table 5.*
*For: researchers who want to repeat or extend Table 5 on other threads, forums or interviews.*

Code each post or comment (the unit) with one primary code. Two coders work independently, then
`tools/kappa.py` gives their agreement and writes the disagreements for a reconciliation meeting.
Report kappa before and after reconciliation; publish the codebook version you used.

## Codes (version 1.0)

| Code | Definition | Include | Exclude |
|---|---|---|---|
| blame | Who is responsible for bad AI output: the model, the setter of the task, the reviewer | "the spec was bad, not the model" | General complaints about quality with no attribution |
| check_cost | The cost, time or price of checking AI output | review hours, reviewer rates, rework | Cost of the AI tool itself (use spend) |
| tiering | Dividing work between a strong planning model and cheaper working models | planner/worker splits, budgets by role | Choosing one tool over another (use compare) |
| overload | Fatigue, constant change of tools, fear of missing out | "my workflow is dead every 3 months" | Workload unrelated to AI |
| own_tools | Building one's own tool instead of buying software | replacing a SaaS with an agent-built tool | Configuring bought software |
| compare | Comparing agents or models on the same task | side-by-side trials, benchmarks run by users | Brand loyalty without comparison (use camp) |
| migration | Moving a team or company onto agents | change programmes, consulting offers | A single person's switch of tool |
| spend | Personal or team AI spend, as cost or as status | monthly bills, caps, allowances | Check costs (use check_cost) |
| camp | Identity attached to one agent or vendor | "X people vs Y people" | Reasoned comparison (use compare) |
| other | None of the above | | |

## Unit and procedure
1. Unit: one post or one top-level comment; replies are coded separately if they add a claim.
2. Collect the sample with its date and URL into a CSV (`item, url, date, text`); do not record
   commenters' names.
3. Each coder adds a column (`coder_a`, `coder_b`) without seeing the other's.
4. Run: `python3 tools/kappa.py codes.csv --a coder_a --b coder_b --id item --disagreements dis.csv`.
5. Meet, fill `agreed_code` in `dis.csv`, and record any change to the definitions as version 1.1.
6. For each code, search the counterpart outside software for the same period and record it as in
   Table 5: counterpart, source, crossed over (yes / partly / no).

A kappa above 0.6 is the usual floor for reporting coded shares; below that, refine the definitions.
