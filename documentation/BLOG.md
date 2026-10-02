# Building AssureX: From Warranty Claim Prediction to Evidence-Driven Decision Support

Warranty claims look simple until the evidence is examined closely.

A customer may have a product, a receipt, a warranty card, a serial number, a
repair history and a description of a fault. The claim can still contain missing
documents, inconsistent dates, conflicting product information, a duplicate
submission or a condition that falls outside the warranty policy. A machine
learning model can classify a claim, but it cannot by itself establish every one
of those business facts.

That observation became the central design principle of **AssureX Claim Engine**:

> \\\*\\\*A model prediction is evidence, not the entire business decision.\\\*\\\*

AssureX combines a Python classification model, a separate Google Teachable
Machine image model, a configurable warranty-rule engine, consistency checks,
duplicate detection and a deterministic decision engine. The result is a system
that can produce a recommendation while preserving the reasons and evidence
behind it.

This article describes what we built, what went wrong during development, what
we corrected, and how we prepared the system for the final competition evidence.

\---

## The business problem

Warranty decisions require more than pattern recognition. A claim can be
statistically similar to previously valid claims and still be invalid because
the warranty expired. Conversely, a claim can have unusual characteristics and
still deserve consideration because the evidence is complete and the warranty
conditions are satisfied.

We therefore separated the problem into evidence categories.

The first category is **structured claim evidence**: product details, dates,
price, fault type, warranty period, repair history, document completeness and
serial-number status.

The second category is **visual evidence**. The same underlying claim is turned
into a Claim Summary Card and independently evaluated by Google Teachable
Machine.

The third category is **business evidence**. Warranty policies determine whether
a claim is within the coverage period, whether the fault is covered, whether
required evidence exists and whether integrity rules are violated.

The final category is **decision evidence**: agreement or disagreement between
the two models, confidence difference, rule outcomes, duplicate indicators,
contradictions and missing evidence.

This separation gives the application a clearer responsibility boundary. Machine
learning estimates. Rules validate business conditions. The decision engine
adjudicates the combined evidence.

\---

## The architecture

The architecture is deliberately straightforward.

```text
Claim + Evidence
      |
      +--> Structured features --> Python classifier
      |
      +--> Evidence-only Card --> Teachable Machine
      |
      +--> Warranty/integrity rules
      |
      +--> Missing/duplicate/contradiction checks
      |
      +------------------------+
                               |
                        Decision Engine
                               |
              +----------------+----------------+
              |                |                |
          Likely Valid   Likely Invalid   Manual Review
```

The important part is what the architecture **does not** do. It does not call a
generative AI API and ask it to decide whether a warranty claim is valid. The
final decision is produced by deterministic application logic using the team's
Python model, Teachable Machine result and rule evidence.

That makes the system easier to explain during evaluation and easier to audit.

\---

## Building the common dataset

The competition specification requires a common warranty-claim dataset with three
classes:

* Valid Claim
* Invalid Claim
* Manual Review

Our dataset contains 1,500 synthetic claim records, 500 per class. The split is
exactly:

```text
Training      1,050
Validation      225
Testing        225
```

and every split retains equal class representation.

The synthetic data intentionally contains features relevant to warranty
assessment: purchase price, warranty duration, product age, remaining warranty,
repair history, missing documents, fault type, fault coverage, serial-number
match and date contradictions.

There is an important limitation here. Synthetic data can produce optimistic
results when its feature-generation logic closely follows its labels. We
therefore treat the 92.89% test result as a **synthetic held-out benchmark**, not
as evidence that the application will achieve the same accuracy on real warranty
claims.

That distinction matters more than a large headline accuracy number.

\---

## The first difficult lesson: the visual dataset has to be faithful

One of the most important defects we found during the resubmission audit was not
a model issue. It was a data-representation issue.

The Python model reads structured claim records. Teachable Machine reads Claim
Summary Card images. The competition requirement is that these two representations
must describe the **same underlying claim**.

The first implementation did not do that faithfully.

The card conversion reconstructed a claim but left the submitted-document list
and repair-history list empty. That meant a CSV record could say:

```text
repair\\\_history\\\_count = 2
missing\\\_document\\\_count = 0
```

while its visual card could show no repair history and missing evidence.

That is more serious than a formatting bug. It means the visual model could be
trained on a different representation of the claim than the Python model.

We fixed the conversion layer so that it reconstructs the same document
availability and repair-history evidence before rendering the card.

Then we regenerated the full card corpus:

```text
Training images      2,100
Validation images      225
Testing images         225
Total                  2,550
```

A deterministic audit checks the fields displayed on the card for all 1,500
claims. The audit result is:

```text
Claims checked       1,500
Field mismatches          0
Result                  PASS
```

