# AssureX Demonstration Video — Final Shot List

This document is the recording blueprint for the mandatory `.mp4` demonstration.
Record only functionality that is actually working in the final resubmission.

## 1. Opening — 10 to 20 seconds

Show the AssureX title screen.

Narration:

> “AssureX combines structured claim evidence, two independent AI assessments,
warranty rules and explainable human review into one warranty-claim decision
pipeline.”

## 2. Login / registration

Show:

- customer registration or login;
- authenticated state.

## 3. Product and warranty

Show:

- product registration;
- warranty record;
- warranty start/end information.

## 4. Claim creation

Show:

- claim ID;
- product link;
- fault description/category;
- claim submission information.

## 5. Evidence upload

Show:

- receipt/invoice;
- warranty card;
- product image;
- serial evidence;
- fault evidence.

## 6. OCR extraction

Show a real document being processed.

Show the extracted values.

Then show the verification/correction step where available.

Do not claim OCR succeeded if the local Tesseract installation is unavailable.

## 7. Data preprocessing

Show the transition from claim data to the feature/evidence representation.

Explain that preprocessing produces derived fields used by the Python model and
rules.

## 8. Claim Summary Card

Show the generated card.

Important visual check:

The card must show evidence only. Do **not** show model outputs or final decision
inside the card itself.

## 9. Python model

Show:

- predicted class;
- Valid Claim probability;
- Invalid Claim probability;
- Manual Review probability;
- model version.

## 10. Teachable Machine

Show the real exported model running on the Claim Summary Card.

Show:

- predicted class;
- Valid Claim probability;
- Invalid Claim probability;
- Manual Review probability.

## 11. Model comparison

Show:

- Python class;
- Teachable Machine class;
- prediction match or mismatch;
- confidence difference;
- consistency status.

## 12. Warranty rules

Show the rule results.

At least one rule should visibly pass.
If a negative case is being demonstrated, show the failed rule and explain why.

## 13. Missing documents

Show a case where a required document is missing.

The application should clearly identify the missing evidence.

## 14. Contradiction detection

Use a controlled synthetic case such as:

- claim date before purchase;
- repair date before purchase; or
- conflicting serial/model evidence.

Show the rule result.

## 15. Duplicate claim

Show a controlled duplicate indicator or duplicate document hash.

Explain that the duplicate signal contributes to escalation rather than being
silently ignored.

## 16. Final decision

Show the deterministic final result and its explanation.

Do not say that the AI alone “approved” the claim. Explain that the result comes
from the combined model, rule and consistency evidence.

## 17. Manual review

Show:

- manual-review routing;
- reviewer comments;
- reviewer approval/rejection or request for information;
- retained original automated evidence.

## 18. Claim status

Show the claim moving through its relevant status states.

## 19. Administrator / reporting evidence

Only show dashboard, analytics or report-generation features that are actually
implemented and working in the final build.

## 20. Required demonstration scenarios

The SRS requires the final recording to include:

### Valid claim

Complete evidence and a valid warranty/business scenario.

### Invalid claim

Clearly invalid warranty or evidence condition.

### Manual-review claim

A genuine uncertainty/escalation case.

### Tricky boundary case

A claim at or near the configured warranty/reporting boundary.

### Model-disagreement case

Python and Teachable Machine actually predict different classes.
Show the confidence values and manual-review routing.

## 21. Closing

Narration:

> “AssureX does not treat machine learning as the entire warranty decision. It
combines independent model evidence with business rules, integrity checks and
human review so that each recommendation has a traceable reason.”

## Final recording checklist

- [ ] No passwords or secrets visible
- [ ] Only synthetic/approved demonstration data used
- [ ] Real Teachable Machine model shown
- [ ] No fabricated confidence values
- [ ] All five required scenario types demonstrated
- [ ] Card contains no model output or final decision
- [ ] Manual review path shown
- [x] Final demonstration recording exists — 1085.767 seconds, 204814629 bytes
- [ ] Video link added to repository documentation — pending public video URL
