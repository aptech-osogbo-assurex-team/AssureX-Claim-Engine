# Teachable Machine model

Export the independently trained Google Teachable Machine **image** model and place these files here:

- `model.json`
- `metadata.json`
- the referenced `.bin` model weights

The application loads the model in the browser and sends the real prediction probabilities to the backend. Do not replace this with hard-coded predictions or simulated confidence values.

Expected class labels:

- `Valid Claim`
- `Invalid Claim`
- `Manual Review`
