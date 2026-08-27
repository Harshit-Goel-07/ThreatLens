"""Unit tests for text chunking utilities."""

import pytest
from app.ingestion.chunking import SemanticChunker, MITREChunker, CVEChunker, PlaybookChunker


def test_semantic_chunker_basic():
    """Test basic semantic chunking."""
    chunker = SemanticChunker(chunk_size=100, chunk_overlap=20)
    text = "This is a test sentence. " * 20
    chunks = chunker.chunk_text(text)
    
    assert len(chunks) > 1
    assert all("content" in chunk for chunk in chunks)
    assert all(chunk["char_count"] <= 100 + 20 for chunk in chunks)


def test_semantic_chunker_small_text():
    """Test chunking with text smaller than chunk size."""
    chunker = SemanticChunker(chunk_size=100, chunk_overlap=20)
    text = "This is a short text."
    chunks = chunker.chunk_text(text)
    
    assert len(chunks) == 1
    assert chunks[0]["content"] == text


def test_semantic_chunker_no_overlap():
    """Test chunking with no overlap."""
    chunker = SemanticChunker(chunk_size=100, chunk_overlap=0)
    text = "This is a test sentence. " * 20
    chunks = chunker.chunk_text(text)
    
    assert len(chunks) > 1


def test_semantic_chunker_empty_text():
    """Test chunking with empty text."""
    chunker = SemanticChunker(chunk_size=100, chunk_overlap=20)
    text = ""
    chunks = chunker.chunk_text(text)
    
    assert len(chunks) == 0


def test_semantic_chunker_with_newlines():
    """Test chunking with text containing newlines."""
    chunker = SemanticChunker(chunk_size=50, chunk_overlap=10)
    text = "Line one\nLine two\nLine three\n\n" * 10
    chunks = chunker.chunk_text(text)
    
    assert len(chunks) > 1


def test_mitre_chunker():
    """Test MITRE technique chunking."""
    chunker = MITREChunker()
    technique_data = {
        "id": "T1059",
        "name": "Command and Scripting Interpreter",
        "tactic": "Execution",
        "description": "Adversaries may abuse command and script interpreters to execute commands.",
        "detection": "Monitor for unusual command-line usage",
        "mitigation": "Restrict command-line access"
    }
    
    chunks = chunker.chunk_technique(technique_data)
    
    assert len(chunks) >= 1
    assert all("content" in chunk for chunk in chunks)
    assert all("chunk_type" in chunk for chunk in chunks)
    assert chunks[0]["metadata"]["technique_id"] == "T1059"


def test_cve_chunker():
    """Test CVE entry chunking."""
    chunker = CVEChunker()
    cve_data = {
        "cve_id": "CVE-2023-1234",
        "severity": "Critical",
        "cvss_score": "9.8",
        "published_date": "2023-01-15",
        "description": "A critical vulnerability in the system",
        "affected_products": "Product X v1.0",
        "mitigation": "Update to v1.1"
    }
    
    chunks = chunker.chunk_cve(cve_data)
    
    assert len(chunks) == 1
    assert "CVE-2023-1234" in chunks[0]["content"]
    assert chunks[0]["metadata"]["cve_id"] == "CVE-2023-1234"


def test_playbook_chunker():
    """Test SOC playbook chunking."""
    chunker = PlaybookChunker()
    playbook_data = {
        "playbook_id": "PB-001",
        "title": "Phishing Response",
        "incident_type": "Phishing",
        "severity": "High",
        "description": "Response procedures for phishing incidents",
        "procedures": [
            {"title": "Isolate affected system", "description": "Disconnect from network", "actions": "Disconnect network cable"},
            {"title": "Analyze email", "description": "Examine email headers", "actions": "Check SPF, DKIM, DMARC"}
        ]
    }
    
    chunks = chunker.chunk_playbook(playbook_data)
    
    assert len(chunks) >= 2  # Overview + at least one procedure
    assert chunks[0]["chunk_type"] == "overview"
    assert chunks[0]["metadata"]["playbook_id"] == "PB-001"
