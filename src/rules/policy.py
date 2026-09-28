"""Pydantic contracts and loader for configurable warranty policies."""

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from src.domain.enums import DocumentType


class PolicyModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class WarrantyPolicy(PolicyModel):
    standard_warranty_duration_months: int = Field(gt=0)
    reporting_deadline_days: int = Field(ge=0)
    grace_period_days: int = Field(ge=0)
    required_document_groups: list[list[DocumentType]] = Field(default_factory=list)
    conditional_document_groups: dict[str, list[list[DocumentType]]] = Field(default_factory=dict)
    covered_fault_categories: list[str] = Field(default_factory=list)
    excluded_damage_types: list[str] = Field(default_factory=list)
    reject_unauthorized_repairs: bool = True
    reject_previous_replacement: bool = True


class PolicySet(PolicyModel):
    version: str = Field(min_length=1)
    default: WarrantyPolicy
    categories: dict[str, WarrantyPolicy] = Field(default_factory=dict)

    def for_category(self, category: str) -> WarrantyPolicy:
        return self.categories.get(category, self.default)


def load_policy_set(path: str | Path) -> PolicySet:
    policy_path = Path(path)
    with policy_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return PolicySet.model_validate(payload)
