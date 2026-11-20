\*\*17 November 2026 — Medicine code field\*\*



I added an editable Medicine code field to the Register Medicine screen and tested it by typing `MED001`.



\[GitHub commit `5755735`](https://github.com/UCU-Campus-Pharmarcy/OOP-FINAL-PROJECT/commit/5755735)


## 18 November 2026 - Day 2

Completed the Register Medicine form layout.

[GitHub commit 1eb849e](https://github.com/UCU-Campus-Pharmarcy/OOP-FINAL-PROJECT/commit/1eb849ef49a3c51c9461f0f501b806bb1a2e7c0e)

## 19 November 2026 - Day 3

Connected the Register button to the existing medicine registration and SQLite modules. Added form validation and clear success and error messages.

Manually checked missing fields, invalid prices and reorder levels, successful registration, duplicate-code rejection, and persistence after restarting the application.

Included the existing database and medicine modules as GUI dependencies, corrected zero-price validation, and added launch and fictional sample-data instructions. Additional checks against a temporary database passed.

AI assistance from Codex included callback and validation examples, indentation debugging, verification, and help with Git and this task log.

[Implementation commit 67209ee](https://github.com/UCU-Campus-Pharmarcy/OOP-FINAL-PROJECT/commit/67209eef049b796f497aa2770ab85ac675f851c1)

## 20 November 2026 - Day 4

Added Register Medicine, Branches, and Receive Stock tabs. Connected branch creation and stock receipt to the existing stock module, included that module as a GUI dependency, and refreshed branch and medicine dropdowns when switching tabs.

Manually checked branch creation, duplicate-name errors, stock receipt totals, invalid quantities, separate branch balances, and persistence after restarting. Automated callback checks against a temporary database also passed, including mapping sorted branch names to their actual database IDs.

The final saved balances for DAY3-001 were 15 at Day 4 clinic and 3 at Day 4 satellite. Updated the README with today's work and verified figures.

AI assistance from Codex included examples for tabs and callbacks, indentation debugging, verification, Git, and documentation.

[Implementation commit cf8bd8f](https://github.com/UCU-Campus-Pharmarcy/OOP-FINAL-PROJECT/commit/cf8bd8fe91de44d5840047c4f316f9550404a01d)
