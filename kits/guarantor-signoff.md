# Guarantor sign-off (one page per product)

*Paper: Section 7.2 (the guarantor) and predictions F11, F12.*
*For: a person who puts their name under a product they did not build, and platforms that ask for one.
A longer version of the record is in `templates/guarantor-record.md`.*

| Field | Entry |
|---|---|
| Product and version | |
| Built by (pseudonym or name, with consent) | |
| Builder's record for this domain ("domain . horizon . gain . date"), and where the log can be seen | |
| What I checked myself, and how | |
| What I did not check | |
| Intended users, and what they will rely on it for | |
| Known risks and how a user is warned of them | |
| Irreversible actions in the product, and how each is confirmed | |
| Who answers when it breaks, and how users reach them | |
| Maintenance promise (until when, by whom) | |
| Date of sign-off | |
| My signature line: "I vouch for this release of this product to the extent stated above." | |

## The guarantor's own record
Keep one line per product you vouched for in the CSV of `templates/guarantor-record.md` (columns
`guarantor`, `domain`, `product`, `maker`, `vouched_on`, `status`, `ended_on`, `severity`).
`tools/liveness.py` checks which products still answer, and `tools/guarantor_record.py` turns the CSV into
the guarantor's track record (Section 7.2): how many products, how many lived 6 and 12 months, the failures
by severity and the median life of those that ended.
