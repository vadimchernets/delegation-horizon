# Matched-task study protocol

*Paper: Section 6 (background neutrality and the credential crossover point), predictions F2 to F7.*
*For: researchers, and organisations that want to test the claim on their own work.*

The question: on the same tasks, with the same agents and the same blind checks, do people without an
IT background deliver work of the same verified quality and size as programmers? Most published
comparisons gave the two groups different tools or tested short exercises (Section 12). This protocol
removes those differences.

## Design
| Element | Rule |
|---|---|
| Groups | People with and without IT education or programming employment, recruited for the same domain experience (for example five years in bookkeeping) |
| Tools | The same agent CLI or product, same model, same settings, same budget for every participant |
| Tasks | Drawn from a frozen task bank with reference hours set by two raters blind to the groups; each participant gets tasks of the same sizes |
| Check | Hidden tests, a blind qualified reviewer, and a security scan; reviewers never see group membership |
| Planted errors | One or more per task from Day size upward, sealed (see `planted-errors-guide.md`) |
| Maintenance | One month later, a different agent makes a small change to each accepted result; whether it succeeds is recorded |
| Logging | Every piece in the work log of Appendix C1, failed and abandoned ones included |
| Outcome | Verified pass share at each size; amplification gain; maintenance success; planted errors caught |

## Analysis plan (write it down and register it before data arrive)
1. Primary: difference in verified pass share between groups at the Day size, with a 95% interval.
2. Equivalence margin chosen in advance (for example 10 percentage points); "parity" means the whole
   interval lies inside the margin.
3. Secondary: the same at Hour and Week sizes; gain; maintenance success.
4. Report every participant, including those who dropped out, and every task, including failures.

## Size
For a margin of 10 points around a pass share near 70%, roughly 400 people per group give an interval
of about plus or minus 6 points at the Day size. Smaller studies are still useful as pilots: state the
interval you got, not a verdict.

## Practical notes
- Randomise task order; balance domains across groups.
- Score with `horizon.py` from the logs, so the analysis uses the paper's rules unchanged.
- Publish the task bank hash, the reference hours and the code before results.
