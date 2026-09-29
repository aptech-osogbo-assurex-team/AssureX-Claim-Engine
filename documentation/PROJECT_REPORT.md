# AssureX Claim Engine — Technical Report

> **Document status:** Working submission draft
>
> **Important:** This report distinguishes implemented and verified functionality from requirements that are still pending verification. Do not replace `TBD` or `PENDING EVIDENCE` entries with guessed values. Update them only after the team produces the corresponding test result, screenshot, metric, or demonstration evidence.

## 1. Executive Summary

AssureX is an AI-assisted warranty claim validation system designed to support structured claim intake, evidence processing, independent machine-learning assessment, warranty-rule validation, model comparison, explainable adjudication, and human review.

The current engineering checkpoint moves the project beyond a standalone classifier into a decision pipeline. The Python classification model provides one evidence source. A separately trained Google Teachable Machine image model is intended to provide an independent second evidence source from a Claim Summary Card. Configurable warranty and integrity rules provide business evidence. A deterministic decision engine combines these signals and can route uncertain or conflicting cases to manual review.

The current verified machine-learning baseline uses 1,500 synthetic claim records across three classes: Valid Claim, Invalid Claim, and Manual Review. The saved Random Forest artifact records 92.889% held-out test accuracy on the synthetic test split. The application currently has 42 passing automated tests in the team's Python 3.13.1 / scikit-learn 1.9.1 environment.

The current checkpoint is not presented as proof that every SRS requirement is complete. The most important remaining evidence includes the independently trained Teachable Machine model, its training/validation/test evidence, actual five-fold cross-validation results, 30+ unseen dual-model comparisons, complete dashboard/reporting flows, monitoring, and the final demonstration/submission evidence.

## 2. Problem Definition

Warranty claim processing can require customers or service-centre staff to submit receipts, warranty cards, serial-number evidence, fault evidence, repair information, and other supporting documents. Manual assessment can be slowed by missing documents, conflicting dates, inconsistent product identifiers, duplicate evidence, unclear warranty status, and high case volume.

The AssureX problem is therefore not simply to predict whether a claim looks valid. The system must combine claim evidence, business warranty conditions, document completeness, integrity checks, and independent model assessments into a traceable recommendation.

## 3. Background and Business Necessity

A practical warranty workflow must answer at least four questions:

1. Is the submitted evidence internally consistent?
2. Is the product and warranty information compatible with the claim?
3. What do the independent machine-learning models predict?
4. Is there enough agreement and evidence to make a recommendation, or should the case be reviewed by a human?

AssureX addresses these questions through a layered decision pipeline rather than treating a single model probability as the final business decision.

## 4. Proposed Solution

The proposed architecture is:

```text
Claim + Evidence
      |
      +--> Python preprocessing / tabular features --> Python classifier
      |
      +--> Evidence-only Claim Summary Card -------> Google Teachable Machine
      |
      +--> Warranty / integrity rules
      |
      +--> Duplicate / missing-document / contradiction checks
      |
      +------------------------------+
                                     |
                          Evidence comparison
                                     |
                              Decision Engine
                                     |
                 +-------------------+-------------------+
                 |                   |                   |
           Likely Valid       Likely Invalid      Manual Review
```

The core design principle is:

> **Model prediction is evidence, not the entire decision.**

The final adjudication is deterministic application logic. It does not call an external generative-AI service to decide whether a claim should be valid or invalid.

## 5. Purpose of this Document

This document records the problem, requirements, architecture, modules, data design, machine-learning approach, decision logic, testing strategy, security and privacy considerations, limitations, and outstanding evidence required for the final AssureX submission.

## 6. Scope

### 6.1 In scope

- User authentication and claim ownership
- Product and warranty data structures
- Claim registration
- Supporting-document intake
- File integrity hashing
- OCR extraction integration
- Canonical claim schemas
- Python ML inference from the saved model
- Evidence-only Claim Summary Card generation
- Google Teachable Machine browser integration
- Warranty and integrity rules
- Model comparison and consistency status
- Final deterministic adjudication
- Duplicate detection
- Manual review and reviewer override foundations
- Persistence and audit records
- Automated tests

