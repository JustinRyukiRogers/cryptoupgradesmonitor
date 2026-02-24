from enum import Enum
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime
from pydantic import BaseModel, Field

# --- Enums ---

class SourceType(str, Enum):
    X = "X"
    GITHUB = "GitHub"
    BLOG = "Blog"

class UpgradeStatus(str, Enum):
    PROPOSAL_ONLY = "proposal_only"
    APPROVED_NOT_DEPLOYED = "approved_not_deployed"
    DEPLOYED_MAINNET = "deployed_mainnet"
    REJECTED = "rejected"

# --- Source Registry Models ---

class ProjectConfig(BaseModel):
    networks: List[str]
    relevant_tokens: List[str] = Field(default_factory=list)
    x_accounts: List[str] = Field(default_factory=list)
    blogs: List[str] = Field(default_factory=list)
    github_orgs: List[str] = Field(default_factory=list)
    governance: List[str] = Field(default_factory=list, description="Governance portal URLs")

class SourceRegistry(BaseModel):
    projects: Dict[str, ProjectConfig]

# --- Ingestion Layer Models ---

class RawEvent(BaseModel):
    event_id: UUID = Field(default_factory=uuid4)
    project: str
    source_type: SourceType
    author: str
    text: str
    url: str
    timestamp: datetime
    raw_data: Optional[Dict[str, Any]] = None

# --- Analysis Layer Models ---

class AffectedSubtype(BaseModel):
    subtype_code: str
    impact_type: str
    reason: str
    confidence: float = Field(default=1.0)
    token_context: str = Field(default="")

class RelevanceSignal(BaseModel):
    is_relevant: bool
    affected_subtypes: List[AffectedSubtype] = Field(default_factory=list)

class Evidence(BaseModel):
    type: str # "x", "github_release", "blog_post", "governance_tx"
    url: str
    description: Optional[str] = None

class UpgradeConfirmation(BaseModel):
    is_confirmed: bool
    confidence: float = Field(..., ge=0.0, le=1.0)
    status_detected: Optional[str] = None
    supporting_evidence: Optional[str] = None
    evidence: List[Evidence]
    reasoning: str

# --- Synthesis/Output Models ---

class CanonicalUpgrade(BaseModel):
    canonical_id: UUID = Field(default_factory=uuid4)
    headline: str
    project: str
    network: str
    status: UpgradeStatus
    primary_source: str
    supporting_sources: List[str]
    timestamp: datetime
    confidence: float
    reasoning: str
    affected_subtypes: List[AffectedSubtype] = Field(default_factory=list)
