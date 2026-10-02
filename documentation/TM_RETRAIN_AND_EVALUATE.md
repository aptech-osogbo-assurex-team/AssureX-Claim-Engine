# Teachable Machine Finalization Procedure

The repository contains an exported Teachable Machine model from the original
submission. The Claim Summary Card generator has since been corrected to ensure
that the visual card faithfully represents the same underlying claim record used
by the Python model.

Therefore, for a final resubmission, the Teachable Machine model should be
**retrained using the corrected training cards** before its results are reported
as final evidence.

## Training dataset

Use only:

```text
data/claim_cards/train/
```

This contains:

- 1,050 training claims
- 2 visual variations per training claim
- 2,100 training images
- 3 classes

Do not train Teachable Machine on:

```text
data/claim_cards/validation/
data/claim_cards/test/
```

## Validation/test evidence

After training, keep the validation and test folders separate.

Use:

```text
/static/tm_batch_evaluator.html
```

from the running FastAPI application to evaluate the held-out test cards using
the real exported model. The evaluator generates:

```text
tm_test_predictions.csv
```

It does not simulate or fabricate predictions.

## Build the 30+ comparison report

After the test CSV is downloaded, run:

```bash
python scripts/build_model_comparison_report.py \
  --tm-results /path/to/tm_test_predictions.csv \
  --limit 30 \
  --output reports/model_comparison_30.csv
```

The report combines the real Teachable Machine probabilities with the Python
model, warranty rules, missing-document indicators, contradictions, duplicate
indicator, model consistency, and final decision engine output.

## Final evidence requirement

Do not publish a Teachable Machine accuracy number until the actual exported
model has been evaluated on the held-out test cards. Do not reuse a score from
another model or another card-generation version.
