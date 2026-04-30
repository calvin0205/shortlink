from fastapi import APIRouter, Depends, Request
from ..models.assistant import AssistantQuery, AssistantResponse
from ..dependencies import get_current_user
from ..ai_engine import process_query
from ..storage.incidents import get_incident
from ..storage.audit import create_audit_log
import os

router = APIRouter(prefix="/api/assistant", tags=["assistant"])


@router.post("/query", response_model=AssistantResponse)
async def query_assistant(
    body: AssistantQuery,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    # Optionally fetch incident context
    incident = None
    if body.incident_id:
        incident = get_incident(body.incident_id)

    # Try LLM first if API key configured
    if os.getenv("ANTHROPIC_API_KEY"):
        result = await _query_claude(body.message, incident)
    else:
        result = process_query(body.message, incident)

    # Audit log
    create_audit_log(
        user_id=current_user["user_id"],
        user_email=current_user["email"],
        action="AI_QUERY",
        resource_type="ASSISTANT",
        resource_id=body.incident_id or "general",
        detail=f"Query: {body.message[:100]}",
        ip_address=request.client.host if request.client else "unknown",
    )

    return AssistantResponse(**result)


@router.get("/suggested-queries")
async def get_suggested_queries(current_user: dict = Depends(get_current_user)):
    """Return suggested queries for the frontend."""
    return {
        "queries": [
            "What should I do about an unauthorized access attempt on a PLC?",
            "How do I respond to firmware tampering?",
            "Explain the risk scoring methodology",
            "What does a protocol anomaly indicate?",
            "How to handle sensor data manipulation?",
            "What are the recommended steps for network scan detection?",
            "How dangerous is a brute force attack on an HMI?",
            "What is IEC 62443 and why is it important?",
        ]
    }


async def _query_claude(message: str, incident=None) -> dict:
    """Query Claude API for AI-powered responses."""
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

        context = ""
        if incident:
            context = f"""
Incident Context:
- Title: {incident.get('title')}
- Severity: {incident.get('severity')}
- Device: {incident.get('device_name')}
- Risk Score: {incident.get('risk_score')}
- Status: {incident.get('status')}
- Description: {incident.get('description')}
"""

        system_prompt = """You are an OT/ICS (Operational Technology / Industrial Control Systems) security expert assistant for the OT Sentinel platform.
You provide expert analysis of security incidents affecting industrial devices like PLCs, HMIs, RTUs, Gateways, and Sensors.
Your responses should be:
1. Technically accurate and specific to OT/ICS environments
2. Reference relevant standards (IEC 62443, NIST SP 800-82, NERC CIP)
3. Include concrete, actionable recommendations
4. Consider the safety implications of OT security incidents

Always respond in this JSON format:
{
  "answer": "detailed analysis",
  "recommendations": ["step 1", "step 2", ...],
  "references": ["standard 1", "standard 2"],
  "severity_assessment": "assessment string"
}"""

        user_message = f"{context}\n\nQuestion: {message}" if context else message

        response = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=1024,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}]
        )

        import json
        content = response.content[0].text
        # Try to parse JSON response
        try:
            parsed = json.loads(content)
            parsed["source"] = "llm"
            parsed["incident_context"] = {
                "incident_id": incident.get("incident_id", ""),
                "title": incident.get("title", ""),
                "severity": incident.get("severity", ""),
                "device_name": incident.get("device_name", ""),
                "status": incident.get("status", ""),
                "risk_score": int(incident.get("risk_score", 0)),
            } if incident else None
            return parsed
        except json.JSONDecodeError:
            # Claude didn't return JSON, wrap the response
            return {
                "answer": content,
                "recommendations": [],
                "references": [],
                "severity_assessment": None,
                "incident_context": None,
                "source": "llm",
            }
    except Exception:
        # Fallback to rule-based
        return process_query(message, incident)
