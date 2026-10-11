# Raters of reference hours: whom to ask, how to admit them, how to combine what they say

*Paper: Section 5.1 (reference hours), Table 3 (generous raters), Section 6.2 (gates that admit by a label and gates
that check the work), Appendix E4 (model raters), Appendix G2 (a Prolific pre-pilot of human raters).*
*For: employers and schools building a task bank, researchers, and anyone who needs reference hours for a log.*

Every rung is counted in reference hours: the time a qualified specialist would need to do the piece by hand. When
the piece is not in a frozen bank with measured times, two raters estimate it. This kit is how to get those two
numbers so that an auditor can trust them.

## 1. Who rates
- Two specialists of the domain who did not do the work and do not know who did it, its background or its result.
- Whoever runs the rating gains nothing from a larger number.
- Model raters can order a bank (four of them agreed on which tasks were larger, intraclass correlation 0.89, in
  Appendix E4) and are no stand-in for the two raters: they differed by a factor of two in level, and given only a
  task's identifier their estimates were of little use.

## 2. Admit raters by a question of the trade, not by a label
A profile, a job title or a degree is a label: it admits people on their own word (Section 6.2). In the Prolific
pre-pilot of Appendix G2, 11 of the 60 people admitted as bookkeepers by their profile answered a first-week question
of the trade wrongly, eight of them by reversing the debit and the credit, and they rated the larger tasks lower than
the others did. A question of the trade is the cheaper gate that checks something.
- **One question a practitioner answers in the first week**, multiple choice, with the reversal among the options.
  The two used in the pre-pilot (`pilot/prolific_to_long.py`): for bookkeeping, the double entry for a customer's
  payment received into the bank ("Debit bank, credit accounts receivable"); for web development, what a LEFT JOIN
  returns ("All rows of the left table, with matching rows of the right table or NULLs").
- **Write a fresh one for each domain and round**, and keep it with the sealed material, not in a public posting.
- **Ask it supervised or under a short time limit.** Chat models answer static screening questions (Serafini et al.,
  2024); audio questions that reveal their content step by step under a strict time limit still held in 2026 (Serafini et
  al., 2026).
- **Report how many it stopped**, as Appendix G2 does, and pay the people it stopped for their time.

## 3. Brief them the same way every time
- Give the full statement of done, the inputs and the hidden check's form, never a title alone.
- Ask for "hours of focused work for a qualified professional working alone without AI tools" for the whole
  deliverable as accepted (the wording of Appendix G2).
- Calibrate first: let raters estimate three to five tasks with measured by-hand times and show them their error
  (Appendix E5). A rater's steady level offset is the cheapest error to remove.

## 4. Combine the two numbers
`python3 tools/reference_hours.py 8 10.5` prints the reference and the cells of the log line:
- within a ratio of 1.5, the geometric mean of the two (here 9.2 hours, Day size);
- further apart, a third rater, blind to the first two; with three estimates the median decides
  (`python3 tools/reference_hours.py 6 10 7`).
Write `reference_basis` as `two raters` and the estimates in `rater_hours` (`8;10.5`); `horizon.py` prints
"needs third rater" for any piece with two estimates more than 1.5 apart, and not once the third estimate is in.

## 5. Check the raters as a group
For a bank rated by many people, `pilot/human_raters.py` and `pilot/table_g2.py` give the share of rater pairs within
1.5 (the calibration protocol asks for at least 70%), the same after removing each rater's level, the intraclass
correlation, test-retest and each task's median against its intended rung; `pilot/screen_compare.py` compares the
raters the question of the trade stopped with those it kept.
