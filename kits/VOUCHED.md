# VOUCHED.md (template for a product repository)

*Paper: Section 7.1 (vouching as a second door for newcomers) and Section 10.3.*
*For: maintainers and platforms who let in newcomers when a known person vouches for them. Copy this
file to the root of your repository and keep it current.*

Contributions and releases from newcomers are accepted here when a known person vouches for them. The
voucher's record grows or shrinks with what happens next. Entries are never deleted; a withdrawal is a
new line.

| Date | Newcomer (handle) | Vouched by (handle) | Scope (what the voucher checked) | Record shown (domain . horizon . date) | Status |
|---|---|---|---|---|---|
| 2026-10-09 | example-newcomer | example-voucher | first pull request: tests and review read | bookkeeping . Day . 2026-Q4 | active |

## Rules
1. A voucher vouches only for what they checked, and writes it in "Scope".
2. A voucher may vouch for at most [N] active newcomers at once.
3. If vouched work causes an incident, both handles are noted in the incident line, and the voucher's
   further vouches pause until a maintainer reviews.
4. A newcomer with [M] accepted contributions without incident no longer needs a voucher.

## Incident lines
| Date | Handle(s) | What happened | Severity | Status |
|---|---|---|---|---|
