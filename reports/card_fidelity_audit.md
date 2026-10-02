# Claim Summary Card Fidelity Audit

**Result: PASS**

The card-generation pipeline was corrected so Claim Summary Cards are generated
from the same claim record represented in `data/claims.csv`.

The audit checks the fields displayed on the card, including:

- product age
- warranty status
- remaining warranty
- fault category
- repair-history count
- receipt/invoice availability
- warranty-card availability
- serial-number match
- missing-document list

## Verification

- Claims checked: **1,500**
- Card images generated: **2,550**
- Training images: **2,100**
- Validation images: **225**
- Test images: **225**
- Field mismatches: **0**

See `reports/card_fidelity_audit.json`, `reports/card_data_manifest.csv`, and
`reports/card_mapping.csv` for machine-readable evidence.

The Claim Summary Card remains evidence-only and does not contain the Python
prediction, Python confidence, Teachable Machine prediction, or final decision.
