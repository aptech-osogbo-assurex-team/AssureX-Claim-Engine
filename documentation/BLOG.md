# AssureX Claim Engine: Building a Warranty Claim Decision System Around Evidence, Not a Single Prediction

## Introduction

Warranty claims look simple from the outside: a customer reports a fault, submits proof of purchase, and expects the claim to be assessed. In practice, a claim can involve a receipt, warranty card, serial number, product photographs, fault evidence, repair records, dates, warranty conditions, and previous claims. A decision can become difficult when those sources disagree, when mandatory evidence is missing, or when the claim falls close to a policy boundary.

AssureX Claim Engine was designed for that problem. The goal is not merely to train a classifier that says “valid” or “invalid”. The more important engineering question is how to make a claim decision from several pieces of evidence while keeping the process explainable and testable.

Our central design principle became simple:

> **A model prediction is evidence. It is not the entire business decision.**

This principle shaped the architecture of AssureX. A Python tabular classifier provides one model-based assessment. A separately trained Google Teachable Machine image model is intended to provide another assessment from a Claim Summary Card. A configurable warranty and integrity rule engine evaluates business conditions independently. A deterministic decision engine combines the evidence and can route uncertainty or disagreement to manual review.

This article describes the current engineering approach, the dataset, model development, Claim Summary Cards, model comparison, warranty rules, OCR integration, testing, security considerations, difficulties encountered, and the remaining evidence required for the final competition submission.

## The Business Problem

A warranty department does not only need a prediction. It needs an answer that can be explained to a customer, service-centre employee, reviewer, or administrator.

Consider three cases.

In the first case, the product is still within its warranty period, the serial number matches the evidence, the required documents are present, the fault is covered, and there is no duplicate indicator. The models may also agree.

In the second case, the warranty has expired and the claim contains evidence that conflicts with the registered product information. Even a high model confidence should not erase the business evidence.

In the third case, the warranty may still be active, but the two models disagree or a mandatory document is missing. The correct response is not to force a binary result. It is to request manual review.

This is why the AssureX architecture separates prediction from adjudication.

## Architecture: From Claim to Decision

The current architecture follows this flow:

```text
Claim + Supporting Evidence
          |
          +---------------------> Python preprocessing -> Python ML
          |
          +---------------------> Claim Summary Card -> Teachable Machine
          |
          +---------------------> Warranty / Integrity Rules
          |
          +---------------------> Duplicate / Missing / Contradiction Checks
          |
          +---------------------------------------------+
                                                        |
                                                 Evidence comparison
                                                        |
                                                  Decision Engine
                                                        |
                         +-------------------------------+------------------+
                         |                               |                  |
                   Likely Valid                    Likely Invalid    Manual Review
```

The application uses strict Pydantic domain schemas so that products, warranties, claims, documents, repairs, predictions, rule results, and final decisions use a consistent contract. Persistence is provided through SQLite, and audit records preserve important decision information.

The application also includes authentication and claim-ownership checks. This is important because the system is handling evidence that may contain purchase details or personal data.

## Building the Dataset

The current Python dataset contains 1,500 synthetic warranty claims divided among three classes:

- Valid Claim
- Invalid Claim
- Manual Review

The dataset uses a 70/15/15 split. With approximately 500 records per class, each partition contains 350 training, 75 validation, and 75 test records per class.

Synthetic data makes it possible to build and test the system without using real customer information. It also makes it possible to deliberately generate difficult cases such as expired warranties, serial mismatches, contradictions, missing evidence, previous repairs, and different decision classes.

However, synthetic data introduces an important limitation. When generated features are closely tied to the label-generation logic, a model can learn the synthetic rule structure more easily than it would learn a messy real-world distribution. Therefore, we treat the resulting accuracy as a baseline engineering measurement, not proof of real-world generalisation.

The final Teachable Machine dataset must use the same underlying claim records in visual form. The Claim ID must remain mapped between the structured CSV representation and the corresponding card images. The training, validation, and test claims must remain separated so that test claims are not reused in training images.

## Python Model Development

The existing training pipeline compares multiple classical classifiers and selects a Random Forest classifier for the saved artifact.

The current committed model metadata records a held-out test accuracy of 92.889% on the synthetic test partition. The confusion matrix is:

| Actual \ Predicted | Valid | Invalid | Manual Review |
|---|---:|---:|---:|
| Valid Claim | 75 | 0 | 0 |
| Invalid Claim | 0 | 68 | 7 |
| Manual Review | 3 | 6 | 66 |

