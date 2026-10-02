# AssureX Claim Engine

AssureX is an AI-assisted warranty claim validation system for the Aptech TechWiz 7 **NextWave AI and ML** category.

The system is designed around a decision pipeline rather than a single model:

```text
Claim evidence
     │
     ├── Python tabular model ───────┐
     │                                │
     └── Claim Summary Card           ├── Evidence comparison
             │                        │
             └── Teachable Machine ───┘
                                      │
                    Warranty / integrity rules
                                      │
                              Final adjudication
                                      │
               Likely Valid / Likely Invalid / Manual Review
```

## Public Project Page

[AssureX Claim Engine on GitHub Pages](https://aptech-osogbo-assurex-team.github.io/AssureX-Claim-Engine/)

## Current implementation

The repository currently contains verified implementations for:

- strict Pydantic domain schemas for products, warranties, claims, documents, repairs, model predictions and final decisions;
- configurable warranty/integrity rules in JSON;
- deterministic model-comparison and final-decision logic;
- the saved Random Forest inference artifact and model metadata;
- SQLite persistence for users, products, warranties, claims, documents, repairs, predictions, rule results, decisions, audit logs and notifications;
- password hashing and expiring opaque bearer sessions;
- secure document storage with size/type checks and SHA-256 hashing;
- OCR extraction using Tesseract/PDF conversion with structured field parsing;
- evidence-only Claim Summary Card generation;
- a browser path that loads a real exported Google Teachable Machine image model and sends its real probabilities to the backend;
- FastAPI health, authentication, claim registration, document upload, card rendering and claim evaluation endpoints;
- automated tests covering the current implemented path.

## Model baseline

`data/claims.csv` contains 1,500 synthetic claims with three classes and the required 70/15/15 split.

The committed Random Forest artifact currently records **92.89% held-out test accuracy** on the synthetic test split. This is a repository verification result, not evidence of real-world generalisation.

The application loads the saved model; it does not retrain during claim evaluation.

## Run locally

Create a virtual environment and install the runtime dependencies:

```bash
python -m venv .venv
# Windows
.venv\\Scripts\\activate
# Linux/macOS
# source .venv/bin/activate

pip install -r requirements.txt
```

Run the application:

```bash
python -m uvicorn src.api:app --reload
```

Open `http://127.0.0.1:8000/`.

The UI supports registration/login, claim JSON loading, Claim Summary Card rendering, Teachable Machine model loading and end-to-end evaluation.

## Teachable Machine model

Export the independently trained **image** model from Google Teachable Machine and place its exported files under:

```text
static/teachable_machine/
    model.json
    metadata.json
    *.bin
```

The three class labels must correspond to:

- `Valid Claim`
- `Invalid Claim`
- `Manual Review`

The card sent to Teachable Machine contains evidence only. Model predictions, confidence values and the final decision are not rendered on the card.

The browser maps the actual Teachable Machine probabilities into the canonical model-prediction contract and sends them to `/api/claims/evaluate`.

## Tests

Run:

```bash
python -m pytest -q
```

The hardened repository test suite contains 45 automated tests. The saved Python artifact was trained under scikit-learn 1.9.1, and `requirements.txt` pins scikit-learn to 1.9.1 for reproduction.

## Important engineering rule

AssureX does not hard-code a claim outcome or fabricate a Teachable Machine prediction. The final decision is derived from model evidence, configured rules, contradictions, document completeness and consistency checks.

## AI-assisted development

AI-assisted development is disclosed in [`AI_USAGE.md`](AI_USAGE.md). AI-generated changes are expected to be reviewed, executed, tested and understood by the team before submission.

## Competition status

The current build is a real implementation baseline, not a claim that every SRS feature is complete. Core resubmission evidence has been verified, including corrected Claim Summary Cards, the Python model evaluation, Teachable Machine Model A evaluation, model comparison evidence, submission validation and automated tests. Remaining competition work is limited to final presentation/submission items and any broader workflow features explicitly required by the competition.

## Resubmission evidence

- [Project Report](documentation/PROJECT_REPORT.md)
- [Technical Blog](documentation/BLOG.md)
- [Video Shot List](documentation/VIDEO_SHOT_LIST.md)
- [Submission Checklist](documentation/SUBMISSION_CHECKLIST.md)
- [TM Retraining and Evaluation](documentation/TM_RETRAIN_AND_EVALUATE.md)
- [Python Model Evaluation](reports/python_model_evaluation.md)
- [Card Fidelity Audit](reports/card_fidelity_audit.md)
