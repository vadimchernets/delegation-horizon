# Trade screen: admit people by a check of the trade, not by a label

*Paper: Section 6.2 (gates that admit by a label, and gates that check the work) and Section 10.5 (experience established by a knowledge screen and a record of work).*
*For: researchers who recruit people "with experience in a trade", and employers before a work test.*

A label admits a person on what they say or once showed: a profile on a platform, a job title, a
degree and, in part, a licence. It tells you about the work only as far as holding it goes with being
able to do the work, and a label that rests on a person's own word was always cheap to claim (Section
6.2). A screen puts a question of the trade behind the label and admits the people who answer it.

The pre-pilot of Appendix G2 met the difference by accident. Prolific admits participants through
filters whose answers are mostly self-reported. Of the 60 people its filters admitted to the
bookkeeping sample, 11 answered a first-week question of the trade wrongly, eight of them by reversing
the debit and the credit. Researchers who recruited programmers on such platforms before agents saw
the same: 42% of a platform's workers who stated programming skill did not meet the criteria of
knowledge questions (Danilova et al., 2021), and on Prolific 55 of the 206 respondents who reported
programming in Node.js passed all of its programming questions (Reid et al., 2022).

## 1. Write the question
- **First week.** Ask what anyone who has worked a week in the trade knows, not a specialist's detail.
  A wrong answer to such a question is a strong sign that the person does not know the trade, though
  haste and a misread question leave the same trace; a right answer shows only the first week.
- **One correct option.** The wrong options include the mistake people really make, such as the
  reversed entry.
- **Plain words.** No trick and no double negative: the question tests the trade, not reading.
- **One to three questions.** Fix before the screen what admits (for example, every answer right), and
  record every answer, right or wrong.
- **Kept out of circulation.** A question that circulates stops being a check, as a planted error does
  (`planted-errors-guide.md`).

## 2. Two questions from the pre-pilot
| Trade | What the question asks | The correct option, as scored |
|---|---|---|
| Bookkeeping | The double entry for a customer's payment received into the bank | "Debit bank, credit accounts receivable" |
| Web and software development | What a LEFT JOIN returns | "All rows of the left table, with matching rows of the right table or NULLs" |

Both are scored in `../pilot/prolific_to_long.py`, and the options above are quoted as it scores them.
In bookkeeping the commonest wrong answer was the reversed entry: eight of the eleven.

## 3. Report the leak
Count the people the label admitted and those who failed the question, and report the share with its
interval, not the share alone. `../tools/gate_leak.py` gives an exact (Clopper-Pearson) 95% interval
and the admission factor, 1 / (1 - share failing): how many people the label must admit for every one
who passes the check.

```
$ python3 tools/gate_leak.py --admitted 60 --failed 11 --label "Prolific occupation filter"
gate: Prolific occupation filter
  admitted by the label: 60
  failed the check of the trade: 11
  share failing: 18.3% (exact 95% interval 9.5% to 30.4%, Clopper-Pearson)
  admission factor: 1.22 (1.11 to 1.44): the label must admit 1.22 people for every one who passes the check
```

The same for the Node.js sample of Reid et al. (2022), in which 151 of the 206 did not pass:

```
$ python3 tools/gate_leak.py --admitted 206 --failed 151 --label "Prolific: reported programming in Node.js"
gate: Prolific: reported programming in Node.js
  admitted by the label: 206
  failed the check of the trade: 151
  share failing: 73.3% (exact 95% interval 66.7% to 79.2%, Clopper-Pearson)
  admission factor: 3.75 (3.00 to 4.81): the label must admit 3.75 people for every one who passes the check
```

Given a file of answers instead, one row per person with the columns
`participant,group,admitted_by,answer_correct` (the last 1 or 0), the tool prints one block per group,
and a line for each label where a group was admitted by several, such as the several occupations one
filter accepts.

## 4. The form of the question
A static text question can be answered by a chat model. In a simulated attack, ChatGPT easily solved
the existing screening questions for programmers (Serafini et al., 2024); by 2026 it also got past the
static visual questions that had been designed to resist it, while audio questions that reveal their
content step by step under a strict time limit still held (Serafini et al., 2026). An unsupervised
online screen therefore uses that form: the question is heard, not read, it unfolds step by step, and
the time is short. Otherwise the question is asked live, in a call or in the room.

## 5. A screen is a weaker gate than checked work
A question shows that a person knows something the trade's first week teaches. It does not show that
they can deliver the trade's work, or accept an agent's. The stronger gates check delivered work: the
paid work test of `hiring-test/`, and the measure itself, which records what a person handed over and
what passed a check the agents did not see (`../horizon.py`). Use the screen to admit people to a study
or to a work test, and let the work decide the rest.

## 6. Where it is used
| Use | How the screen enters |
|---|---|
| The comparison of Section 10.5 (`process-vs-experience-study.md`) | Experience counts as present when a person passes the screen and has a record of work in the trade, and as absent when they have neither a record of work nor training in it; the screen result is recorded for everyone |
| The matched-task study (`matched-task-study.md`) | Confirms the domain experience both groups were recruited for, in place of a profile label |
| A hiring test (`hiring-test/`) | Step zero: a short live question before the paid day of work, so that the day goes to people who know the trade's first week |

## 7. What to report
- The label, the platform and its filters, as they stood on the date of recruitment.
- The questions, their correct options and the rule that admitted.
- People admitted by the label, people who failed, and the share with its exact interval
  (`../tools/gate_leak.py`).
- What happened to those who failed. In the pre-pilot, as registered, they were excluded from the
  outcomes and paid.