### 6.2 Out of scope or pending final verification

- Production-scale monitoring
- Full administrator analytics and export suite
- Complete notification catalogue required by the SRS
- Final deployment proof
- Final Teachable Machine training artefact and evaluation evidence
- Complete hidden-claim evaluation

## 7. Assumptions

- The competition dataset may be synthetic, provided it meets the SRS requirements and is documented transparently.
- The Python model artifact is treated as immutable during claim evaluation.
- Teachable Machine is independently trained from Claim Summary Card images generated from the same underlying claim records.
- Configurable warranty policies are authoritative for rule evaluation.
- Human review remains necessary for uncertain, conflicting, incomplete, duplicated, or otherwise escalated claims.

## 8. Constraints

- The SRS requires two independently assessed representations of the same underlying claim data.
- The final claim decision must be produced by team application logic using the Python model, Google Teachable Machine model, warranty rules, and application logic.
- The solution must remain explainable to the student team during judging.
- AI-assisted development must be disclosed and independently reviewed and tested.

## 9. Functional Requirements Traceability

Status labels:

- **Implemented:** present in the current engineering checkpoint and covered by tests or direct inspection.
- **Partial:** some supporting infrastructure exists, but the full SRS behavior is not yet demonstrated.
- **Pending:** not yet implemented or not yet evidenced.