This was a good example of the difference between implementation quality and
decision quality. The code already worked. The evidence relationship was wrong.

\---

## Claim Summary Cards

The Claim Summary Card is intentionally evidence-only.

It contains things such as:

* Claim ID
* product age
* warranty status
* remaining warranty
* fault category
* repair history count
* receipt/invoice availability
* warranty-card availability
* serial-number status
* missing documents

It does **not** contain:

* Python prediction
* Python confidence
* Teachable Machine prediction
* Teachable Machine confidence
* final decision

That design prevents direct label leakage. The visual classifier has to infer
from the claim evidence representation rather than simply reading a precomputed
answer from the card.

\---

## Python model development

We compared three candidate approaches:

1. Logistic Regression
2. Random Forest
3. Gradient Boosting

Model selection is performed on the validation split. The held-out test split is
reserved for the final benchmark.

The selected model is Random Forest.

The reported evidence is:

```text
Validation accuracy:          90.67%
5-fold CV mean:               90.76%
5-fold CV standard deviation:  1.72%
Held-out test accuracy:      92.89%
```

The test confusion matrix is:

```text
                 Predicted
               V      I      M

Actual V       75     0      0
Actual I        0    68      7
Actual M        3     6     66
```

The class-wise results show that Manual Review is the hardest of the three
classes in the synthetic benchmark, with recall of 88.00%.

That result is useful because it tells us where errors remain instead of hiding
them behind one overall accuracy figure.

\---

## Why Manual Review exists

A claim-processing system should not assume that every case can be classified
cleanly.

AssureX therefore has three outputs at the application level:

```text
Likely Valid
Likely Invalid
Manual Review Required
```

Manual review is not a failure state. It is a deliberate safety mechanism for
uncertainty and conflict.

Examples include:

* model disagreement;
* low confidence;
* missing required evidence;
* duplicate-claim indicators;
* contradictory dates;
* serial-number conflicts;
* warranty-rule failures that require human judgement.

The reviewer can make a decision and add comments, while the original automated
evidence remains in the audit trail.

\---

## Warranty rules are not machine learning

The warranty-rule engine is another important separation.

Rules are stored in configuration rather than scattered through API handlers.
The active policy file contains category-aware warranty logic and the submission
package includes three standalone policy artifacts.

Representative checks include:

* warranty activity;
* reporting deadline;
* required documents;
* covered faults;
* excluded damage;
* serial-number consistency;
* model consistency;
* claim date before purchase;
* repair date before purchase;
* unauthorized repairs;
* previous replacement;
* duplicate claim.

The rule engine returns a result such as:

```text
rule\\\_id
passed
severity
message
```

That means the final decision can explain not only what a model predicted, but
also which business conditions passed or failed.

\---

## OCR and document processing

The SRS requires document ingestion and extraction. AssureX therefore includes a
document service with file validation, storage, SHA-256 hashing and OCR
integration.

A document record retains:

```text
Document type
Filename
MIME type
Size
SHA-256
Upload time
OCR/extraction output
Verification status
```

This gives the application a place to record not just what someone uploaded,
but what the system extracted from it and whether that extraction was verified.

The practical limitation is that actual OCR depends on the Tesseract installation
in the runtime environment. The application handles unavailable OCR with a
controlled error instead of crashing.

\---

## Model comparison

The most interesting part of AssureX is not running two models separately. It is
comparing them.

For every evaluated claim, the decision evidence can contain:

```text
Python class
Python confidence for all three classes
TM class
TM confidence for all three classes
Predicted-class match
Top-class confidence difference
Consistency status
Rule results
Missing documents
Contradictions
Duplicate indicator
Final recommendation
```

The confidence difference is calculated as the absolute difference between the
top-class probabilities from the two models.

The system categorizes the comparison into:

* Strong Match
* Acceptable Match
* Weak Match
* Model Disagreement
* Uncertain Result

The key idea is that disagreement becomes a visible signal rather than something
that is averaged away.

\---

\## The 30+ unseen-claim requirement

The competition requires a separate comparison report containing at least 30 unseen test claims and detailed evidence for both models.

The retained comparison report is `reports/model_comparison_30.csv`.

The report contains Claim ID, actual class, Python prediction and confidences, Claim Summary Card filename, Teachable Machine prediction and confidences, prediction agreement, confidence difference, consistency status, warranty-rule result, missing documents, contradictions, duplicate indicator, final application decision, and disagreement explanation.

The retained report contains 30 claims with 25/30 prediction agreements, or 83.33%.

Consistency results: Strong Match 10, Weak Match 7, Uncertain Result 5, Acceptable Match 5, and Model Disagreement 3.

Final decisions: 28 manual review required and 2 likely valid.

The 30-case comparison is integration evidence. It demonstrates the interaction between the Python model, Teachable Machine, evidence checks, consistency logic and the final decision engine. It is not a substitute for the full independent 225-card Teachable Machine accuracy measurement.

