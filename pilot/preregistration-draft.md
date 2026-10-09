# Preregistration draft: feasibility pilot of the verified delegation horizon

Template: OSF Preregistration (standard). Draft of 9 October 2026; fields in braces are filled at
registration. Full design: `pilot-protocol.md`.

## Study information
- Title: Feasibility pilot of the verified delegation horizon and amplification gain
- Authors: {AUTHOR}
- Description: A six-month pilot with 60 adults (30 with a software background, 30 without) in three
  low-risk domains, testing whether reference hours can be rated reliably, whether a person's rung
  repeats across two 91-day windows, and whether the rung predicts passing new work.
- Hypotheses:
  - H1. At least 70% of pairs of blind human estimates of reference hours lie within a ratio of 1.5.
  - H2. At least 60% of rated reference hours lie within x1.5 of measured by-hand times.
  - H3. Weighted kappa of the rung across two consecutive windows is at least 0.6.
  - H4. The rung held predicts passing new tasks at that size with AUC at least 0.7.
  - Feasibility: fewer than 5% lost log lines; at least 95% of failed hand-overs recorded.

## Design plan
- Observational, within-person, two consecutive windows. No randomisation. Raters and checkers are
  blind to the person and to the background group.
- Prior work: a desk pre-pilot (no human participants) computed the rules' operating characteristics
  and the agreement of four model raters; it motivated rule v1.1 and rater calibration.

## Sampling plan
- Existing data: none. Recruitment open, not from any course or cohort.
- Sample size: 60 (30 + 30); up to 100 allowed. Justification: feasibility, not power. With 60
  people, a kappa of 0.6 has a 95% interval of roughly plus or minus 0.15.
- Stopping rule: end of window 2 for every participant who started window 1.

## Variables
- Measured: every log line of `log.schema.json` v1.1; two or three rater estimates per piece; measured
  by-hand time on 20% of bank tasks; rung and gain per person, domain and window from `horizon.py` v1.1.
- Indices: share of rater pairs within x1.5; ICC(2,1) on log hours; weighted kappa; AUC.

## Analysis plan
- H1, H2: `pilot/rater_agreement.py`; one-sided test that the share exceeds the criterion, exact
  binomial. H3: weighted kappa with bootstrap interval. H4: AUC with bootstrap interval.
- Sensitivity: every outcome re-scored with count 8, 10, 12 and share 0.7, 0.8, 0.9.
- Exploratory: rung and gain by background group (paper hypothesis F7); not confirmatory.
- Missing data: pieces with lost lines are reported; persons with fewer than five lines in a window
  are reported but excluded from H3 and H4.

## Other
- Ethics review: {COMMITTEE}, {APPROVAL_ID}. Consent: `consent-template.md`, separate from any other consent.
- Code and data: `delegation-horizon` repository, release {VERSION}; pseudonymous logs released after
  the study under CC BY 4.0.
