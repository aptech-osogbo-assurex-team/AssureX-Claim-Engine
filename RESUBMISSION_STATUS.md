# AssureX — Resubmission Status



Date: 2026-09-30



This package contains the evidence-first hardening and final validation work for the AssureX submission.



## Current verified status



The major evidence gaps identified during hardening have now been addressed.



- common dataset retained at 1,500 claims with exact 70/15/15 split;

- 2,550 Claim Summary Cards retained across training, validation and test data;

- card fidelity audit: 1,500 claims checked, 0 field mismatches;

- explicit train/validation/test CSV artifacts;

- Claim ID → image mapping;

- test-set manifest and integrity verification;

- data dictionary and dataset statistics;

- three standalone warranty-policy files;

- Python model evaluation report;

- corrected Teachable Machine training set;

- Teachable Machine Model A retrained on the corrected 2,100-card training set;

- Teachable Machine evaluated on the independent 225-card test set;

- 30-case Python/TM model-comparison report;

- final submission validator;

- full automated test suite.



## Teachable Machine final result



The retained production Teachable Machine Model A was evaluated against the independent 225-card unseen test set.



- Test records: 225

- Correct predictions: 191

- Accuracy: 84.8889%

- SRS target: ≥85%

- Gap: 0.1111 percentage points



The result is reported exactly. It is below the stated SRS target by 0.1111 percentage points and is therefore not represented as a pass.



## Model comparison



A deterministic 30-case comparison was generated from the independent test set.



- Claims compared: 30

- Prediction agreement: 25/30

- Agreement rate: 83.33%

- Report: reports/model_comparison_30.csv



The 30-case comparison demonstrates claim-level integration between the Python model, Teachable Machine, warranty rules and the final decision pipeline. It is not used as a substitute for the full 225-card Teachable Machine accuracy measurement.



## Model B validation experiment



A separate Teachable Machine configuration was evaluated on the validation set.



- Model A: 189/225 = 84.00%

- Model B: 181/225 = 80.4444%



Model B was not promoted to production.



The independent test result above remains the retained final Model A measurement.



## Final validation



The submission validator currently reports:



dataset_split       PASS

card_fidelity       PASS

card_mapping        PASS

standalone_policies PASS

tm_artifact         PASS

comparison_30       PASS

overall             PASS



The full automated test suite reports:



45 passed



There is one non-failing Starlette/httpx deprecation warning.



## Remaining submission work



The remaining work is primarily final review and packaging:



1. Review the synchronized documentation.

2. Review the final Git diff.

3. Remove temporary working files that are not intended for submission.

4. Confirm the required video, technical blog and deployment links.

5. Run the final validation again before packaging.

6. Create the final submission archive only after the review is clean.



## Engineering integrity rule



The current Teachable Machine result must remain 84.8889% in the documentation.



Do not round it to 85%, replace the test set, or alter the retained production model merely to make the numeric requirement appear satisfied.



The submission should clearly distinguish between:



- functionality that has been implemented;

- evidence that has been verified; and

- the SRS numeric target that remains narrowly unmet.