| SRS area | Requirement summary | Status | Current evidence / gap |
|---|---|---|---|
| Authentication | User registration/login | Implemented | FastAPI auth endpoints and tests |
| Product/warranty | Product and warranty structures | Partial | Domain and persistence models exist; complete registration workflow still needs final UI/demo verification |
| Documents | Receipt/invoice/warranty/evidence upload | Partial | Secure upload and document model exist; full document lifecycle is not complete |
| OCR | Extract purchase and product fields | Partial | Tesseract/PDF conversion integration exists; extraction coverage must be demonstrated on representative documents |
| Verification | User reviews/corrects extracted data | Pending | Not yet demonstrated as a complete UI workflow |
| Warranty tracking | Calculate/display warranty state | Partial | Rule/card logic exists; complete user-facing tracking still required |
| Expiry alerts | Configurable expiry notifications | Pending | Notification infrastructure exists, but expiry-trigger workflow is not complete |
| Claim registration | Unique claim linked to user/product/warranty/docs | Implemented | Authenticated claim registration and persistence |
| Claim information | Product age, dates, fault, history, replacement, etc. | Partial | Canonical schemas and persistence cover many fields; final UI collection needs verification |
| Repair history | Repair details and authorization | Partial | Domain/persistence/rule support exists; full management UI is pending |
| Document organization | View/download/replace/remove | Pending | Storage exists; complete lifecycle endpoints are pending |
| Data validation | Required fields, file limits/types, duplicate IDs | Implemented/Partial | Pydantic and upload validation exist; full UX validation matrix remains |
| Preprocessing | Missing values, dates, encoding, normalization, derived fields | Partial | Training pipeline and canonical processing exist; final SRS evidence needs explicit preprocessing report |
| Common dataset | Same underlying records for CSV and cards | Partial | Card generator maps claim records; final mapping/evidence package is pending |
| Python classifier | Compare algorithms and select model | Implemented | Existing baseline compares multiple classifiers and saves Random Forest |
| Python confidence | All three class probabilities | Implemented | Inference adapter exposes probabilities |
| Claim Summary Card | Evidence-only standardized visual card | Implemented | Deterministic renderer; cards contain no prediction/decision |
| Teachable Machine | Separate image classifier with 3 classes | Partial | Browser integration exists; exported trained artifact is still required |
| Model comparison | Compare predicted classes | Implemented | Decision engine computes agreement |
| Confidence comparison | Absolute top-class confidence difference | Implemented | Decision engine computes difference |
| Consistency status | Strong/Acceptable/Weak/Disagreement/Uncertain | Implemented | Configurable thresholds in policy |
| Warranty rules | Expiry, coverage, reporting, purchase, serial, repairs, exclusions, documents | Partial | Rule engine has broad support; final SRS coverage audit still required |
| Configurable policies | Category-specific rules in config | Implemented | JSON warranty-policy support |
| Serial verification | Compare serials across evidence | Partial | Rule engine and extracted-value helpers exist; complete evidence sources need final demonstration |
| Contradiction detection | Date/model/serial consistency checks | Implemented/Partial | Rule engine supports key contradiction checks; full document-driven path pending |
| Missing documents | Detect and explain missing mandatory evidence | Implemented/Partial | Rule engine/evaluation service support; full user guidance is pending |
| Duplicate claims | Compare claim/document/product indicators | Implemented | Evaluation service checks claim/document indicators |
| Document duplicates | SHA-256 document hashing | Implemented | Secure document hash stored and checked |
| AI-generated claim summary | Human-readable claim summary | Partial | Evidence-only visual card exists; narrative summary workflow is not complete |
| Claim preparation assistance | Show missing info, docs, deadlines, contradictions and actions | Pending | Not yet demonstrated as complete pre-submission assistant |
| Final claim decision | Combine models, rules, contradictions, duplicates, confidence | Implemented | Deterministic decision engine |
| Decision explanation | Supporting/opposing factors and reasons | Implemented | FinalDecision contains explainable evidence and reasons |
| Manual review | Queue escalated claims and reviewer action | Partial | Review endpoint/override foundation exists; full queue and additional-information flow pending |
| Reviewer override | Comments and auditable override | Implemented/Partial | Override is persisted; complete reviewer UI is pending |
| Status tracking | Draft → Submitted → Evaluation/Info/Review → outcome → Closed | Partial | Status persistence exists, but complete lifecycle needs implementation/verification |
| Notifications | Submission/docs/status/review/decision/expiry alerts | Partial | Notification persistence exists; full trigger catalogue pending |
| User dashboard | Products, warranties, claims, pending actions | Pending | Not complete |
| Admin dashboard | Counts, disagreements, trends, confidence etc. | Pending | Not complete |
| Search/filtering | Claim/product/status/confidence/reviewer/date filters | Pending | Not complete |
| Analytics/reporting | Outcome, faults, reasons, expirations, model performance | Pending | Not complete |
| Downloadable claim report | Full evidence and decision report | Pending | Not complete |
| Data export | CSV/Excel compatible export | Pending | Not complete |
| Database | Secure relational/NoSQL store | Implemented | SQLite persistence models exist |
| Audit trail | Record important actions and decisions | Implemented | AuditLog persistence exists |
| Model versioning | Link predictions to model versions | Implemented | Prediction records and metadata |
| Error handling | Friendly errors without technical leakage | Partial | API/error handling exists; final UX review pending |
| Monitoring | Upload/login/duplicate/model/anomaly alerts | Pending | Not complete |
| Responsive web UI | Customer/reviewer/admin workflows | Partial | Browser application foundation exists; complete role dashboards are pending |

## 10. Non-Functional Requirements Traceability

| Requirement | Status | Evidence / next evidence |
|---|---|---|
| Performance: prediction within 5 seconds under normal operation | Pending | Benchmark on the final deployed environment |
| Scalability: at least 10,000 claims | Pending | Persistence/load test evidence |
| Usability | Partial | Browser UI exists; full role-based usability walkthrough pending |
| Accuracy: at least 85% on unseen claims for both models | Partial | Python held-out synthetic accuracy is 92.889%; Teachable Machine unseen accuracy is pending |
| Availability: 99% uptime during business hours | Pending | Deployment/availability evidence |

## 11. System Architecture

### 11.1 Application layers

