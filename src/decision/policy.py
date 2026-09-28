"""Configurable model-consistency thresholds."""

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ConsistencyPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    min_confidence: float = Field(ge=0.0, le=1.0)
    confidence_diff_tight_band: float = Field(ge=0.0, le=1.0)
    confidence_diff_wide_band: float = Field(ge=0.0, le=1.0)

    @model_validator(mode="after")
    def validate_bands(self) -> "ConsistencyPolicy":
        if self.confidence_diff_tight_band > self.confidence_diff_wide_band:
            raise ValueError("tight confidence band must not exceed wide confidence band")
        return self


def load_consistency_policy(path: str | Path) -> ConsistencyPolicy:
    policy_path = Path(path)
    with policy_path.open("r", encoding="utf-8") as handle:
        return ConsistencyPolicy.model_validate(json.load(handle))
