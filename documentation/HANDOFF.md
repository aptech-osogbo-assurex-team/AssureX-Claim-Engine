# AssureX Claim Engine — Resubmission Handoff

## Repository

`https://github.com/aptech-osogbo-assurex-team/AssureX-Claim-Engine`

## Git baseline

The verified engineering baseline on GitHub `main` is:

* `335019d` — `feat: establish AssureX claim decision pipeline`
* `8352490` — `docs: add submission documentation foundation`

The reviewed competition submission ZIP was based on `4333210` and contained the
exported Teachable Machine model.

## Hardened changes in this working package

* corrected CSV → Claim Summary Card fidelity;
* regenerated all 2,550 cards;
* generated explicit train/validation/test CSV artifacts;
* generated Claim ID → image mapping;
* generated data dictionary and dataset statistics;
* generated card-fidelity audit: 1,500 claims, 0 mismatches;
* added three standalone warranty policy files;
* generated a Python model evaluation report;
* added browser batch evaluation for the real Teachable Machine model;
* added a 30+ model-comparison report generator;
* added final submission validator;
* refreshed the project report, blog, video plan and resubmission documentation.

## Verified Python evidence

* Dataset: 1,500 synthetic claims
* Training: 1,050
* Validation: 225
* Test: 225
* Test accuracy: 92.89%
* Five-fold CV mean: 90.76%
* Five-fold CV std: 1.72%
* Hardened working test suite: 45 passed

The saved classifier artifact remains the original scikit-learn 1.9.1 artifact.
The package requirements pin scikit-learn 1.9.1.

## Current evidence status

The major resubmission engineering work is complete.



The corrected Claim Summary Cards were regenerated and audited against the

structured claims with 0 field mismatches. The dataset split and test-set

integrity artifacts are retained.



Teachable Machine Model A was retrained using the corrected 2,100-card training

set, with 700 cards per class. The independent test set contains 225 cards,

with 75 cards per class.



The final retained Teachable Machine result is:



\- 191/225 correct predictions

\- 84.8889% accuracy

\- SRS target: at least 85%

\- Gap: 0.1111 percentage points below the target



The result is retained exactly and is not rounded upward.



Model A validation accuracy was 84.00%. A separate Model B experiment achieved

80.4444% on validation and was not promoted.



The retained 30-case comparison report is:

`reports/model_comparison_30.csv`









It contains 30 claims, with 25/30 prediction agreements (83.33%), 28 final

manual-review decisions and 2 likely-valid decisions.



The automated submission validator passes all required checks, and the complete

Python test suite passes with 45 tests passed and one dependency deprecation

warning.



## Remaining submission work



The remaining work is submission preparation rather than rebuilding the core

model pipeline:



1\. Review and synchronize the remaining documentation.

2\. Remove temporary files and confirm the final repository file set.

3\. Confirm the mandatory MP4 demo, technical blog and deployment/submission links.

4\. Run `scripts/validate\\\_submission.py` again on the final file set.

5\. Run `py -m pytest -q` again on the final file set.

6\. Create the clean final submission archive.



The Teachable Machine accuracy requirement remains an explicitly documented

0.1111-percentage-point gap. Do not round 84.8889% to 85%, alter the retained

test set, or change the reported evidence merely to make the requirement appear

satisfied.

## Integrity rule

Never fabricate:

* TM accuracy;
* model disagreement results;
* confidence values;
* reviewer outcomes;
* screenshots;
* deployment URLs.

## New-chat restart

> AssureX resubmission handoff: repository
> `aptech-osogbo-assurex-team/AssureX-Claim-Engine`. Stable engineering baseline
> is `335019d`; documentation baseline is `8352490`; submitted ZIP was reviewed
> from `4333210`. Resubmission hardening corrected CSV→Claim Summary Card
> fidelity, regenerated 2,550 cards with a 0-mismatch audit, added split/mapping
> evidence, three policy artifacts, Python evaluation reporting, TM batch
> evaluation tooling and a 30+ comparison generator. Read
> `documentation/HANDOFF.md` and continue from the Critical remaining action.