These results are useful because the confusion matrix shows more than one headline number. In particular, some Invalid Claim cases move into Manual Review and some Manual Review cases are predicted as Invalid Claim or Valid Claim. That is exactly the type of behavior that makes class-wise metrics important.

A five-fold cross-validation procedure has also been added to the training workflow. The actual fold-by-fold values still need to be generated and recorded for the final evidence package. We are deliberately not inserting invented numbers into the report or blog.

## Why the Python Model Does Not Make the Final Decision

A machine-learning model is good at identifying patterns in its feature representation. A warranty policy contains business constraints. Those are different things.

For example, a model may see a pattern that resembles a valid claim, but the policy may say that the claim is outside the reporting window. Another claim may look invalid according to one representation while the supporting documents show a legitimate explanation.

AssureX therefore treats the Python model as one evidence stream. The model is loaded from a saved artifact during claim evaluation. The application does not retrain the model while processing a claim.

The model prediction includes the predicted class, probabilities for all three classes, the model name, model version, and timestamp.

## The Claim Summary Card

One of the most important design details in AssureX is the Claim Summary Card.

The card converts a structured claim into a standardized visual representation containing evidence fields such as:

- product age
- warranty status
- remaining warranty period
- fault category
- repair history count
- receipt or invoice availability
- warranty-card availability
- serial-number status
- missing-document indicators
- damage type where available

The card intentionally excludes the Python model prediction, Python confidence score, and final decision.

This separation matters because the second model should not simply be shown the output of the first model. The purpose of the visual model is to provide an independent assessment of the same underlying claim information in a different representation.

The current card generator is deterministic, reproducible, and supports visual variations for dataset generation.

## Google Teachable Machine

The SRS requires a separately trained Google Teachable Machine image classifier with the same three classes used by the Python model.

The intended workflow is:

```text
Common claim record
      |
      +--> CSV/tabular representation --> Python model
      |
      +--> Evidence-only visual card --> Teachable Machine
```

The browser integration in the application loads the real exported Teachable Machine model and maps its probabilities into the canonical model-prediction contract.

The final trained Teachable Machine artifact is still a required competition step. It must be trained, exported, loaded into the application, and evaluated on unseen claims. We will not simulate this model or manufacture its confidence values.

## Comparing the Two Models

For each claim, AssureX compares:

1. Python predicted class
2. Teachable Machine predicted class
3. whether the classes match
4. the top-class confidence from each model
5. the absolute confidence difference
6. a consistency status

The consistency status can be:

- Strong Match
- Acceptable Match
- Weak Match
- Model Disagreement
- Uncertain Result

The thresholds are configurable. This matters because the comparison policy should be visible and adjustable rather than scattered across application code.

A disagreement is not treated as a problem to hide. It is a signal that the evidence needs additional human attention.

## Warranty and Integrity Rules

The warranty-rule engine is independent of the machine-learning models. Policies are stored in configuration files so that product-category rules can be changed without rewriting the whole adjudication service.

The rules cover areas such as warranty activity and expiry, proof of purchase, required documents, serial-number consistency, product/model consistency, reporting conditions, repairs, excluded damage, and date contradictions.

Examples of contradiction checks include:

- claim date before purchase date
- fault date after claim submission
- repair date before purchase
- conflicting serial numbers
- inconsistent product models

The system also checks missing required documents and duplicate indicators. Uploaded documents receive a SHA-256 hash so that an identical file can be detected if it has already been associated with another claim.

These rules are important because they provide business evidence that is separate from statistical model output.

## The Final Decision Engine

The final decision engine combines the evidence streams into one of three recommendations:

- Likely Valid
- Likely Invalid
- Manual Review Required

A key part of the implementation is the escalation path. Low confidence, model disagreement, weak consistency, missing evidence, contradictions, duplicate indicators, and relevant rule failures can cause manual review instead of forcing a binary result.

The final decision also records reasons, supporting factors, opposing factors, model evidence, rule results, contradictions, missing documents, and duplicate indicators.

That makes it possible to answer a practical reviewer question:

> **Why did the system reach this recommendation?**

Instead of replying that “the AI said so”, the application can show the evidence that contributed to the result.

## OCR and Document Processing

Warranty claims frequently depend on documents. AssureX therefore includes secure document intake and OCR integration.

The document layer validates file size and type, stores the file using a controlled filename, computes a SHA-256 hash, and associates the document with the claim. OCR can use Tesseract for image/PDF text extraction and field parsing.

The final competition demonstration still needs to show realistic documents and the extracted-data verification step required by the SRS. The OCR library alone is not enough; the judges should be able to see where extracted information appears and how it is checked before it becomes decision evidence.