1. **Interface layer** — browser-facing HTML/JavaScript and FastAPI endpoints.
2. **Domain layer** — strict Pydantic schemas and enums.
3. **Application services** — registration, evaluation, document handling.
4. **Evidence layer** — OCR, hashing, Claim Summary Card generation.
5. **Model layer** — saved Python model inference and Teachable Machine integration.
6. **Rules layer** — configurable warranty and integrity policy evaluation.
7. **Decision layer** — deterministic model comparison and final adjudication.
8. **Persistence layer** — relational records for claims, documents, predictions, rule results, decisions, audit entries and notifications.

### 11.2 Decision boundary

The decision engine receives already-computed evidence. It does not train models, generate fabricated confidence values, or call a generative model to decide the claim.

## 12. Module Descriptions

### 12.1 Domain schemas

The domain layer defines stable contracts for products, warranties, claims, documents, repairs, model predictions, rule results, decision evidence, and final decisions.

### 12.2 Authentication

Users authenticate through registration/login. Passwords are stored as hashes and sessions use opaque bearer tokens with expiration.

### 12.3 Persistence

SQLite provides the current relational store. The schema includes users, sessions, products, warranties, claims, documents, repairs, predictions, rule results, decisions, audit logs and notifications.

### 12.4 Document intake

Uploaded documents are validated for supported type and size, assigned secure stored names, hashed with SHA-256, and associated with the relevant claim.

### 12.5 OCR

OCR uses Tesseract integration with PDF/image handling. The deployment environment must have the OCR executable installed and configured.

### 12.6 Claim Summary Card

The card is generated deterministically from evidence-only fields such as product age, warranty status, fault type, repair history, document availability, and serial-number status. It intentionally excludes model predictions, confidence scores, and the final decision.

### 12.7 Python model inference

The application loads `model/classifier.joblib` and predicts the three canonical classes. Claim evaluation does not retrain the model.

### 12.8 Warranty and integrity rules

Rules are loaded from JSON policy files and check warranty dates, proof/evidence conditions, serial consistency, contradictions, document completeness, duplicates, repairs, exclusions and related integrity constraints.

### 12.9 Decision engine

The engine computes model agreement, confidence difference and consistency status, then considers rule failures, contradictions, missing documents and duplicate indicators. Escalation produces `Manual Review Required` rather than hiding uncertainty.

### 12.10 Manual review

Escalated claims can be reviewed by an authorized user. Reviewer comments and override state are persisted.

## 13. Database Design

Current persistence entities:

```text
User
  └── Session

User
  └── Product
        └── Warranty
        └── Repair

Claim
  ├── Documents
  ├── Predictions
  ├── Rule Results
  ├── Decision
  ├── Audit Logs
  └── Notifications
```

The final report must add the database ER diagram and data dictionary as actual figures/appendices.

## 14. Data Dictionary

| Entity | Key fields | Purpose |
|---|---|---|
| User | user_id, email, password_hash | Customer/reviewer identity |
| Session | token hash, expiry, user_id | Authenticated session state |
| Product | product_id, serial_number, category, purchase_date | Registered product |
| Warranty | warranty_id, start/end, policy fields | Warranty coverage |
| Claim | claim_id, product_id, warranty_id, fault fields, status | Claim case |
| Document | document_id, claim_id, type, sha256, extracted_data | Evidence file |
| Repair | repair_id, product_id, repair_date, authorization | Service history |
| Prediction | claim_id, model_name/version, class, probability map | Model evidence |
| RuleResult | claim_id, rule_id, pass/fail, severity, message | Business/integrity evidence |
| Decision | claim_id, outcome, reasons, evidence, reviewer data | Final adjudication |
| AuditLog | action, user_id, claim_id, details, timestamp | Accountability |
| Notification | user_id, claim_id, type, message, read state | User alerts |

## 15. Data and Dataset Design

The current Python dataset contains 1,500 synthetic claim records across three classes with a 70/15/15 split. This corresponds to 350/75/75 records per class in each partition.

The committed Python model is a Random Forest classifier. The baseline held-out test accuracy recorded in model metadata is 0.928889 (92.889%).

