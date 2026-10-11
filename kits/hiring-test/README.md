# Hiring test: one day of work in the candidate's own domain

*Paper: Section 10.1 (for employers and HR) and Section 6.2 (the credential crossover point).*
*For: employers and HR teams who want to hire by verified work instead of by degree or job title.*

The candidate receives a day's work (about 8 reference hours) in the domain of the role, does it
through any agents they like, and must show it is right under a check they did not design, with a few
planted errors to find. The test measures what the job needs: delivering verified work through agents.

## Files
| File | Use |
|---|---|
| `task-brief.md` | Template for the task the candidate receives |
| `hidden-check.md` | The check and the sealed planted-error list; never shown to the candidate |
| `blind-rater-sheet.md` | Sheet for a reviewer who does not know the candidate's background |
| `job-posting-template.md` | A posting that asks for verified work and does not require a degree |

## Steps
1. Choose a real piece of past work (anonymised) of about one day for a qualified specialist. Two
   colleagues estimate its by-hand hours separately, as Section 5.1 of the paper asks. If the larger
   estimate is at most 1.5 times the smaller, use their geometric mean (the square root of their
   product); otherwise a third colleague estimates it too, and the median of the three is used (Section
   5.8 and Table 3). `python3 tools/reference_hours.py 6 10` does the arithmetic and says when a third
   estimate is needed; `../reference-hours-raters.md` says how to choose and brief the raters.
2. Write the brief from `task-brief.md`. Plant one to three errors, at least one of them an omission
   (`../planted-errors-guide.md`), seal the list with `python3 tools/planted.py seal`, write the hidden check.
3. Give every candidate the same task, the same time window and the same budget for AI tools, or let
   them use their own tools and record which.
4. The candidate returns the result, their own acceptance card (`../acceptance-card.md`) and a short
   log of what they handed over and how they checked it.
5. A rater who has not seen the CV scores the result with `blind-rater-sheet.md`.
6. Decide on the scores. Record the candidate's background separately, so the organisation can later
   compare hires at equal verified horizon (Section 10.1).

## Fairness notes
- Pay candidates for a full day of work.
- Offer the same accommodations as for any work sample test.
- Never reuse the task's planted errors with candidates who may talk to each other.
