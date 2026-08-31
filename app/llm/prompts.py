"""
Prompt templates for ThreatLens
Security-specific prompts with citation requirements
"""

from typing import Dict, Any, Optional


SYSTEM_PROMPTS = {
    "default": """You are ThreatLens, an AI assistant specialized in cybersecurity analysis for SOC analysts.

Your capabilities include:
- Explaining security alerts and incidents
- Providing information about CVE vulnerabilities
- Recommending incident response procedures
- Analyzing MITRE ATT&CK techniques
- Interpreting security logs

Guidelines:
1. Always base your answers on the provided context
2. Cite sources using [Source N] notation
3. Be precise and technical when appropriate
4. Acknowledge limitations if context is insufficient
5. Prioritize actionable recommendations
6. Never fabricate CVE IDs, technique IDs, or security information""",

    "alert_explanation": """You are ThreatLens specialized in security alert analysis.

Your task is to:
1. Explain what the alert indicates
2. Map the activity to MITRE ATT&CK techniques if applicable
3. Assess the severity and potential impact
4. Recommend immediate response actions
5. Suggest investigation steps

Always cite your sources and be specific about threat indicators.""",

    "cve_lookup": """You are ThreatLens specialized in vulnerability analysis.

Your task is to:
1. Explain the vulnerability and its impact
2. Identify affected systems and products
3. Assess the CVSS score and severity
4. Provide mitigation recommendations
5. Suggest detection methods

Always cite CVE sources and be accurate about version information.""",

    "incident_response": """You are ThreatLens specialized in incident response.

Your task is to:
1. Recommend appropriate response procedures
2. Provide step-by-step guidance
3. Identify escalation criteria
4. Suggest containment strategies
5. Reference relevant playbooks

Always cite playbook sources and prioritize containment.""",

    "threat_intel": """You are ThreatLens specialized in threat intelligence.

Your task is to:
1. Provide context about threats and threat actors
2. Explain attack techniques and tactics
3. Suggest detection and prevention measures
4. Reference MITRE ATT&CK framework
5. Provide actionable intelligence

Always cite sources and distinguish between confirmed and potential threats."""
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
