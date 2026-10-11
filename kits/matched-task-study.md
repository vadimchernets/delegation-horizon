# Matched-task study protocol

*Paper: Section 6 (background neutrality and the credential crossover point), Section 11.2 and Table A6 (predictions F2, F3, F3b and F7).*
*For: researchers, and organisations that want to test the claim on their own work.*

The question: on the same tasks, with the same agents and the same blind checks, do people without an
IT background deliver work of the same verified quality and size as programmers? Most published
comparisons gave the two groups different tools or tested short exercises (Section 12). This protocol
removes those differences. F2, F3, F3b and F7 resolve only from a study registered separately before
data are collected, with a named owner, a protocol and a power calculation; a prediction whose protocol
is not registered by 30 June 2027 is recorded as not conducted (Section 11.2).

## Design
| Element | Rule |
|---|---|
| Domains | Fixed in the registration and analysed one by one. The paper's crossover domains are small-business bookkeeping, and legal and marketing documents (Appendix D) |
| Groups | Programmers (IT education or programming employment) and people with neither, recruited for the same experience in the domain (for example five years in bookkeeping). Education and employment are established by a record (degree, job history), and equal domain experience by a knowledge screen of the domain scored before the work starts, not by a profile label (Section 6.2) |
| Tools | The same agent CLI or product, same model, same settings, same time and budget for every participant |
| Tasks | Drawn from a frozen task bank with reference hours set by two raters blind to the groups; each participant gets tasks of the same sizes in their own domain, and, for F3b, tasks outside it |
| Check | Hidden tests, a blind qualified reviewer, and a blind security review; reviewers never see group membership |
| Planted errors | One or more per task from Day size upward, sealed with their kind; both kinds, wrong entries and omissions, across the tasks (see `planted-errors-guide.md`) |
| Maintenance | One month later, a different agent makes a small change to each accepted result; whether it succeeds is recorded |
| Logging | Every piece in the work log of Appendix C1, failed and abandoned ones included |
| Outcome | Verified pass share at each size; amplification gain; maintenance success; planted errors caught |

## Analysis plan (write it down and register it before data arrive)
1. Primary: in each named domain, the difference in verified pass share, people without IT education
   minus programmers, on tasks of their own domain at the Day size, with a 95% interval.
2. F2 (parity) came true if the lower bound of that interval lies above minus 10 points; did not if the
   upper bound lies below minus 10; otherwise it is unresolved. This is a one-sided bound, not two-sided
   equivalence: an interval that lies wholly above zero meets it too.
3. F3 (overtaking) came true if the lower bound lies above zero; did not if the upper bound lies below
   zero; otherwise it is unresolved. F3b is the same, on tasks outside the participants' own domain.
4. F7 (background neutrality): the odds ratio of passing independent checks associated with IT
   education at an equal rung, controlling for domain command and acceptance literacy, with the horizon
   scored on one task set and quality on held-out tasks. It came true if the 90% interval lies within
   0.67 to 1.5, separately at Day and at Week and above; did not if the interval lies wholly outside
   0.67 to 1.5 at either level; any other combination, including equivalence at one level only, is
   unresolved.
5. Secondary: the same difference at Hour and Week sizes; gain; maintenance success; planted errors
   caught, wrong entries and omissions scored apart.
6. Report every participant, including those who dropped out, and every task, including failures. An
   interval that meets neither rule is unresolved, not a failure (Section 11.2).

## Size
The paper's study has 1,500 people per group (Section 11.2). At a pass share near 50%, that gives
about 0.8 power to detect a true advantage of 5 points (two-sided alpha 0.05); 400 per group would show
it about 30% of the time. `tools/power.py` repeats the arithmetic (normal approximation; `--p` is the
programmers' pass share, `--diff` the true advantage of people without IT education):

```sh
python3 tools/power.py --p 0.5 --diff 0.05 --n 1500      # power 0.78
python3 tools/power.py --p 0.5 --diff 0.05 --n 400       # power 0.29
python3 tools/power.py --p 0.5 --diff 0.05 --power 0.8   # 1562 per group for power 0.80
python3 tools/power.py --p 0.7 --n 1500 --margin 0.10    # chance 1.000 that the lower bound clears -10 points
```

The last line applies the came-true rule of F2: it gives the chance that the lower 95% bound of (people
without IT education minus programmers) lies above minus 10 points when the two groups are truly equal;
at 400 per group that chance is 0.870. The figures hold for each comparison: if F2 and F3 are read in each named domain,
each domain needs that many people per group. F7 needs its own power calculation, for the equivalence
of an odds ratio, which this tool does not make.

400 per group is a pilot size, stated as such. Near a pass share of 70% it gives an interval of about
plus or minus 6.4 points (`python3 tools/power.py --p 0.7 --n 400`): state the interval you got, not a
verdict.

## Practical notes
- Randomise task order; recruit both groups in every named domain.
- Run the knowledge screen supervised or under a strict time limit: chat models answer static screening
  questions (Section 6.2).
- Score with `horizon.py` from the logs, so the analysis uses the paper's rules unchanged.
- Publish the task bank hash, the reference hours and the code before results.
