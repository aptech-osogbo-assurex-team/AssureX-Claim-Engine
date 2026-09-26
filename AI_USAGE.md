# AI Tool Usage Log

| Date       | Tool Used   | What It Touched                        | What a Human Verified    |
|------------|-------------|----------------------------------------|--------------------------|
|2026-09-25  | Claude      | src/data_generation/generate_claims.py | Ran the script myself; 
|                                                                   | confirmed exactly 1500 records with 350/75/75 per class in each split;
                                                                    | reviewed the class generation logic and understood why each class uses the fields it does


|026-09-26  | GLM 5.3     |src/model_training/train_model.py        |Ran the script myself; 
                                                                    |confirmed 81.78% test accuracy, below the 85% target; 
                                                                    |reviewed the confusion matrix and found Manual Review is the weakest class (65% recall), 
                                                                    |confused with both Valid and Invalid claims