### 15.1 Important limitation

The dataset is synthetic and some generated features are closely tied to the generated class logic. Therefore, the test result is evidence that the model works on the defined synthetic distribution; it is not evidence of real-world warranty-claim generalisation.

### 15.2 Required final dataset package

The SRS requires:

- structured CSV training, validation and test datasets;
- Claim Summary Card training, validation and test images;
- generation scripts;
- scenario definitions;
- labels and statistics;
- data dictionary;
- Claim ID ↔ image filename mapping;
- strict separation between training and validation/test claims.

**Final evidence status:** PENDING.

## 16. Python Classification Model

### 16.1 Algorithms compared

The existing training pipeline compares multiple classical classifiers and selects Random Forest for the committed artifact.

### 16.2 Evaluation

Verified baseline:

```text
Dataset size:           1,500 synthetic claims
Classes:                Valid Claim / Invalid Claim / Manual Review
Split:                  70 / 15 / 15
Held-out test accuracy: 92.889%
```

### 16.3 Held-out confusion matrix

| Actual \ Predicted | Valid | Invalid | Manual Review |
|---|---:|---:|---:|
| Valid Claim | 75 | 0 | 0 |
| Invalid Claim | 0 | 68 | 7 |
| Manual Review | 3 | 6 | 66 |

### 16.4 Pending metric evidence

- Five-fold cross-validation fold scores: **PENDING**
- Mean and standard deviation: **PENDING**
- Final precision/recall/F1 report: **PENDING final evidence table**
- Final hidden/unseen evaluation: **PENDING**

## 17. Google Teachable Machine Model

The application includes a browser integration for a separately trained Teachable Machine image model. The required class labels are:

- Valid Claim
- Invalid Claim
- Manual Review

The model input is a Claim Summary Card containing evidence only. The card must not render Python predictions, confidence scores or final decisions.

### 17.1 Pending evidence

- exported `model.json`
- `metadata.json`
- weight files
- training image counts
- validation/test image counts
- training settings
- unseen accuracy
- class-wise metrics
- representative predictions
- 30+ common-claim comparison table

## 18. Model Prediction and Confidence Comparison

For each evaluated claim, AssureX records:

- Python predicted class
- Python probabilities
- Teachable Machine predicted class
- Teachable Machine probabilities
- whether predicted classes match
- absolute difference between top-class confidence scores
- consistency status

The consistency policy supports:

```text
Strong Match
Acceptable Match
Weak Match
Model Disagreement
Uncertain Result
```

Thresholds are configurable rather than embedded throughout the application.

## 19. Warranty Rule Engine

Warranty policies are externalized in JSON so that important policy values can be modified without rewriting the adjudication algorithm.

The rule engine covers categories of checks including:

- warranty activity and expiry
- proof-of-purchase requirements
- required documents
- serial-number consistency
- product/model consistency
- claim/fault/repair date contradictions
- reporting conditions
- repair authorization
- excluded damage/fault conditions
- duplicate indicators

The final submission must demonstrate the exact policies used for each supported product category and include at least one surprise-modification exercise.

## 20. Final Decision Logic

The final decision is one of:

- **Likely Valid**
- **Likely Invalid**
- **Manual Review Required**

The decision engine deliberately escalates cases with uncertain model consistency, model disagreement, weak matching, manual-review predictions, critical/warning rule failures, contradictions, missing evidence, or duplicate indicators.

### 20.1 Decision explanation

The final decision retains supporting factors, opposing factors, rule results, model evidence, and escalation reasons so a reviewer can understand why the recommendation was made.

## 21. Testing Strategy

The current automated test suite contains 42 passing tests in the verified student environment.

The test suite covers:

- domain schema validation
- API flows
- card rendering
- rule engine behavior
- decision engine behavior
- ML inference
- document handling
- authentication and ownership
- persistence paths

### 21.1 Final adversarial test matrix

