# AssureX Dataset Statistics

## Common dataset

| Measure | Value |
|---|---:|
| Total claims | 1,500 |
| Valid Claim | 500 |
| Invalid Claim | 500 |
| Manual Review | 500 |
| Training claims | 1,050 |
| Validation claims | 225 |
| Testing claims | 225 |

## Stratified class split

| Split | Valid Claim | Invalid Claim | Manual Review | Total |
|---|---:|---:|---:|---:|
| Training | 350 | 350 | 350 | 1,050 |
| Validation | 75 | 75 | 75 | 225 |
| Testing | 75 | 75 | 75 | 225 |

The split is claim-level. All visual variations of a training claim remain in
training, while validation and test claims are kept out of training images.

## Card corpus

| Split | Claims | Cards per claim | Images |
|---|---:|---:|---:|
| Training | 1,050 | 2 | 2,100 |
| Validation | 225 | 1 | 225 |
| Testing | 225 | 1 | 225 |
| **Total** | **1,500** | — | **2,550** |

The card generator now reconstructs the document and repair-history evidence
represented by each CSV row before rendering its card. The generated integrity
audit reports zero card-data field mismatches across all 1,500 claims.
