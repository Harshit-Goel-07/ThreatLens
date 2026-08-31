"""
SQLAlchemy models for ThreatLens metadata storage
"""

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, JSON, String, Text
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class User(Base):
    """Application user for JWT authentication."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(320), unique=True, index=True, nullable=False)
    full_name = Column(String(255), nullable=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(20), default="analyst", nullable=False)  # analyst, admin
    is_active = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login_at = Column(DateTime(timezone=True), nullable=True)


class Document(Base):
    """Base document model for all ingested content"""
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    doc_id = Column(String(255), unique=True, index=True, nullable=False)
    source_type = Column(String(50), nullable=False, index=True)  # mitre, cve, log, playbook
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)
    # NOTE: attribute is renamed from "metadata" (reserved by SQLAlchemy's
    # declarative base) while keeping the physical column name "metadata".
    doc_metadata = Column("metadata", JSON, nullable=True)  # Flexible metadata storage
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Processing status
    processed = Column(Boolean, default=False)
    embedding_id = Column(String(255), nullable=True)  # Qdrant point ID


class MITRETechnique(Base):
    """MITRE ATT&CK technique metadata"""
    __tablename__ = "mitre_techniques"
    
    id = Column(Integer, primary_key=True, index=True)
    technique_id = Column(String(20), unique=True, nullable=False)  # T1059
    technique_name = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    
    # ATT&CK framework info
    tactic_name = Column(String(100), nullable=False)
    tactic_id = Column(String(10), nullable=False)  # TA0002
    platforms = Column(JSON, nullable=True)  # ["Windows", "Linux", "macOS"]
    
    # Additional metadata
    data_sources = Column(JSON, nullable=True)
    permissions_required = Column(JSON, nullable=True)
    defenses_bypassed = Column(JSON, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    doc_id = Column(String(255), nullable=False)  # Link to documents table


class CVEEntry(Base):
    """CVE vulnerability metadata"""
    __tablename__ = "cve_entries"
    
    id = Column(Integer, primary_key=True, index=True)
    cve_id = Column(String(20), unique=True, nullable=False)  # CVE-2024-1234
    description = Column(Text, nullable=False)
    
    # CVSS scores
    cvss_base_score = Column(Float, nullable=True)
    cvss_base_severity = Column(String(20), nullable=True)  # HIGH, MEDIUM, LOW
    cvss_vector = Column(String(500), nullable=True)
    
    # Affected products
    vendor = Column(String(100), nullable=True)
    product = Column(String(100), nullable=True)
    versions_affected = Column(JSON, nullable=True)
    
    # Timeline
    published_date = Column(DateTime(timezone=True), nullable=True)
    last_modified_date = Column(DateTime(timezone=True), nullable=True)
    
    # References and mitigations
    references = Column(JSON, nullable=True)
    mitigations = Column(JSON, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    doc_id = Column(String(255), nullable=False)  # Link to documents table


class SecurityLog(Base):
    """Security log entries metadata"""
    __tablename__ = "security_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    log_id = Column(String(255), unique=True, nullable=False)
    log_type = Column(String(50), nullable=False)  # sysmon, windows_event, auditd
    
    # Log content and parsing
    raw_log = Column(Text, nullable=False)
    parsed_fields = Column(JSON, nullable=True)
    
    # Event details
    event_id = Column(String(50), nullable=True)
    event_name = Column(String(200), nullable=True)
    severity = Column(String(20), nullable=True)
    category = Column(String(100), nullable=True)
    
    # System info
    hostname = Column(String(255), nullable=True)
    username = Column(String(255), nullable=True)
    process_name = Column(String(255), nullable=True)
    
    # Timestamps
    event_timestamp = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    doc_id = Column(String(255), nullable=False)  # Link to documents table


class SOCPlaybook(Base):
    """SOC playbook metadata"""
    __tablename__ = "soc_playbooks"
    
    id = Column(Integer, primary_key=True, index=True)
    playbook_id = Column(String(100), unique=True, nullable=False)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=False)
    
    # Classification
    incident_type = Column(String(100), nullable=False)  # phishing, malware, ddos
    severity_level = Column(String(20), nullable=False)  # HIGH, MEDIUM, LOW
    phase = Column(String(50), nullable=True)  # detection, analysis, containment
    
    # Playbook content
    procedures = Column(JSON, nullable=True)  # Structured procedure steps
    checklists = Column(JSON, nullable=True)
    escalation_criteria = Column(JSON, nullable=True)
    
    # Metadata
    author = Column(String(255), nullable=True)
    version = Column(String(20), nullable=True)
    tags = Column(JSON, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    doc_id = Column(String(255), nullable=False)  # Link to documents table


class QueryHistory(Base):
    """Query history for analytics and feedback"""
    __tablename__ = "query_history"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(255), nullable=False, index=True)
    user_query = Column(Text, nullable=False)
    
    # Retrieval info
    retrieved_docs = Column(JSON, nullable=True)  # List of retrieved doc IDs
    retrieval_scores = Column(JSON, nullable=True)
    
    # Response info
    llm_response = Column(Text, nullable=False)
    response_time_ms = Column(Integer, nullable=True)
    token_count = Column(Integer, nullable=True)
    
    # Quality metrics
    user_feedback = Column(Integer, nullable=True)  # 1 (good) to 5 (bad)
    groundedness_score = Column(Float, nullable=True)
    hallucination_detected = Column(Boolean, default=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class IngestionJob(Base):
    """Ingestion job tracking"""
    __tablename__ = "ingestion_jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String(255), unique=True, nullable=False)
    source_type = Column(String(50), nullable=False)
    
    # Job status
    status = Column(String(20), default="pending")  # pending, running, completed, failed
    progress = Column(Float, default=0.0)  # 0.0 to 1.0
    
    # Statistics
    total_items = Column(Integer, default=0)
    processed_items = Column(Integer, default=0)
    failed_items = Column(Integer, default=0)
    
    # Error handling
    error_message = Column(Text, nullable=True)
    error_details = Column(JSON, nullable=True)
    
    # Timestamps
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
