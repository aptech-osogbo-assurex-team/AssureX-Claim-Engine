# AssureX Final Submission Checklist

This checklist separates what is already verified from what must still be
completed before a final resubmission.

## Code and repository

- [x] Public GitHub repository
- [x] Python/FastAPI application source
- [x] Model artifact
- [x] Warranty rules/policies
- [x] OCR/document-processing code
- [x] Claim Summary Card generator
- [x] Automated tests
- [x] AI_USAGE.md
- [x] Documentation directory

## Dataset

- [x] 1,500 common claim records
- [x] 70/15/15 claim-level split
- [x] Train/validation/test CSV files generated
- [x] 2,100 training card images
- [x] 225 validation card images
- [x] 225 test card images
- [x] Claim ID → card filename mapping
- [x] Dataset statistics
- [x] Data dictionary
- [x] Card fidelity audit: 0 mismatches

## Python model

- [x] Multiple algorithms compared
- [x] Random Forest selected from validation performance
- [x] Held-out test accuracy: 92.89% on the synthetic test split
- [x] Class-wise precision/recall/F1 recorded
- [x] Confusion matrix recorded
- [x] Five-fold CV procedure/results recorded in the model metrics artifact
- [ ] Re-run final training under the declared scikit-learn runtime if the model artifact is replaced

## Teachable Machine

- [x] Retained Teachable Machine Model A export exists
- [x] Three required classes
- [x] Browser integration exists
- [x] Retrained on corrected Claim Summary Cards
- [x] Evaluated the corrected exported model on the held-out test cards — 191/225 correct (84.8889%)
- [ ] Achieve at least 85% unseen-test accuracy — measured result is 84.8889% (191/225), gap 0.1111 percentage points; report transparently
- [x] Preserve training/validation/test evidence

## Model comparison

- [x] Comparison logic exists
- [x] Confidence-difference calculation exists
- [x] Consistency-status logic exists
- [x] Generate actual 30+ unseen-claim comparison report using the corrected TM model — 30 cases, 25/30 prediction agreement (83.33%)
- [x] Preserve major disagreement explanations

## Warranty policies

- [x] Active combined warranty policy
- [x] Electronics standalone policy
- [x] Home-appliance standalone policy
- [x] Default standalone policy

## Final demonstration and documentation

- [ ] Final application walkthrough
- [ ] Required valid claim case
- [ ] Required invalid claim case
- [ ] Required manual-review case
- [ ] Required tricky boundary case
- [ ] Required model-disagreement case
- [ ] Final screenshots/evidence
- [x] Final Project Report update — final TM evaluation and documented 0.1111 percentage-point SRS gap
- [x] Final 2,000+ word blog update and external publication — GitHub Pages: https://aptech-osogbo-assurex-team.github.io/AssureX-Claim-Engine/
- [x] Final .mp4 demonstration recording
- [x] Blog link added to repository documentation — GitHub Pages URL above
- [ ] Video link added to repository documentation — pending public video URL
- [ ] Final clean submission archive