The final Teachable Machine measurement is 191 correct predictions out of 225 independent unseen test cards, or 84.8889% accuracy. The SRS target is at least 85%, so the measured result is 0.1111 percentage points below the stated target.

These values are reported from the retained evidence. The result is not rounded or adjusted to satisfy the target.

---
## Security and privacy

AssureX uses several practical controls in the current build.

Authentication uses hashed passwords and expiring sessions. Protected claim
endpoints verify ownership so a customer cannot simply access another
customer's claim.

Documents are hashed using SHA-256. File ingestion validates types and sizes and
stores files under controlled names.

Pydantic domain models are configured to reject unexpected fields, which reduces
the chance of silent contract drift.

The final decision is not delegated to a generative AI API. The SRS explicitly
requires the final result to come from the team's models, warranty rules and
application logic, and that is how the decision path is structured.

The competition dataset is synthetic. Real personal customer evidence should not
be committed to the public repository.

\\---

## Testing

Testing was treated as part of implementation rather than a final ceremony.

The hardened suite now contains 45 tests covering:

\* domain schema validation;
\* authentication and API protection;
\* card rendering;
\* ML inference;
\* rule behavior;
\* decision behavior;
\* document ingestion;
\* dataset/card fidelity.

The test run in the current engineering environment is:

```text
45 passed
```

The saved Python artifact was trained with scikit-learn 1.9.1 and the project
requirements pin that version. The final local verification should be repeated
on the team's declared Python 3.13.1 / scikit-learn 1.9.1 environment after the
final Teachable Machine and evidence changes.

\---

## What went wrong and what we learned

The most valuable lessons were not about adding more code.

### Lesson 1: a working feature can still be wrong evidence

The Claim Card bug passed code-level thinking but failed evidence-level thinking.
The important question was not “does it render?” but “does it represent the same
claim?”

### Lesson 2: one accuracy number is not enough

A 92.89% test score is useful, but the confusion matrix and class-wise results
show where the model actually makes mistakes.

### Lesson 3: uncertainty must have a path

A system that always returns Valid or Invalid can look simple while silently
hiding uncertainty. Manual review makes uncertainty explicit.

### Lesson 4: reproducibility matters

The dataset split, card mapping, model artifact and evaluation scripts are all
part of the evidence chain. A reviewer should be able to trace an image back to a
claim ID and then back to the structured record.

### Lesson 5: documentation should follow evidence



The report and blog should describe what was measured, not what was intended.

The final Teachable Machine measurement is therefore reported exactly:

84.8889% (191/225) on the independent unseen test set, compared with the SRS

target of at least 85%.



The 0.1111 percentage-point gap is retained rather than rounded upward.

\---

## Limitations



The most important limitation remains the use of synthetic data. Synthetic

benchmarks are suitable for demonstrating the requested pipeline, but they do

not prove production performance on real customers.



The final Teachable Machine result is 84.8889% on 225 independent unseen test

cards. This is 0.1111 percentage points below the stated SRS target of at least

85%, so that numeric requirement remains unmet.



The current application has a stronger core decision path than a complete

enterprise product. Some dashboards, search/filtering, analytics, export and

full document-verification flows remain incomplete.



The 30-case model comparison is retained as integration evidence, but it is not

a replacement for the full 225-card Teachable Machine accuracy evaluation.



That is a deliberate trade-off for the competition build: preserve the integrity

of the core decision system rather than implement a large number of shallow

features that cannot be properly tested.

\---

## Conclusion

AssureX is an example of a practical AI decision-support architecture in which
models are only one part of the evidence.

The final structure is:

```text
Evidence
  ↓
Python model + visual model
  ↓
Model comparison
  ↓
Warranty / integrity rules
  ↓
Contradiction / duplicate / missing evidence checks
  ↓
Explainable decision
  ↓
Human review when necessary


The hardened resubmission now has a traceable evidence chain from the corrected
structured claims and Claim Summary Cards through the independent model
evaluations and the retained 30-case comparison report.

The Python model achieved 92.8889% accuracy on the independent 225-card test
set. The retained Teachable Machine Model A achieved 84.8889% on the same
independent test set. The Teachable Machine SRS target of at least 85% therefore
remains unmet by 0.1111 percentage points.

That result is reported exactly rather than rounded upward. Model B was not
promoted because its validation result was lower than Model A's.

The important engineering lesson is that a competition submission should make
the evidence easy to audit. Dataset integrity, card fidelity, model artifacts,
independent evaluation, comparison reports, automated validation and tests all
form part of the final claim.

The result is therefore presented as an evidence-backed competition prototype,
with its implemented capabilities and remaining limitations stated explicitly.

\---