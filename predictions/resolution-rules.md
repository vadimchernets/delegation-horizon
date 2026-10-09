# Resolution rules (v2 DRAFT)

1. Every prediction has three outcomes: came true, did not, unresolved. Unresolved is never a success.
2. An interval that meets neither the came-true rule nor the did-not rule is unresolved, for every study-based prediction.
3. Set A predictions resolve from public data and the files in `resolve/`. Set B predictions resolve only from a study registered separately before data collection; if its protocol is not registered by 30 June 2027 the prediction is recorded as "not conducted", listed on every scorecard and excluded from the Brier score.
4. Probabilities are conditional on resolution. Each scorecard prints: the Brier score over resolved predictions, by set and by family (a family counts once); the share resolved; a worst bound in which every unresolved prediction past its final date is scored as wrong; and the Brier skill score against a flat 0.5, against the pooled model forecasters and, where a market existed on the registration day, against the market price (`skill.py`).
5. A fallback source counts only if it measures the same quantity.
6. The crossover point in a domain is the first year in which F3 and the domain analogue of F5 are both met in that same named domain.
7. Disagreements on resolution are settled by the frozen text; models of two families check each scorecard and their disagreements are reported.
