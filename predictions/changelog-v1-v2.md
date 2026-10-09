# Changelog of the predictions, v1 (8 October 2026 draft) to v2 (9 October 2026 draft)

Nothing was registered before v2, so every change below was made before freezing. No v1 prediction was dropped.
Reviewers are cited by role: independent model reviewers of five families (labelled R-sol, R-gemini, R-kimi,
R-claude, R-chatgpt, R-deepseek, R-meta) answered the question "are these the best predictions possible?".

| ID | Change | Reason | Suggested by |
|---|---|---|---|
| all | Every row has came true, did not and unresolved rules; an inconclusive interval is unresolved, never "did not" | One rule for uncertainty across experiments | R-sol |
| all | Split into Set A (public data) and Set B (research programme; protocol registered by 30 June 2027, otherwise recorded as not conducted) | Readers can score Set A without the author | R-deepseek, R-claude (opus) |
| all | Probabilities are conditional on resolution; the share resolved is reported beside the Brier score; a worst bound scores every overdue unresolved prediction as wrong | Brier over resolved predictions rewards only conditional numbers; the worst bound blocks selective non-resolution | R-claude, R-chatgpt, R-sol |
| all | Columns added: set, family, registration deadline, model forecasts (median, geometric mean of odds, range), market price with URL and date | Provenance of probabilities; scoring by family so linked predictions count once | R-kimi, R-claude (opus), R-gemini |
| crossover | The crossover point in a domain is the first year in which F3 and the domain analogue of F5 are both met in the same named domain | v1 dated it from two different populations | R-sol |
| F1 | Unresolved if the session definition changes | Comparability | R-claude |
| F1b | The 10 occupations frozen; a 2-point margin for multiplicity | Ten comparisons | R-chatgpt |
| F2, F3, F3b | One study of 1,500 per group; F3 did-not now requires the upper bound below zero | At 400 per group a true 5-point advantage is shown about 30% of the time | R-claude |
| F4a, F4b | Explicit did-not rules; F4b written as an interval rule | Symmetry with F2 | R-sol |
| F5 | Taxonomy version, frozen skill list and exact matching rule in resolve/F5.md; baseline archived before registration | Without them nobody else can resolve F5 | R-sol, R-kimi, R-deepseek |
| F6 | Unresolved if fewer than half of the other domains cross | Otherwise "last" is undefined | R-claude, R-chatgpt |
| F7 | One sentence justifies the 0.67 to 1.5 margin (odds ratio 1.5 is about d = 0.22); did-not rule added | Margin looked arbitrary | R-deepseek |
| F8, F9, F11, F13, F25 | Frozen queries and codebook in resolve/ | Promised in v1, written nowhere | R-claude (opus) |
| F9 | Counts normalised by all postings | Overall posting volume moves both families | R-chatgpt |
| F11 | At least 10 postings from at least 5 employers | One posting is too easy and too noisy | R-claude |
| F14 | Gain must add 0.02 out-of-sample R squared | "Adds predictive power" had no threshold | R-chatgpt |
| F17 | Kept; soft twin F17b (at least one employer) added | F17 alone is near zero | R-deepseek |
| F19 | Predicts later verified output out of sample, not gain | Gain contains horizon by construction | R-chatgpt |
| F21 | Claude.ai sample named, not API | Two samples differ | R-claude (opus) |
| F22 | Product Hunt monthly leaderboards of 2027, top 100 by upvotes, two blind coders; unresolved if fewer than 50 codable | "Frozen ranking" was unnamed | R-deepseek, R-claude, R-chatgpt |
| F23 | Checked 9 October 2026: no proposed or final SOC 2028 structure yet | The prediction must not be known at registration | R-claude (opus) |
| F24 | "Scientific product" defined | Ambiguous | R-claude, R-chatgpt |
| F27 to F36, F17b | New predictions (see table) | Publicly resolvable additions | see each row |

New predictions: F27 survival of a frozen sample of agent-built products against Gartner (R-claude; sample must be frozen by 31 December 2026); F28 and F28b machine 80% horizon at Day and Week (R-claude, R-kimi, R-claude opus); F29 computer science majors (R-claude); F30 agent co-author trailers in GH Archive (R-claude); F31 builder against agent manager titles (R-claude); F32 vendor reports non-developer majority (R-claude); F33 machine security floor (R-kimi); F34 reproducible reference hours (R-chatgpt); F35 horizon predicts later output (R-chatgpt, merged); F36 verified-builder badges (R-deepseek).
Considered and not added: F3p, a point-estimate twin of F3, dropped after the blind raters flagged it as a near duplicate once F3 has 1,500 per group.

## Author against pooled models: differences above 0.15

The recommended probability is the midpoint in log odds of the two; the owner fixes the final number at registration.

- F6: author 0.6, pooled models 0.41; the domain argument of Section 6.3.
- F15: author 0.35, pooled models 0.56; entry-level take-home tasks are usually 2 to 6 hours.
- F32: author 0.15, pooled models 0.33; large-vendor coding agents are still used mainly by developers.
- F34: author 0.45, pooled models 0.62; reference hours are judgements and the rule uses the lower bound.
