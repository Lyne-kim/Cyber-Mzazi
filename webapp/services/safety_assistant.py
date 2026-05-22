from __future__ import annotations

from ml.labels import label_title, label_tone

from .prediction_service import PredictionUnavailable, predict_message


HIGH_RISK_LABELS = {
    "grooming",
    "sexual_content",
    "sextortion",
    "phishing",
    "scam",
    "cyberbullying",
    "violence",
}


LABEL_GUIDANCE = {
    "safe": {
        "child": "This looks low risk. Still avoid sharing private information, passwords, photos, school details, or location.",
        "parent": "This looks low risk. Keep context in mind and continue encouraging open reporting.",
    },
    "grooming": {
        "child": "Do not meet, move to a private chat, or share photos. Block the person and tell your parent or another trusted adult.",
        "parent": "Check whether the person is asking for secrecy, private contact, photos, gifts, or meetings. Preserve evidence and block/report the account.",
    },
    "sexual_content": {
        "child": "Do not reply or send anything private. Save the message if you can and ask a trusted adult for help.",
        "parent": "Review context carefully, preserve evidence, and report the account or platform if a child is being sexualized.",
    },
    "sextortion": {
        "child": "Do not send photos, money, or more messages. Tell a trusted adult now. You are not in trouble for asking for help.",
        "parent": "Treat this as urgent. Preserve evidence, stop contact, report the account, and consider local law-enforcement or child-protection support.",
    },
    "phishing": {
        "child": "Do not tap links, enter passwords, or download files. Ask your parent to check it first.",
        "parent": "Avoid opening the link on the child device. Check the sender, URL, urgency language, and account-security claims.",
    },
    "scam": {
        "child": "Do not send money, codes, airtime, or personal details. Ask your parent before responding.",
        "parent": "Look for prize, job, investment, fee, or urgency tactics. Block/report and warn the child not to share one-time codes.",
    },
    "cyberbullying": {
        "child": "You do not have to answer hurtful messages. Save evidence, block if needed, and talk to a trusted adult.",
        "parent": "Support the child first, preserve evidence, block/report repeat offenders, and involve the school/platform when needed.",
    },
    "violence": {
        "child": "Move away from the conversation and tell a trusted adult immediately if anyone threatens harm.",
        "parent": "Assess immediacy. If there is a real threat, escalate to guardians, school, platform safety tools, or emergency services.",
    },
    "misinformation": {
        "child": "Do not forward it quickly. Ask an adult and check trusted sources first.",
        "parent": "Help the child verify the claim using reliable sources and explain emotional or sensational manipulation.",
    },
    "betting": {
        "child": "Do not join betting groups or share payment details. Ask your parent before clicking anything about money or prizes.",
        "parent": "Review access to betting content, payments, and app permissions. Discuss financial pressure and age restrictions.",
    },
}


def build_safety_assistant_response(prompt: str, *, audience: str, family_id: int | None = None) -> dict:
    cleaned_prompt = " ".join(str(prompt or "").split())
    if not cleaned_prompt:
        return {
            "ok": False,
            "error": "Enter a message or question first.",
        }

    audience_key = "child" if audience == "child" else "parent"
    try:
        prediction = predict_message(cleaned_prompt, family_id=family_id)
        label = prediction.label
        confidence = prediction.confidence
        indicators = prediction.risk_indicators
    except PredictionUnavailable as exc:
        return {
            "ok": False,
            "error": str(exc),
        }

    title = label_title(label)
    guidance = LABEL_GUIDANCE.get(label, LABEL_GUIDANCE["safe"])[audience_key]
    tone = label_tone(label)
    risk_level = "high" if label in HIGH_RISK_LABELS and confidence >= 0.55 else "low" if label == "safe" else "medium"
    explanation = (
        f"I classified this as {title.lower()} with {confidence:.0%} confidence. "
        f"The main signals were: {indicators or 'general wording and context'}."
    )
    if audience_key == "child":
        next_steps = [
            "Do not share passwords, private photos, money, school details, or your location.",
            "Block or stop replying if the person pressures you, scares you, or asks for secrecy.",
            "Tell your parent/guardian or another trusted adult if it feels unsafe.",
        ]
    else:
        next_steps = [
            "Ask the child what happened without blame.",
            "Preserve screenshots or message text before blocking/reporting.",
            "Review privacy settings and repeat-contact patterns.",
        ]

    return {
        "ok": True,
        "label": label,
        "label_title": title,
        "tone": tone,
        "confidence": confidence,
        "risk_level": risk_level,
        "indicators": indicators,
        "explanation": explanation,
        "guidance": guidance,
        "next_steps": next_steps,
        "should_alert_guardian": audience_key == "child" and risk_level == "high",
    }
