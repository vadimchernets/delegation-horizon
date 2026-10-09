# Policy template: AI usage in performance reviews

*Paper: Section 4 (the year tokens were tried as seniority) and Section 10.1 (employers and HR).*
*For: HR teams and managers who are asked to "measure AI adoption" in reviews. Adapt the brackets.*

## 1. What we do not do

- We do not rank, rate, reward or set targets on the number of tokens, prompts, sessions, agent runs
  or the amount spent on AI tools, individually or by team. Usage dashboards are cost tools, not
  performance tools.
- We do not publish leaderboards of usage.
- We do not treat low usage as a performance concern on its own.

Why: when usage became a ranking in 2026, people optimised the number and not the work (Section 4).
Spending is the cheapest thing to inflate.

## 2. What we look at instead

| Instead of | We ask for |
|---|---|
| Tokens or spend | Accepted pieces of work, with the check each one passed |
| "Uses AI daily" | The largest piece of work the person handed to agents and verified in the last quarter (the verified delegation horizon), with domain and date |
| Hours saved (self-reported) | Verified work per hour of the person's attention (amplification gain), from a log that keeps failures |
| Number of agents run | Pieces that failed checks and what the person changed afterwards |

A record reads "domain . horizon . gain . date", for example "accounts payable . Day . x5 . 2026-Q4".
The log behind it is the evidence; `record_card.py` produces the card from the log.

## 3. Rules for using the record

1. The record is one input among several, never the only input to pay or promotion.
2. Only checks the agents could not see count: hidden tests, a qualified reviewer, real use, or another
   model family with sources the person opened. A self-review or a same-family model does not count.
3. The log keeps failed and abandoned pieces. A log with no failures is a reason for a friendly audit,
   not a reward (`tools/too_clean.py`).
4. The kind of check is printed next to every rung, so a reader sees what the number rests on.
5. People may decline to keep a log; the review then proceeds without it, with no penalty.

## 4. Review conversation, three questions

- What is the largest piece of work you handed to agents this quarter and showed to be right? How?
- What failed, and what did you change in how you check?
- Which of your checks would you trust if the stakes were ten times higher?

*Status: the rungs and thresholds are provisional until the human pilot (Section 5.8).*
