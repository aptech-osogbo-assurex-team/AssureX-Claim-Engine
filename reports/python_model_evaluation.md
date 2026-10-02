# Python Model Evaluation

**Model:** RandomForest
**Training / validation / test:** 1050 / 225 / 225
**Held-out test accuracy:** 0.9289
**5-fold CV mean:** 0.9076
**5-fold CV standard deviation:** 0.0172

## Class-wise metrics

| Class | Precision | Recall | F1 | Support |
|---|---:|---:|---:|---:|
| Valid Claim | 0.9615 | 1.0000 | 0.9804 | 75 |
| Invalid Claim | 0.9189 | 0.9067 | 0.9128 | 75 |
| Manual Review | 0.9041 | 0.8800 | 0.8919 | 75 |

## Confusion matrix

| Actual \ Predicted | Valid Claim | Invalid Claim | Manual Review |
|---|---:|---:|---:|
| Valid Claim | 75 | 0 | 0 |
| Invalid Claim | 0 | 68 | 7 |
| Manual Review | 3 | 6 | 66 |

## Evidence note

The score is measured on the held-out synthetic test split. It is not presented as evidence of real-world production generalisation.
