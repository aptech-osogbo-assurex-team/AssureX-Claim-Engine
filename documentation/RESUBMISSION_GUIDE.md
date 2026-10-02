\## Current resubmission evidence status



The Teachable Machine model has now been retrained using the corrected training

cards.



The retained Model A was trained on 2,100 corrected training cards, with 700

cards per class. The independent test set contains 225 cards, with 75 cards per

class.



The final independent Teachable Machine result is:



\- 191/225 correct predictions

\- 84.8889% accuracy

\- SRS target: at least 85%

\- Gap: 0.1111 percentage points below the target



The result is reported exactly and is not rounded upward.



A separate Model B validation experiment achieved 80.4444% and was not promoted.



The 30-case comparison report has also been generated and retained at:



`reports/model_comparison_30.csv`



It contains 30 claims, with 25/30 prediction agreements (83.33%), 28 final

manual-review decisions and 2 likely-valid decisions.



The 30-case report is integration evidence and does not replace the full

225-card Teachable Machine accuracy evaluation.



## Final commands



Run the final validation commands after all documentation and submission files

have been reviewed:



```bash

py scripts/validate_submission.py

py -m pytest -q
```


