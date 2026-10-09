# Release checklist by risk

*Paper: Section 8 (two markets: phone snapshots and the wedding).*
*For: people who built something through agents and are about to let other people use it.*

Work for oneself is literacy; work for others with consequences is the profession. The step from one to
the other is the release. Find your row first, then do every item in that row and the rows above it.

| Level | Who uses it | Examples | Before release |
|---|---|---|---|
| 0. Myself | Only me | a personal notifier, my own contract checker | Back up my data; know how to switch it off |
| 1. My team | People I work with, who can ask me | a shared spreadsheet tool, a team bot | Level 0, plus: a one-paragraph "what it does and does not do"; who to ask; a way to undo the last change |
| 2. Strangers, low stakes | Unknown users, no money or personal data | a free utility, a public page | Level 1, plus: `tools/prerelease-check.sh` clean; no secrets in the repository; a contact address; a version number and change log |
| 3. Strangers, money or personal data | Paying users, accounts, personal data | a paid app, a booking system | Level 2, plus: a named person who answers (you or a guarantor, `guarantor-signoff.md`); a privacy notice that matches what the code does; a tested rollback; payment and deletion paths tested twice |
| 4. Irreversible or regulated | health, legal, financial advice, infrastructure | anything that moves money, gives advice relied on, or controls equipment | Level 3, plus: review by a qualified person in the domain; every irreversible action confirmed by the user; an incident plan; the relevant rules of your domain checked by someone who knows them |

## Six questions for every release above level 1
1. Who are the users, and what will they rely on?
2. What happens when it fails halfway?
3. How do we roll back, and have we tried it once?
4. Who answers, by name?
5. Who maintains it next month, and next year?
6. What would make us withdraw it?

Write the answers in the release notes. A product with answers is a product someone can trust.
