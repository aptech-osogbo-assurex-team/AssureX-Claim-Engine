from pathlib import Path

import pandas as pd

from src.cards.dataset import REQUIRED_DOCUMENT_GROUPS, row_to_claim


EXPECTED_REQUIRED_DOCS = {group[0] for group in REQUIRED_DOCUMENT_GROUPS}


def test_row_to_claim_preserves_document_availability_and_repair_count() -> None:
    frame = pd.read_csv("data/claims.csv")

    for _, row in frame.sample(n=25, random_state=7).iterrows():
        claim = row_to_claim(row)
        supplied = {document.document_type for document in claim.submitted_documents}

        expected_tokens = {
            token.strip()
            for token in str(row.documents_provided).split(",")
            if token.strip()
        }

        assert {item.value for item in supplied} == expected_tokens
        assert len(claim.previous_repairs) == int(row.repair_history_count)
        assert len(claim.missing_document_types) == int(row.missing_document_count)


def test_every_dataset_row_has_a_deterministic_fidelity_mapping() -> None:
    frame = pd.read_csv("data/claims.csv")
    assert frame["claim_id"].is_unique
    assert frame["class_label"].value_counts().to_dict() == {
        "Valid Claim": 500,
        "Invalid Claim": 500,
        "Manual Review": 500,
    }
    assert frame.groupby(["split", "class_label"]).size().to_dict()



def test_card_source_module_exists() -> None:
    assert Path("src/cards/dataset.py").exists()
