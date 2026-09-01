"""
Prompt templates for ThreatLens
Security-specific prompts with citation requirements
"""

from typing import Dict, Any, Optional


SYSTEM_PROMPTS = {
    "default": """You are ThreatLens, an elite AI assistant specialized in cybersecurity analysis for SOC analysts.

Format your responses with clean, highly structured Markdown:
- Use `## Heading` for major sections and `### Subheading` for subsections.
- Use Markdown tables when comparing metrics, CVSS details, or affected components.
- Use numbered lists (1, 2, 3) for sequential investigation and remediation steps.
- Use bullet points for indicators, detection rules, or key observations.
- Bold key terms or entity names clearly.

Guidelines:
1. Base your answers on the provided context whenever available
2. Cite sources using [Source N] notation when applicable
3. Be precise, technical, and directly actionable
4. Never fabricate CVE IDs, technique IDs, or security information""",

    "alert_explanation": """You are ThreatLens specialized in security alert triage and analysis.

Format your output with clear structured sections:
## 1. Alert Summary & Threat Overview
(Concise summary of the activity, severity, and potential impact)

## 2. MITRE ATT&CK Mapping
(Map tactics, techniques, and sub-techniques)

## 3. Immediate Response & Containment
(Numbered step-by-step containment actions)

## 4. Deep Investigation & Forensics
(Specific logs, endpoints, network queries, and commands to investigate)

Always cite your sources and provide clear, actionable guidance.""",

    "cve_lookup": """You are ThreatLens specialized in vulnerability analysis.

Format your output with clear structured sections:
## 1. Vulnerability Overview
(Description, impact, and root cause)

## 2. Technical Details & Affected Systems
| Metric / Property | Details |
| :--- | :--- |
| **CVE ID** | [CVE ID] |
| **Severity** | [CVSS Score / Severity] |
| **Vulnerability Type** | [RCE, PrivEsc, etc.] |
| **Affected Versions** | [Software & Version ranges] |

## 3. Remediation & Patching
(Official patches, vendor workarounds, and configuration hardening)

## 4. Detection & Hunting
(SIEM rules, YARA/Sigma rules, or log queries)""",

    "incident_response": """You are ThreatLens specialized in SOC incident response.

Format your response as an actionable SOC Playbook:
## 1. Incident Assessment & Severity
(Brief scenario overview, risk level, and scope)

## 2. Immediate Containment Checklist
(Numbered immediate isolation and containment procedures)

## 3. Eradication & Remediation Steps
(Step-by-step instructions to eliminate the threat from the environment)

## 4. Recovery & Post-Incident Actions
(System restoration, monitoring, and lessons learned)""",

    "threat_intel": """You are ThreatLens specialized in threat intelligence.

Format your response cleanly:
## 1. Threat Profile & Background
(Adversary group, campaigns, and primary objectives)

## 2. Tactics, Techniques & Procedures (TTPs)
(MITRE ATT&CK breakdown and observed behaviors)

## 3. Indicators of Compromise (IoCs) & Detection
(File hashes, domains, network signatures, and detection strategies)

## 4. Mitigation & Defense Recommendations
(Hardening measures and preventative controls)"""
}


def build_rag_prompt(
    query: str,
    context: str,
    prompt_type: str = "default",
    additional_instructions: Optional[str] = None
) -> str:
    """
    Build RAG prompt with context and query
    
    Args:
        query: User query
        context: Retrieved context
        prompt_type: Type of system prompt to use
        additional_instructions: Optional additional instructions
        
    Returns:
        Formatted prompt string
    """
    system_prompt = SYSTEM_PROMPTS.get(prompt_type, SYSTEM_PROMPTS["default"])
    
    prompt_parts = [
        system_prompt,
        "\n# Retrieved Context\n",
        context,
        "\n# User Query\n",
        query
    ]
    
    if additional_instructions:
        prompt_parts.append(f"\n# Additional Instructions\n{additional_instructions}")
    
    return "\n".join(prompt_parts)


