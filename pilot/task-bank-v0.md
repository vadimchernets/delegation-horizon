# Task bank v0

Thirty tasks, ten per domain, written for the desk pre-pilot and as a seed for the live pilot. All data are synthetic. Reference hours are not given here: in the pre-pilot they were estimated blind by model raters (`results/model-ratings.csv`); in the live pilot they are measured on a share of tasks and rated by two blind human specialists on the rest. Planted errors are required from Week upward (Section 5.2). Each task follows `templates/task-card.md`.


## small-business bookkeeping

| ID | Intended rung | Statement of done | Hidden check | Planted errors |
|---|---|---|---|---|
| BK01 | Hour | Reconcile one month of a single bank account (about 60 transactions, synthetic data) against the ledger; list every unmatched item with its amount and a one-line reason | Hidden list of the 7 true unmatched items; pass if all 7 are found and no false item is listed | 0 |
| BK02 | Hour | Categorise 120 card transactions of a café (synthetic) into the 14 accounts of a given chart of accounts | Hidden answer key; pass if at least 114 of 120 match | 0 |
| BK03 | Hour | Prepare a one-page VAT summary for one quarter from a given sales and purchases register (synthetic, one rate plus exempt sales) | Hidden figures for output tax and input tax and net payable; pass if all three match to the cent | 0 |
| BK04 | Day | Close one month for a small retailer (synthetic): bank reconciliation for two accounts, accruals for three known bills, depreciation of five assets, trial balance that balances | Hidden closing trial balance; pass if every account matches within 1.00 | 0 |
| BK05 | Day | Build a spreadsheet tool that ages accounts receivable (0-30, 31-60, 61-90, over 90 days) from an invoice export and flags customers over a credit limit | Hidden test file of 300 invoices with known buckets and flags | 0 |
| BK06 | Day | Migrate twelve months of transactions from a CSV export into a new chart of accounts using a mapping table, producing opening balances and a migration log | Hidden totals per new account and a list of 9 rows that cannot be mapped; pass if totals match and all 9 are logged | 0 |
| BK07 | Day | Prepare a 13-week cash-flow forecast for a small services firm from 12 months of history and a list of known contracts, with stated assumptions | Expert review against a rubric of 10 items; pass at 8 or more | 0 |
| BK08 | Week | Year-end close for a small company (synthetic): all reconciliations, fixed asset register, accruals and prepayments, inventory adjustment, draft profit and loss and balance sheet with notes | Hidden closing figures and expert review of notes; pass if figures match and review passes | 3 |
| BK09 | Week | Design and build a reusable month-end close workbook with checks for a firm with three entities and intercompany balances, plus a written procedure a junior can follow | Hidden test month with known errors; pass if the workbook's checks flag every one | 3 |
| BK10 | Week | Reconstruct the books of a small firm from bank statements and a shoebox of 400 receipts (scanned, synthetic) for one year, ready for a tax return | Hidden reconstructed ledger; pass if totals per account match within 0.5% | 3 |

## internal web tools

| ID | Intended rung | Statement of done | Hidden check | Planted errors |
|---|---|---|---|---|
| WT01 | Hour | Write a script that reads a folder of CSV exports and writes one merged file with a source column and de-duplicated rows | Hidden test folder with 5 files and known duplicates | 0 |
| WT02 | Hour | Add server-side validation for email, date and amount fields to an existing small form handler, with clear error messages | Hidden unit tests (20 cases) | 0 |
| WT03 | Hour | Fix a reported bug in which a list page shows deleted records; add a regression test | Hidden test reproducing the bug plus existing suite | 0 |
| WT04 | Day | Build a single-page internal tool to log equipment loans (who, what, out, back) with a small database, search and an overdue view | Hidden acceptance tests (15) run against the deployed tool | 0 |
| WT05 | Day | Add role-based access (viewer, editor, admin) to an existing internal app with about ten routes; document which role sees what | Hidden tests that probe every route with every role | 0 |
| WT06 | Day | Write an importer that pulls orders from a documented REST API every hour, stores them, and retries on failure with a log | Hidden mock API with failures and pagination; pass if all orders arrive once | 0 |
| WT07 | Day | Replace a fragile nightly spreadsheet macro with a scheduled script that produces the same report, with a comparison run on three past months | Hidden three-month comparison; pass if outputs are identical | 0 |
| WT08 | Week | Build an internal booking system for meeting rooms with calendar view, conflict rules, email reminders and an admin page, to a 3-page specification | Hidden acceptance suite (40 tests) and real use by 5 staff for a week | 3 |
| WT09 | Week | Migrate a small internal app from one framework to another with no change of behaviour, including its tests and deployment | Hidden behaviour suite run on old and new; pass if all match | 3 |
| WT10 | Week | Build a customer support inbox tool that pulls email, tags by topic, assigns to staff and reports response times, to a 4-page specification | Hidden acceptance suite (35 tests) and expert review of the report | 3 |

## legal and marketing documents

| ID | Intended rung | Statement of done | Hidden check | Planted errors |
|---|---|---|---|---|
| LM01 | Hour | Summarise a 20-page commercial lease (synthetic) into a one-page term sheet: parties, term, rent, reviews, break clauses, repair obligations | Expert key of 12 terms; pass if all 12 are correct | 0 |
| LM02 | Hour | Write five versions of a product announcement email (150 words each) from a one-page brief, each for a named audience | Expert review against brief (fact accuracy |  audience fit); pass if no factual error and 4 of 5 fit |
| LM03 | Hour | Compare two versions of a standard services agreement and list every substantive change with its effect | Hidden list of 9 substantive changes; pass if all 9 are found | 0 |
| LM04 | Day | Draft a data processing agreement for a small software vendor from a given template and a fact sheet, with all blanks filled and choices explained | Expert review against a checklist of 15 items; pass at 14 or more | 0 |
| LM05 | Day | Produce a competitor comparison for a small software product: eight competitors, pricing, features, positioning, each fact with a public source | Hidden fact sample of 20 claims checked against sources; pass if 19 or more hold | 0 |
| LM06 | Day | Write website copy for a five-page site of a local accounting practice from interview notes, with page structure and meta descriptions | Real use: the owner approves without factual corrections; expert review of claims | 0 |
| LM07 | Day | Review a 40-page supplier contract (synthetic) for a buyer and produce an issues list with proposed redlines for the top ten risks | Expert key of 10 planted risky clauses; pass if 9 or more are found with sound redlines | 0 |
| LM08 | Week | Assemble a due-diligence pack for the purchase of a small business (synthetic data room of 60 documents): findings report, red flags, document index | Expert key of 12 issues including 3 planted ones; pass if all planted and 10 of 12 found | 3 |
| LM09 | Week | Build a three-month content campaign for a product launch: strategy, calendar, 30 pieces of copy, and a measurement plan | Expert review against brief and real use of the first two weeks | 3 |
| LM10 | Week | Prepare a complete employee handbook for a 25-person firm in one jurisdiction from a policy questionnaire, with all mandatory policies | Expert checklist of 25 mandatory items including 3 planted gaps; pass if all planted gaps are caught and 24 of 25 present | 3 |
