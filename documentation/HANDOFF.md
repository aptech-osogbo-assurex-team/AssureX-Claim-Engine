# AssureX Claim Engine — Engineering Handoff

_Last updated: 2026-09-29_

## 1. Repository

GitHub repository:
`https://github.com/aptech-osogbo-assurex-team/AssureX-Claim-Engine`

Current stable branch:
`main`

Current stable commit:
`335019d feat: establish AssureX claim decision pipeline`

The engineering checkpoint has been pushed to GitHub `main`.

## 2. Verified Environment

Student machine:
- OS: Windows
- Python: `3.13.1`
- scikit-learn: `1.9.1`

The saved model artifact was trained under scikit-learn `1.9.1`, and the repository now pins that version.

## 3. Test Status

Full suite on the student's machine:

`42 passed, 1 warning`

The remaining warning is a Starlette/httpx deprecation warning from the installed test-client stack. It is non-blocking; do not destabilize the build just to remove it unless there is a clear safe fix.

## 4. Engineering Checkpoint Implemented

The `335019d` checkpoint established:

- canonical domain schemas
- authentication/session handling
- SQLite persistence
- configurable warranty policies/rules
- rule engine
- deterministic decision engine
- existing Random Forest ML inference adapter
- model metadata/version tracking
- OCR/document intake layer
- secure document hashing/storage
- Claim Summary Card generation
- Teachable Machine browser integration hook
- duplicate-claim detection
- claim state/notification workflow
- reviewer override/audit trail support
- FastAPI application
- automated tests

## 5. Important Truth About Current ML Evidence

Current Python ML baseline:
- dataset: 1,500 synthetic claims
- classes: Valid Claim / Invalid Claim / Manual Review
- held-out test accuracy: `92.89%`
- confusion matrix and class-wise results exist in the engineering work

Important limitation:
`92.89%` is a result on the synthetic held-out dataset. It is NOT evidence of 92.89% real-world warranty-claim accuracy.

Cross-validation code has been added to the training pipeline, but actual CV results still need to be generated and documented as evidence.

## 6. Current Documentation Artifacts

Working documentation drafts created locally:

- `PROJECT_REPORT.md`
- `BLOG.md`
- `VIDEO_SHOT_LIST.md`

The intended repository location is:

```text
documentation/
├── PROJECT_REPORT.md
├── BLOG.md
└── VIDEO_SHOT_LIST.md
```

A documentation branch was created:
`docs/submission-documentation`

The documentation files are currently copied into that branch's `documentation/` directory but have not yet been committed/pushed as a documentation commit at the time this handoff was created.

## 7. SRS-Critical Remaining Work

### Highest priority

1. Real Google Teachable Machine model
   - Train the three required classes.
   - Export the actual model.
   - Place the exported model under the application's expected Teachable Machine static directory.
   - Preserve training/validation/test evidence.

2. Enforce evidence-driven evaluation
   - The final decision path should be based on persisted claim/evidence records rather than arbitrary client-supplied decision JSON.
   - Preferred flow:

```text
registration
→ claim creation
→ document/evidence upload
→ OCR/extraction
→ verification
→ persisted claim
→ Claim Summary Card
→ Python model
→ Teachable Machine
→ warranty/integrity rules
→ model/rule consistency
→ final decision
→ explanation/audit
→ manual review when required
```

3. Produce actual evaluation evidence
   - five-fold CV metrics
   - held-out test metrics
   - class-wise precision/recall/F1
   - confusion matrix
   - 30+ unseen claim comparisons between Python and Teachable Machine
   - model agreement/disagreement and confidence-difference evidence

4. Final SRS audit
   - check every functional and non-functional requirement
   - verify screenshots/demo evidence
   - verify security/privacy/error handling
   - verify dashboards/search/reporting/export/deployment requirements
   - verify final source tree contents

5. Mandatory presentation video
   - `.mp4` is mandatory
   - use `VIDEO_SHOT_LIST.md` as the recording checklist

6. Technical blog
   - minimum 2,000 words
   - publish externally
   - add published link to project documentation and repository

7. Final report
   - update `PROJECT_REPORT.md` with only verified final results, screenshots, metrics, links, and limitations

## 8. Documentation Principles

Never claim an SRS requirement is complete unless the feature exists and has been tested or otherwise demonstrated.

Use these labels while the work is incomplete:
- Implemented
- Partial
- Pending

Do not invent:
- Teachable Machine accuracy
- cross-validation scores
- unseen-claim results
- deployment URLs
- screenshots
- reviewer outcomes
- performance measurements

## 9. Git Discipline

Current stable point:
`335019d`

Do not rewrite or amend the stable engineering commit unless a real defect requires it.

Prefer focused commits, for example:

```text
docs: add submission documentation foundation
feat: integrate real teachable machine model
feat: enforce evidence-driven claim evaluation
chore: record model evaluation evidence
fix: close final SRS workflow gap
```

Before every commit:

```bash
git status
git diff --check
py -m pytest -q
```

Never commit generated runtime artifacts such as:

```text
data/assurex.db
data/uploads/
static/cards/
__pycache__/
.pytest_cache/
```

## 10. Immediate Next Action

The engineering checkpoint is already safely on `main`.

The next working branch is:

`docs/submission-documentation`

Immediate documentation action:

1. Stage the three documentation files.
2. Inspect the staged diff.
3. Run any relevant documentation checks.
4. Commit as a separate documentation commit.

Then return to the SRS-critical implementation/evidence path, with Teachable Machine as the first major remaining item.

## 11. If Starting in a New Chat

Start with this exact message:

> AssureX handoff: GitHub repo `aptech-osogbo-assurex-team/AssureX-Claim-Engine`. Stable `main` commit is `335019d` (`feat: establish AssureX claim decision pipeline`). Student environment is Python 3.13.1 with scikit-learn 1.9.1. Full test suite is 42 passed, 1 warning. Read `documentation/HANDOFF.md` and continue from the Immediate Next Action. Do not rewrite the architecture. Treat the SRS as the source of truth and distinguish implemented work from pending evidence.

## 12. SRS Source-of-Truth Reminder

The AssureX SRS requires the team to design, build, test, document, deploy, and demonstrate the complete application. It explicitly requires a Project Report, public GitHub source code, a mandatory `.mp4` demonstration video, a 2,000+ word Technical Blog, AI tool usage declaration, and team contribution record.

The video must demonstrate the end-to-end claim workflow and include valid, invalid, manual-review, tricky-boundary, and model-disagreement cases.

The technical blog must discuss the business problem, architecture, dataset, Python model, Teachable Machine, Claim Summary Card, model comparison, warranty rules, OCR, difficulties, model errors/disagreement cases, testing, security, limitations, lessons learned, and future enhancements.

The source submission is expected to include datasets, model artifacts, card images, mappings, policy/rule files, OCR/document-processing files, tests, sample claims, documentation, screenshots/reports, and configuration as applicable.
