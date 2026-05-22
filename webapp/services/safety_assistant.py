from __future__ import annotations

from ml.labels import SAFE_LABEL, label_title, label_tone, normalize_label

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

GREETING_WORDS = {
    "hi",
    "hello",
    "hey",
    "good morning",
    "good afternoon",
    "good evening",
    "habari",
    "niaje",
    "mambo",
    "sasa",
}

HELP_WORDS = {
    "help",
    "what can you do",
    "how can you help",
    "what do you do",
    "how does this work",
    "can you help",
}

THANK_WORDS = {"thanks", "thank you", "asante", "shukran"}


def _matches_any(text: str, phrases: set[str]) -> bool:
    lowered = text.lower().strip(" ?.!,")
    return any(phrase in lowered for phrase in phrases)


def _intro_message(audience_key: str) -> str:
    if audience_key == "child":
        return (
            "Hi, I am the Cyber Mzazi AI Safety Assistant. I can help you understand a message, "
            "spot unsafe online behavior, explain why something may be risky, and suggest what to do next. "
            "Tell me what happened or paste the message you are worried about."
        )
    return (
        "Hello, I am the Cyber Mzazi AI Safety Assistant. I can explain suspicious messages, slang, links, "
        "online risks, and recommended parent actions. Paste the message or describe the situation, and I will "
        "classify the risk and suggest next steps."
    )


def _thanks_message(audience_key: str) -> str:
    if audience_key == "child":
        return "You are welcome. If something online feels confusing, scary, secretive, or pressuring, tell me what happened and I will help you think through it."
    return "You are welcome. Share any message, link, slang, or incident and I will help you assess the risk and decide what to do next."


def _solution_text(label: str, risk_level: str, audience_key: str, guidance: str) -> str:
    title = label_title(label).lower()
    if label == SAFE_LABEL:
        if audience_key == "child":
            return (
                "This looks low risk from the text provided. Still be careful: do not share passwords, private photos, "
                "school details, location, or verification codes. If the person keeps pressuring you, tell a trusted adult."
            )
        return (
            "This looks low risk from the text provided. Keep the conversation open, check the wider context, "
            "and remind the child not to share private details or one-time codes."
        )

    if audience_key == "child":
        return (
            f"This may be {title}, so the safest choice is to pause before replying. {guidance} "
            "If you feel scared, pressured, or asked to keep secrets, get help from your parent/guardian or another trusted adult now."
        )
    return (
        f"This may be {title} and the risk level is {risk_level}. {guidance} "
        "Talk to the child calmly, save evidence, block/report if needed, and review whether the sender has contacted them before."
    )


def build_safety_assistant_response(prompt: str, *, audience: str, family_id: int | None = None) -> dict:
    cleaned_prompt = " ".join(str(prompt or "").split())
    if not cleaned_prompt:
        return {
            "ok": False,
            "error": "Enter a message or question first.",
        }

    audience_key = "child" if audience == "child" else "parent"
    if _matches_any(cleaned_prompt, GREETING_WORDS) or _matches_any(cleaned_prompt, HELP_WORDS):
        return {
            "ok": True,
            "label": SAFE_LABEL,
            "label_title": "Conversation",
            "tone": "safe",
            "confidence": 1.0,
            "risk_level": "none",
            "indicators": "conversation",
            "explanation": _intro_message(audience_key),
            "guidance": "Describe the problem in your own words or paste the message you want me to check.",
            "assistant_message": _intro_message(audience_key),
            "next_steps": [
                "Paste the message, link, screenshot text, or slang you want explained.",
                "Tell me who sent it and whether they asked for secrecy, money, photos, links, or codes.",
                "I will explain the risk and give a practical next step.",
            ],
            "should_alert_guardian": False,
            "response_type": "greeting",
        }

    if _matches_any(cleaned_prompt, THANK_WORDS):
        return {
            "ok": True,
            "label": SAFE_LABEL,
            "label_title": "Conversation",
            "tone": "safe",
            "confidence": 1.0,
            "risk_level": "none",
            "indicators": "conversation",
            "explanation": _thanks_message(audience_key),
            "guidance": "You can continue the conversation by describing the next concern.",
            "assistant_message": _thanks_message(audience_key),
            "next_steps": [
                "Ask another question if you are unsure.",
                "Share the exact words or link if you want a better risk check.",
            ],
            "should_alert_guardian": False,
            "response_type": "conversation",
        }

    try:
        prediction = predict_message(cleaned_prompt, family_id=family_id)
        label = normalize_label(prediction.label)
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
    solution = _solution_text(label, risk_level, audience_key, guidance)
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
        "assistant_message": f"{explanation} {solution}",
        "next_steps": next_steps,
        "should_alert_guardian": audience_key == "child" and risk_level == "high",
        "response_type": "safety_analysis",
    }