## Authentication, Persistence, and Auditability

The current application includes user registration/login, expiring opaque bearer sessions, claim-ownership checks, and relational persistence using SQLite.

The database stores claim-related records such as products, warranties, documents, repairs, predictions, rule results, decisions, audit entries, and notifications.

This is important for reproducibility. A decision should not disappear when the page is refreshed. The application should preserve the evidence and the result associated with the claim.

Audit records are also part of accountability. Important actions such as evaluation and reviewer actions should remain traceable.

## Testing and Difficulties Encountered

The engineering build currently passes 42 automated tests on the team's Windows environment with Python 3.13.1 and scikit-learn 1.9.1.

The testing process exposed real portability problems that were fixed before the engineering checkpoint was committed.

The first issue was that the Claim Summary Card renderer used a Linux-specific font path. That worked in the development environment but failed on Windows. The fix made font selection environment-aware.

The second issue was OCR availability. A test environment without Tesseract produced a structured OCR-availability error instead of silently pretending that text extraction had succeeded. The Windows environment was then configured to support the OCR path.

These failures were valuable because they demonstrated why “the test suite passed on my machine” is not enough. The project needed to pass in the actual student environment where it would be demonstrated.

Another important limitation surfaced in the model itself: the synthetic dataset can produce strong results without proving real-world generalisation. That led us to focus on the entire decision system, not just on improving the headline accuracy.

## Security Considerations

Security in AssureX includes authentication, claim ownership, password hashing, upload validation, secure file naming, SHA-256 document hashing, persistence rollback, audit records, and controlled error handling.

The final assessment should also include malformed file tests, unauthorized claim access, path traversal attempts, repeated login attempts, duplicate-document behavior, and reviewer privilege boundaries.

A production deployment should also define document retention and deletion policies because warranty evidence can contain personal and purchase information.

## What Still Needs to Be Proven

A strong engineering checkpoint is not the same thing as complete competition evidence. The remaining work is therefore explicit.

First, the team must train and export the actual Teachable Machine model and capture its training, validation, and unseen-test evidence.

Second, the Python five-fold cross-validation results must be generated and recorded rather than merely having the procedure in code.

Third, at least 30 previously unseen claims should be evaluated through the dual-model comparison path and recorded with predictions, confidence values, agreement state, and final decision.

Fourth, the remaining SRS application features—especially dashboards, reporting/export, full notification coverage, monitoring, and the complete status lifecycle—must be tested and documented.

Finally, the demonstration video, technical report, and published technical blog must all describe the actual implementation. Documentation should follow evidence, not the other way around.

## Lessons Learned

The main lesson from AssureX is that building a machine-learning feature and building a decision system are different tasks.

A model can be accurate on a test set and still be the wrong place to put the final decision. The surrounding application has to know when evidence is missing, when models disagree, when a policy is violated, and when a human should review the case.

A second lesson is that reproducibility matters. Pinning the machine-learning runtime version to the version used to create the saved artifact reduces uncertainty around model loading.

A third lesson is that tests are most valuable when they find uncomfortable problems. The Windows font issue and Tesseract availability issue were not theoretical. They were concrete failures discovered before the engineering checkpoint was considered safe.

A fourth lesson is that synthetic evaluation must be interpreted carefully. Strong results can be useful while still being limited by the synthetic data distribution.

## Conclusion

AssureX is being built as an evidence-driven warranty claim decision system rather than a single-model demo.

The current engineering checkpoint has a working Python classification path, canonical domain contracts, configurable rules, persistence, authentication, document intake, Claim Summary Card generation, model comparison logic, audit records, reviewer foundations, and 42 passing automated tests.

The remaining work is not to make the project sound more complete than it is. The remaining work is to produce the actual Teachable Machine evidence, complete the high-value SRS workflows, demonstrate unseen cases, and then make the report, blog, and video mirror the verified system.

That discipline is important because the strongest claim AssureX can make is not that the AI is infallible. It is that the system knows how to combine evidence, detect uncertainty, explain its recommendation, and involve a human when the automated evidence is not sufficient.

---

## Final publication checklist

Before publishing this article, replace the following placeholders only with verified evidence:

- `[INSERT FINAL CROSS-VALIDATION METRICS]`
- `[INSERT FINAL TEACHABLE MACHINE RESULTS]`
- `[INSERT 30+ UNSEEN CLAIM COMPARISON SUMMARY]`
- `[INSERT FINAL SCREENSHOTS]`
- `[INSERT DEPLOYMENT DETAILS]`
- `[INSERT FINAL BLOG / VIDEO LINKS]`