def build_messages(
    query: str,
    context: str,
    prompt_type: str = "default",
    conversation_history: Optional[list] = None
) -> list:
    """
    Build message list for chat-based LLMs
    
    Args:
        query: User query
        context: Retrieved context
        prompt_type: Type of system prompt
        conversation_history: Previous conversation messages
        
    Returns:
        List of message dictionaries
    """
    messages = []
    
    # System message
    system_prompt = SYSTEM_PROMPTS.get(prompt_type, SYSTEM_PROMPTS["default"])
    messages.append({
        "role": "system",
        "content": system_prompt
    })
    
    # Add conversation history if provided
    if conversation_history:
        messages.extend(conversation_history)
    
    # User message with context
    user_message = f"""# Retrieved Context
{context}

# Query
{query}

Please provide a comprehensive answer based on the context above. Always cite your sources using [Source N] notation."""
    
    messages.append({
        "role": "user",
        "content": user_message
    })
    
    return messages


# Specialized prompt builders

def build_alert_explanation_prompt(
    alert_description: str,
    context: str
) -> str:
    """Build prompt for alert explanation"""
    query = f"""Explain this security alert:

{alert_description}

Please provide:
1. What this alert indicates
2. Relevant MITRE ATT&CK techniques
3. Severity assessment
4. Recommended response actions
5. Investigation steps"""
    
    return build_rag_prompt(query, context, prompt_type="alert_explanation")


def build_cve_lookup_prompt(
    cve_query: str,
    context: str
) -> str:
    """Build prompt for CVE lookup"""
    query = f"""Provide information about: {cve_query}

Please include:
1. Vulnerability description and impact
2. Affected products and versions
3. CVSS score and severity
4. Mitigation recommendations
5. Detection methods"""
    
    return build_rag_prompt(query, context, prompt_type="cve_lookup")


def build_incident_response_prompt(
    incident_description: str,
    context: str
) -> str:
    """Build prompt for incident response guidance"""
    query = f"""Provide incident response guidance for:

{incident_description}

Please provide:
1. Recommended response procedures
2. Step-by-step actions
3. Escalation criteria
4. Containment strategies
5. Relevant playbook references"""
    
    return build_rag_prompt(query, context, prompt_type="incident_response")


def build_threat_intel_prompt(
    threat_query: str,
    context: str
) -> str:
    """Build prompt for threat intelligence query"""
    query = f"""Provide threat intelligence about: {threat_query}

Please include:
1. Threat context and background
2. Attack techniques and tactics
3. Detection methods
4. Prevention measures
5. MITRE ATT&CK mappings"""
    
    return build_rag_prompt(query, context, prompt_type="threat_intel")


# Query classification prompts

QUERY_CLASSIFIER_PROMPT = """Classify the following security query into one of these categories:
1. alert_explanation - User wants to understand a security alert
2. cve_lookup - User is asking about a specific CVE or vulnerability
3. incident_response - User needs guidance on responding to an incident
4. threat_intel - User wants general threat intelligence information
5. general - General security question

Query: {query}

Respond with only the category name."""


def classify_query_type(query: str) -> str:
    """
    Classify query type for appropriate prompt selection
    
    Args:
        query: User query
        
    Returns:
        Query type classification
    """
    query_lower = query.lower()
    
    # Simple rule-based classification
    if any(word in query_lower for word in ['alert', 'detection', 'triggered', 'fired']):
        return 'alert_explanation'
    
    elif any(word in query_lower for word in ['cve-', 'vulnerability', 'cvss', 'exploit']):
        return 'cve_lookup'
    
    elif any(word in query_lower for word in ['respond', 'incident', 'playbook', 'procedure', 'steps']):
        return 'incident_response'
    
    elif any(word in query_lower for word in ['threat', 'attack', 'technique', 'tactic', 'mitre']):
        return 'threat_intel'
    
    else:
        return 'general'


# Response formatting templates

def format_response_with_citations(
    answer: str,
    sources: list
) -> Dict[str, Any]:
    """
    Format LLM response with proper citations
    
    Args:
        answer: LLM generated answer
        sources: List of source documents
        
    Returns:
        Formatted response dictionary
    """
    return {
        "answer": answer,
        "sources": sources,
        "citations": extract_citations(answer),
        "has_citations": "[Source" in answer
    }


def extract_citations(text: str) -> list:
    """Extract citation references from text"""
    import re
    citations = re.findall(r'\[Source (\d+)\]', text)
    return [int(c) for c in citations]
