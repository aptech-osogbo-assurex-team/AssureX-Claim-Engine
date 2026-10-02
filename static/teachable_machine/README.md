# Google Teachable Machine model

The application expects an independently trained Google Teachable Machine **image**
model in this directory:

- `model.json`
- `metadata.json`
- the referenced `.bin` weights

Expected classes:

- `Valid Claim`
- `Invalid Claim`
- `Manual Review`

## Resubmission integrity requirement

The original submission model is retained here as a reference artifact. The
Claim Summary Card generator has since been corrected so that cards preserve the
same claim evidence represented in the structured dataset.

Before final resubmission, replace the model files in this directory with a new
export trained on the corrected training cards:

```text
data/claim_cards/train/
```

Do not train on the validation or test folders.

After replacement, use:

```text
/static/tm_batch_evaluator.html
```

to generate real predictions for the held-out test cards. Never insert hard-coded
predictions or fabricated confidence values.
