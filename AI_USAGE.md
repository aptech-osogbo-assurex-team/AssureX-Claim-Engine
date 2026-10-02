# AI Tool Usage Log

AI tools were used as development assistants. The team reviewed generated changes, ran the relevant code, and corrected issues found during testing.

| Date | Tool | Area | Human verification / correction |
|---|---|---|---|
| 2026-09-25 | Claude | `src/data_generation/generate_claims.py` | Ran the generator; confirmed 1,500 records and the 350/75/75 split per class; reviewed the class-generation logic. |
| 2026-09-26 | GLM 5.3 | `src/model_training/train_model.py` | Ran the baseline; observed 81.78% test accuracy, below the 85% target; reviewed the confusion matrix and Manual Review recall. |
| 2026-09-27 | Claude | Dataset generation and model training | Tested feature engineering and tuning; identified the synthetic class-boundary issue and corrected the generation logic; verified accuracy improvement on the local test run. |
| 2026-09-28 | Claude | `src/data_generation/generate_claims.py`, `data/claims.csv`, `src/model_training/train_model.py`, `model/classifier.joblib` | Reviewed contradiction flags against real dates; added the repair-date field/fix and retrained; verified the 350/75/75 split and 92.89% held-out test accuracy. |
| 2026-09-28 | AI-assisted engineering review | Domain, rules, decision engine, persistence, API, OCR and UI | Reviewed generated implementation against the SRS; added strict schemas, configurable rules, deterministic adjudication, model metadata, authentication, document hashing/OCR, tests and real Teachable Machine browser integration. |
| 2026-09-29 | Resubmission hardening review | `src/cards/dataset.py`, dataset/card evidence scripts, policy artifacts, documentation and evaluation tooling | Identified the CSV→Claim Summary Card fidelity defect; corrected document/repair reconstruction, regenerated the card corpus, verified 0 fidelity mismatches, added split/mapping/evaluation artifacts and documented the Teachable Machine retraining/evaluation requirement. |

| 2026-09-30 | AI-assisted engineering review | Teachable Machine Model A, model comparison, submission validation and documentation | Verified 191/225 correct predictions (84.8889%) on the independent 225-card test set; recorded the 0.1111 percentage-point gap to the 85% SRS target without rounding; reviewed Model B validation at 80.4444% and did not promote it; verified the 30-case comparison report with 25/30 prediction agreement (83.33%); ran submission validation with PASS results and 45 passing tests; synchronized the resubmission documentation. |

## Rules for AI-assisted code

1. No hard-coded claim outcomes or fabricated confidence values.
2. AI-generated code must be run and tested before it is treated as implemented.
3. Team members must understand the code they submit and be able to explain the decision flow.
4. Problems discovered during verification must be recorded and corrected rather than hidden.