| Scenario | Expected behavior |
|---|---|
| Valid in-warranty claim with complete evidence | Likely Valid when model/rules support it |
| Expired warranty | Rule evidence should oppose validity and may trigger review/rejection according to policy |
| Missing mandatory document | Missing-document flag + manual review/escalation |
| Serial mismatch | Integrity warning/escalation |
| Contradictory dates | Contradiction flag + escalation |
| Duplicate claim | Duplicate flag + escalation |
| Unauthorized repair | Rule result according to policy |
| Boundary date | Explicit policy evaluation |
| Low-confidence model | Uncertain result / manual review |
| Model disagreement | Manual review |
| Reviewer override | Persisted override and audit entry |

## 22. Security Considerations

Current controls include:

- password hashing
- expiring opaque sessions
- authenticated claim access
- claim ownership checks
- upload size/type validation
- secure generated storage names
- SHA-256 document hashes
- persistence rollback on failure
- audit records
- no external generative-AI API used for the final claim decision

Remaining security verification should include:

- malformed/oversized files
- path traversal attempts
- unsupported content types
- repeated login attempts
- unauthorized claim access
- duplicate documents across users
- malformed model payloads
- reviewer privilege boundaries

## 23. Privacy Considerations

Claim documents can contain personal and purchase information. The implementation should therefore minimize stored data to what is necessary for evaluation, protect access through authentication and ownership checks, avoid exposing document contents through error messages, and maintain auditable access/decision records.

A production deployment should additionally define retention and deletion policies before handling real customer documents.

## 24. Performance Considerations

The SRS requires claim processing and both model predictions within five seconds under normal operating conditions. A final benchmark must measure the complete path rather than individual functions:

```text
request
→ persistence
→ preprocessing
→ Python inference
→ card generation
→ Teachable Machine inference
→ rules
→ decision
→ persistence
```

**Benchmark evidence:** PENDING.

## 25. Limitations

1. The current model is trained on synthetic data.
2. The committed 92.889% result does not establish real-world accuracy.
3. Teachable Machine's final trained artifact and evaluation evidence are still pending.
4. The current application does not yet cover every dashboard, export, monitoring and notification feature in the SRS.
5. OCR quality depends on document quality and local Tesseract installation/configuration.
6. The current browser-to-backend Teachable Machine integration must be hardened before production because a browser-supplied prediction should not be treated as cryptographically trusted evidence.

## 26. Future Enhancements

- stronger production-side verification of Teachable Machine outputs
- production document storage and retention controls
- richer monitoring and anomaly detection
- full analytics/reporting/export suite
- more diverse real or privacy-safe benchmark data
- calibrated confidence analysis
- expanded product-category policy library
- reviewer workload analytics

## 27. Final Evidence Checklist

Complete these items before final submission:

- [ ] Real Teachable Machine model exported and loaded
- [ ] Teachable Machine training/validation/test evidence captured
- [ ] Claim Summary Card training corpus generated with required mapping
- [ ] Actual five-fold cross-validation metrics recorded
- [ ] 30+ unseen claim comparison table completed
- [ ] Final SRS traceability matrix reviewed against the running application
- [ ] Administrator dashboard demonstrated
- [ ] User dashboard demonstrated
- [ ] Report generation demonstrated
- [ ] Status tracking demonstrated
- [ ] Required notifications demonstrated
- [ ] Monitoring/anomaly behavior demonstrated or documented
- [ ] Performance benchmark completed
- [ ] Security test scenarios completed
- [ ] Project report diagrams inserted
- [ ] Screenshots added
- [ ] Installation/execution/deployment instructions verified
- [ ] Technical blog published and link added
- [ ] Demonstration video recorded as `.mp4`
- [ ] AI_USAGE.md finalized
- [ ] Team contribution record finalized

## 28. Source Repository

Repository:

`https://github.com/aptech-osogbo-assurex-team/AssureX-Claim-Engine`

Final branch/commit details must be recorded here after final merge:

```text
Branch: TBD
Final commit: TBD
Deployment URL: TBD
Demo video: TBD
Technical blog: TBD
```
