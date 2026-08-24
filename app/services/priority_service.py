def calculate_priority(title: str, description: str, category: str) -> str:
    """
    Evaluates ticket title, description, and category to determine priority:
    - critical: Emergency category or keywords: outage, system down, server down, security breach, data loss
    - high: Billing category or keywords: payment failed, cannot login, urgent, broken
    - medium: Technical Issue category or keywords: bug, slow, error, glitch
    - low: General Inquiry, Feedback, or default fallback
    """
    text = f"{title} {description}".lower()
    cat = category.strip().lower() if category else ""

    # 1. Critical rule check
    critical_keywords = ["outage", "system down", "server down", "security breach", "data loss"]
    if cat == "emergency" or any(kw in text for kw in critical_keywords):
        return "critical"

    # 2. High rule check
    high_keywords = ["payment failed", "cannot login", "urgent", "broken"]
    if cat == "billing" or any(kw in text for kw in high_keywords):
        return "high"

    # 3. Medium rule check
    medium_keywords = ["bug", "slow", "error", "glitch"]
    if cat == "technical issue" or any(kw in text for kw in medium_keywords):
        return "medium"

    # 4. Low fallback
    return "low"
