"""Pydantic models used throughout the PR Agent Swarm.

These models define the inputs, outputs and intermediate data exchanged
between agents. Using strict validation ensures high extraction accuracy
and prevents accidental omission of required fields. When a value cannot
be reliably determined it must be set to ``"N/A"`` to honour the
"Data Not Found" policy.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional, Any

from pydantic import BaseModel, Field, HttpUrl, validator, root_validator


class Prospect(BaseModel):
    """Represents a potential journalist prospect pulled from the input CSV."""

    name: str = Field(..., description="Full name of the journalist")
    publication: str = Field(..., description="Publication or outlet the journalist writes for")
    keywords: Optional[str] = Field(
        None,
        description="Semi‑colon separated list of topics or keywords relevant to the journalist",
    )

    @validator("name", "publication", pre=True)
    def strip_strings(cls, v: str) -> str:
        return v.strip() if isinstance(v, str) else v


class Citation(BaseModel):
    """A citation referencing the source of extracted information."""

    url: HttpUrl
    description: str


class JournalistProfile(BaseModel):
    """Information about a journalist returned by the discovery agent."""

    prospect_name: str = Field(..., description="Name of the input prospect")
    matched_name: Optional[str] = Field(
        None, description="Name as found in public sources; may be N/A if not found"
    )
    email: Optional[str] = Field(
        None, description="Publicly available email address; N/A if not found"
    )
    publication: Optional[str] = Field(
        None, description="Publication or outlet associated with the journalist; N/A if not found"
    )
    profile_url: Optional[str] = Field(
        None, description="URL to the journalist’s profile or biography; N/A if not found"
    )
    citations: List[Citation] = Field(
        default_factory=list,
        description="List of citations evidencing the discovery results",
    )

    def model_post_init(self, __context: Any) -> None:
        """Ensure optional fields default to 'N/A' when not provided."""
        for field_name in ["matched_name", "email", "publication", "profile_url"]:
            value = getattr(self, field_name)
            if not value:
                object.__setattr__(self, field_name, "N/A")


class ResearchNotes(BaseModel):
    """Notes produced by the research agent summarising the journalist’s recent work."""

    prospect_name: str = Field(..., description="Name of the input prospect")
    topics: List[str] = Field(
        ..., description="List of key topics or themes identified in the journalist’s recent work"
    )
    summary: str = Field(
        ..., description="Concise summary of the journalist’s recent articles or social posts"
    )
    angles: List[str] = Field(
        ..., description="Suggested angles or hooks relevant to the Life Legally Single brand"
    )
    citations: List[Citation] = Field(
        default_factory=list,
        description="List of citations supporting the research notes",
    )


class PitchDraft(BaseModel):
    """A pitch draft tailored to a specific journalist."""

    prospect_name: str = Field(..., description="Name of the input prospect")
    slug: str = Field(..., description="Slugified filename for saving the pitch draft")
    subject_line: str = Field(..., description="Suggested subject line for the email pitch")
    greeting: str = Field(..., description="Personalized greeting for the journalist")
    body: str = Field(..., description="Main pitch body text")
    closing: str = Field(..., description="Closing sentence and signature")
    citations: List[Citation] = Field(
        default_factory=list,
        description="List of citations used to justify the pitch contents",
    )


class ManifestError(BaseModel):
    """Represents an error encountered during processing of a prospect."""

    prospect_name: str
    stage: str
    message: str


class RunManifest(BaseModel):
    """Summary of a run across all prospects."""

    started_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when the run started (UTC)",
    )
    finished_at: Optional[datetime] = Field(
        None, description="Timestamp when the run finished (UTC)"
    )
    total_prospects: int = Field(..., description="Total number of prospects processed")
    successful: int = Field(0, description="Number of successfully processed prospects")
    errors: List[ManifestError] = Field(
        default_factory=list,
        description="List of errors that occurred during the run",
    )

    def record_success(self):
        self.successful += 1

    def record_error(self, prospect_name: str, stage: str, message: str):
        self.errors.append(ManifestError(prospect_name=prospect_name, stage=stage, message=message))

    def finish(self):
        self.finished_at = datetime.utcnow()