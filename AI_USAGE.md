# AI Tool Usage Log

| Date       | Tool Used   | What It Touched                        | What a Human Verified    |
|------------|-------------|----------------------------------------|--------------------------|
|2026-09-25  | Claude      | src/data_generation/generate_claims.py | Ran the script myself; 
|                                                                   | confirmed exactly 1500 records with 350/75/75 per class in each split;
                                                                    | reviewed the class generation logic and understood why each class uses the fields it does


|026-09-26   | GLM 5.3      |src/model_training/train_model.py      |Ran the script myself;  
                                                                    |confirmed 81.78% test accuracy, below the 85% target; 
                                                                    |Reviewed the confusion matrix and found Manual Review is the weakest class (65% recall), 
                                                                    |confused with both Valid and Invalid claims 
                                         
|2026-09-27 |Claude         |src/data_generation/generate_claims.py,|Ran the initial baseline (81.78%, below target);
                            |src/model_training/train_model.py      |tried feature engineering (no real improvement, 82.22%);
                            |                                       |tried hyperparameter tuning (84.44%, still short);
                            |                                       |diagnosed the actual cause (Valid/Invalid claims crowding into Manual Review's boundary zone)
                            |                                       |& fixed the generation logic directly; confirmed 87.11% test accuracy on my own machine,
                            |                                       |A meeting the 85% target




|           |               |src/data_generation/generate_claims.py;|Review found the contradiction flags did not match the actual dates, 
|2026-09-28 |Claude        data/claims.csv & model/classifier.joblib|(76 rows flagged claim-before-purchasewith none actually so; 
|           |               |                                       |repair flag had no repair date column). 
|           |               |                                       |Corrected generator derives both flags from real dates and adds a repair_date column.
|           |               |                                       |I re-ran generation and training myself;
|           |               |                                       | confirmed 350/75/75 split, flags match dates, and test accuracy of Test accuracy: 0.9289, 
                                                                    | Test accuracy: 92.89% 
|           |               |                                       | Meeting the 85% target