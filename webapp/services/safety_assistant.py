from __future__ import annotations

import re

from ml.labels import SAFE_LABEL, label_title, label_tone, normalize_label

from .prediction_service import PredictionUnavailable, predict_message
from .resource_library import search_resource_chunks, summarize_resource_library


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

DEFINITION_PATTERNS = (
    "what is ",
    "what's ",
    "what does ",
    "what do you mean by ",
    "meaning of ",
    "define ",
    "explain ",
    "tell me about ",
)

ADVICE_PATTERNS = (
    "what should i do",
    "what can i do",
    "how do i handle",
    "how should i respond",
    "what should we do",
    "someone is",
    "someone asked",
    "someone wants",
    "asking for",
    "asked for",
    "wants me to",
    "they asked",
    "they want",
    "i clicked",
    "i shared",
    "i sent",
    "i received",
    "am being",
    "being threatened",
    "threatening me",
)

CLASSIFICATION_PATTERNS = (
    "is this safe",
    "is this risky",
    "is this dangerous",
    "classify",
    "analyse this",
    "analyze this",
    "check this message",
    "check this link",
    "rate this",
    "what category",
)

PRIZE_LINK_PATTERNS = (
    "won a prize",
    "win a prize",
    "claim your prize",
    "claim prize",
    "free prize",
    "congratulations",
    "you have won",
    "winner",
    "giveaway",
)

UNKNOWN_CONTEXT_MARKERS = (
    "someone tells me",
    "someone told me",
    "they told me",
    "what does",
    "what mean",
    "meaning",
)

RESOURCE_SUMMARY_PATTERNS = (
    "summarize the book",
    "summarise the book",
    "summary of the book",
    "summarize safety resources",
    "summarise safety resources",
    "summarize the resource",
    "summarise the resource",
    "what is in the book",
    "what books are in safety resources",
    "books in safety resources",
    "resources uploaded",
)

URL_RE = re.compile(r"https?://|www\.|bit\.ly|t\.co|tinyurl|wa\.me", re.I)
PHONE_OR_CODE_RE = re.compile(r"\b(?:otp|pin|code|password|login|verify|account|mpesa|m-pesa)\b", re.I)


SAFETY_TOPICS = {
    "sextortion": {
        "aliases": ("sextortion", "blackmail photos", "private photos", "nudes", "leaking photos", "explicit photos"),
        "label": "sextortion",
        "risk": "high",
        "definition": "Sextortion is online blackmail where someone threatens to share private, intimate, or sexual images, videos, chats, or rumors unless the victim sends money, more images, or obeys them.",
        "child_advice": "Do not send more images, money, passwords, or codes. Save screenshots, stop replying, block/report the account, and tell a parent, guardian, teacher, or another trusted adult immediately.",
        "parent_advice": "Stay calm and avoid blaming the child. Preserve evidence, stop contact, report the account to the platform, and escalate to child-protection or law-enforcement support if there are threats or intimate images.",
        "signs": "Threats, shame, secrecy, demands for money, demands for more images, or pressure to move to private chat.",
    },
    "grooming": {
        "aliases": ("grooming", "online predator", "predator", "secret friend", "meet up", "older person", "private chat"),
        "label": "grooming",
        "risk": "high",
        "definition": "Grooming is when someone builds trust with a child online so they can manipulate, exploit, sexualize, isolate, or meet the child.",
        "child_advice": "Do not keep secrets for online contacts, meet them, move to private apps, or send photos. Save the messages and tell a trusted adult.",
        "parent_advice": "Look for secrecy, gifts, flattery, private contact, age gaps, sexual jokes, photo requests, or meeting plans. Preserve evidence and report/block the account.",
        "signs": "Secrecy, gifts, compliments, private chats, requests for photos, asking where the child lives or goes to school.",
    },
    "phishing": {
        "aliases": ("phishing", "fake login", "fake website", "suspicious link", "harmful link", "verify account", "claim prize"),
        "label": "phishing",
        "risk": "high",
        "definition": "Phishing is a trick that uses fake messages, websites, links, or login pages to steal passwords, verification codes, money, or personal information.",
        "child_advice": "Do not tap the link, log in, download files, or share codes. Ask a parent or guardian to check it first.",
        "parent_advice": "Check the real domain, sender, urgency language, spelling, and whether the message asks for passwords or one-time codes. Change passwords if credentials were entered.",
        "signs": "Urgent account warnings, prizes, fake delivery messages, shortened links, password/code requests, or odd web addresses.",
    },
    "scam": {
        "aliases": ("scam", "fraud", "con", "fake prize", "investment", "job offer", "airtime", "free money", "giveaway"),
        "label": "scam",
        "risk": "high",
        "definition": "A scam is a dishonest message or offer designed to steal money, airtime, accounts, codes, identity details, or trust.",
        "child_advice": "Do not send money, airtime, photos of documents, or verification codes. Ask a parent before replying.",
        "parent_advice": "Block/report the sender, warn the child about urgency and prize tactics, and review whether payment or account details were exposed.",
        "signs": "Too-good-to-be-true offers, pressure to act fast, secret deals, fees before rewards, codes, or payment requests.",
    },
    "cyberbullying": {
        "aliases": ("cyberbullying", "bullying", "harassment", "insults", "hate", "body shaming", "rumors", "mocking"),
        "label": "cyberbullying",
        "risk": "medium",
        "definition": "Cyberbullying is repeated or harmful online behavior meant to embarrass, threaten, exclude, insult, or intimidate someone.",
        "child_advice": "Do not reply when angry. Save evidence, block/report the person if needed, and tell a trusted adult. It is not your fault.",
        "parent_advice": "Support the child emotionally first, preserve evidence, report repeat abuse, and involve the school or platform when appropriate.",
        "signs": "Repeated insults, threats, humiliation, group exclusion, rumor spreading, fake accounts, or pressure to self-harm.",
    },
    "misinformation": {
        "aliases": ("misinformation", "fake news", "rumor", "hoax", "false information", "deepfake"),
        "label": "misinformation",
        "risk": "medium",
        "definition": "Misinformation is false or misleading information that can spread quickly, especially when it is emotional, shocking, political, or health-related.",
        "child_advice": "Do not forward it quickly. Check trusted sources, look for the original source, and ask an adult if unsure.",
        "parent_advice": "Teach the child to pause, verify sources, compare reliable outlets, and watch for edited images, fake accounts, and emotional manipulation.",
        "signs": "No source, dramatic claims, pressure to share, edited screenshots, fake celebrity posts, or claims only one page is reporting.",
    },
    "malware": {
        "aliases": ("malware", "virus", "spyware", "apk", "download app", "install this", "file attachment"),
        "label": "phishing",
        "risk": "high",
        "definition": "Malware is harmful software that can steal data, spy on activity, damage a device, or take control of accounts.",
        "child_advice": "Do not install unknown apps or open unexpected attachments. Ask a parent before downloading anything.",
        "parent_advice": "Remove suspicious apps/files, update the device, scan with trusted security tools, and change passwords if accounts may be exposed.",
        "signs": "Unknown APKs, unexpected attachments, fake updates, popups, battery drain, unusual permissions, or apps from outside trusted stores.",
    },
    "privacy": {
        "aliases": ("privacy", "personal information", "private information", "location", "address", "school", "phone number"),
        "label": "safe",
        "risk": "medium",
        "definition": "Online privacy means controlling who can see personal information such as location, school, phone number, family details, photos, passwords, and routines.",
        "child_advice": "Do not share your address, school, location, phone number, passwords, private photos, or daily routine with online contacts.",
        "parent_advice": "Review app privacy settings, location sharing, profile visibility, friend requests, and what personal details appear in posts or bios.",
        "signs": "Requests for school, home, live location, phone number, family details, or private photos.",
    },
    "passwords": {
        "aliases": ("password", "passwords", "passcode", "otp", "verification code", "2fa", "two factor", "one time code"),
        "label": "phishing",
        "risk": "high",
        "definition": "Passwords and verification codes prove account ownership. Anyone asking for them may be trying to take over the account.",
        "child_advice": "Never share passwords or verification codes, even with friends. If you shared one, tell a parent quickly so the account can be protected.",
        "parent_advice": "Change exposed passwords, revoke unknown sessions, enable two-factor authentication, and teach that support staff never need one-time codes in chat.",
        "signs": "Requests for OTP, login code, password reset link, account recovery, or screen sharing.",
    },
    "impersonation": {
        "aliases": ("impersonation", "fake account", "catfish", "catfishing", "pretending", "fake profile"),
        "label": "scam",
        "risk": "medium",
        "definition": "Impersonation is when someone pretends to be another person, brand, school, friend, celebrity, or support agent to gain trust.",
        "child_advice": "Do not share private details or money. Verify through another trusted channel before believing the account.",
        "parent_advice": "Check account age, username spelling, mutual contacts, profile history, and whether the person avoids video/voice verification.",
        "signs": "New accounts, copied photos, urgent requests, secrecy, money requests, or inconsistent identity details.",
    },
    "digital_footprint": {
        "aliases": ("digital footprint", "online reputation", "posted online", "delete post", "old posts"),
        "label": "safe",
        "risk": "low",
        "definition": "A digital footprint is the trail of posts, comments, photos, searches, accounts, and shared content connected to someone online.",
        "child_advice": "Before posting, ask: would I be okay if a parent, teacher, future school, or stranger saw this later?",
        "parent_advice": "Help the child review public profiles, old posts, usernames, privacy settings, and content that reveals location or identity.",
        "signs": "Public profiles, oversharing, identifying details, screenshots, or posts that can be copied even after deletion.",
    },
    "screen_time": {
        "aliases": ("screen time", "too much phone", "addicted", "sleep", "gaming too much"),
        "label": "safe",
        "risk": "low",
        "definition": "Screen-time safety is about balancing online activity with sleep, school, movement, family time, and emotional wellbeing.",
        "child_advice": "Take breaks, protect sleep, and talk to an adult if an app makes you feel anxious, angry, or unable to stop.",
        "parent_advice": "Use consistent routines, device-free sleep time, collaborative limits, and conversations about mood rather than punishment only.",
        "signs": "Lost sleep, secrecy, anger when disconnected, falling grades, anxiety, or withdrawal from offline activities.",
    },
    "reporting": {
        "aliases": ("report", "reporting", "evidence", "screenshot", "block", "where to report"),
        "label": "safe",
        "risk": "low",
        "definition": "Reporting means using platform tools, trusted adults, schools, guardians, or authorities to stop unsafe behavior and preserve evidence.",
        "child_advice": "Take screenshots if safe, do not delete important evidence too quickly, block/report the account, and tell a trusted adult.",
        "parent_advice": "Capture usernames, dates, links, screenshots, and message context. Report through the platform and escalate if threats, exploitation, or extortion are involved.",
        "signs": "Threats, repeated harassment, private image abuse, scams, suspicious links, or pressure for secrecy.",
    },
}

GENERAL_SAFETY_TOPICS = (
    "sextortion",
    "grooming",
    "phishing",
    "scam",
    "cyberbullying",
    "misinformation",
    "malware",
    "privacy",
    "passwords",
    "impersonation",
    "digital_footprint",
    "screen_time",
    "reporting",
)


def _matches_any(text: str, phrases: set[str]) -> bool:
    lowered = text.lower().strip(" ?.!,")
    return any(
        lowered == phrase
        or lowered.startswith(f"{phrase} ")
        or lowered.endswith(f" {phrase}")
        for phrase in phrases
    )


def _contains_any(text: str, phrases: tuple[str, ...] | set[str]) -> bool:
    lowered = text.lower()
    return any(phrase in lowered for phrase in phrases)


def _response(
    *,
    label: str,
    label_title_value: str,
    tone: str,
    confidence: float,
    risk_level: str,
    indicators: str,
    explanation: str,
    guidance: str,
    assistant_message: str,
    next_steps: list[str],
    response_type: str,
    should_alert_guardian: bool = False,
) -> dict:
    return {
        "ok": True,
        "label": label,
        "label_title": label_title_value,
        "tone": tone,
        "confidence": confidence,
        "risk_level": risk_level,
        "indicators": indicators,
        "explanation": explanation,
        "guidance": guidance,
        "assistant_message": assistant_message,
        "next_steps": next_steps,
        "should_alert_guardian": should_alert_guardian,
        "response_type": response_type,
    }


def _with_resource_context(result: dict, resource_matches: list[dict]) -> dict:
    if not resource_matches or not result.get("ok"):
        result["resource_matches"] = []
        return result

    context_lines = []
    for match in resource_matches:
        excerpt = " ".join(str(match["text"]).split())[:420]
        context_lines.append(f"{match['title']}: {excerpt}")

    result["resource_matches"] = resource_matches
    result["assistant_message"] = (
        f"{result.get('assistant_message', '')} "
        "I also found related guidance in the Cyber Mzazi resource library: "
        + " ".join(context_lines)
    ).strip()
    next_steps = list(result.get("next_steps") or [])
    next_steps.append("Open the Safety Resources page to read or download the matched resource.")
    result["next_steps"] = next_steps
    return result


def _intro_message(audience_key: str) -> str:
    if audience_key == "child":
        return (
            "Hi, I am the Cyber Mzazi AI Safety Assistant. I can explain online safety words, "
            "help you understand a message, spot scams or bullying, and suggest what to do next. "
            "You can ask a question or paste the message you are worried about."
        )
    return (
        "Hello, I am the Cyber Mzazi AI Safety Assistant. I can explain online risks, slang, links, "
        "suspicious messages, child safety incidents, and practical parent actions. Ask a question, "
        "describe what happened, or paste the message you want checked."
    )


def _thanks_message(audience_key: str) -> str:
    if audience_key == "child":
        return "You are welcome. If something online feels confusing, scary, secretive, or pressuring, tell me what happened and I will help you think through it."
    return "You are welcome. Share any message, link, slang, or incident and I will help you assess the risk and decide what to do next."


def _detect_topic(text: str) -> tuple[str | None, dict | None]:
    lowered = text.lower()
    for key, topic in SAFETY_TOPICS.items():
        if any(alias in lowered for alias in topic["aliases"]):
            return key, topic
    return None, None


def _detect_intent(text: str) -> str:
    lowered = text.lower().strip()
    if _matches_any(lowered, GREETING_WORDS) or _matches_any(lowered, HELP_WORDS):
        return "greeting"
    if _matches_any(lowered, THANK_WORDS):
        return "thanks"
    if _contains_any(lowered, RESOURCE_SUMMARY_PATTERNS):
        return "resource_summary"
    if _contains_any(lowered, DEFINITION_PATTERNS):
        return "education"
    if _contains_any(lowered, ADVICE_PATTERNS):
        return "advice"
    if _contains_any(lowered, CLASSIFICATION_PATTERNS):
        return "classification"
    if _contains_any(lowered, PRIZE_LINK_PATTERNS) and ("link" in lowered or URL_RE.search(lowered)):
        return "classification"
    if URL_RE.search(lowered) or PHONE_OR_CODE_RE.search(lowered):
        return "classification"
    if len(lowered.split()) >= 16:
        return "classification"
    return "education"


def _resource_summary_response(prompt: str, audience_key: str, family_id: int | None) -> dict:
    summary = summarize_resource_library(prompt, audience=audience_key, family_id=family_id)
    if not summary:
        message = (
            "I do not see any approved books in the Safety Resources library yet. "
            "Ask the developer to upload a book, or use the Safety Resources request form to suggest one."
        )
        return _response(
            label=SAFE_LABEL,
            label_title_value="Safety Resources",
            tone="safe",
            confidence=1.0,
            risk_level="none",
            indicators="resource_library_empty",
            explanation=message,
            guidance="Upload or request a safety resource first.",
            assistant_message=message,
            next_steps=[
                "Open Safety Resources to see the current approved books.",
                "Use the request form if you want a specific topic or book added.",
            ],
            response_type="resource_summary",
        )

    lines = []
    for item in summary["documents"]:
        lines.append(
            f"{item['title']} ({item['topic']}): {item['summary']}"
        )
    message = (
        "Here is a summary of the approved Safety Resources I can access: "
        + " ".join(lines)
    )
    return _response(
        label=SAFE_LABEL,
        label_title_value="Safety Resources",
        tone="safe",
        confidence=1.0,
        risk_level="none",
        indicators="resource_library_summary",
        explanation=message,
        guidance="Use the Safety Resources page to open or download the full book.",
        assistant_message=message,
        next_steps=[
            "Open Safety Resources to read or download the full book.",
            "Ask a more specific question about one topic in the book for a focused answer.",
            "Request another book if the library does not cover the topic you need.",
        ],
        response_type="resource_summary",
    )


def _education_response(prompt: str, audience_key: str) -> dict:
    topic_key, topic = _detect_topic(prompt)
    if not topic:
        lowered = prompt.lower()
        if "knowledge is power" in lowered:
            message = (
                "\"Knowledge is power\" means learning and understanding things can help you make better choices. "
                "By itself, that sentence is safe and positive. Be careful only if someone uses it to pressure you into clicking a link, "
                "sharing private information, keeping secrets, or doing something uncomfortable."
            )
        elif _contains_any(lowered, UNKNOWN_CONTEXT_MARKERS):
            message = (
                "I do not see a clear danger in that phrase by itself. Tell me the exact full message, who sent it, "
                "and whether they asked for a link click, password, code, money, photos, secrecy, or a private chat. "
                "Those details help me decide whether it is safe."
            )
        else:
            topics = ", ".join(topic.replace("_", " ") for topic in GENERAL_SAFETY_TOPICS)
            message = (
                "I can help with online safety topics such as "
                f"{topics}. Ask me to explain one of these, or paste a message/link if you want me to check whether it is risky."
            )
        return _response(
            label=SAFE_LABEL,
            label_title_value="Online Safety",
            tone="safe",
            confidence=1.0,
            risk_level="none",
            indicators="education_request",
            explanation=message,
            guidance="Ask a specific question or share the situation you want help with.",
            assistant_message=message,
            next_steps=[
                "Ask: what is phishing, grooming, sextortion, cyberbullying, or a scam?",
                "Paste a suspicious message if you want it analysed.",
                "Tell me what happened if you need practical next steps.",
            ],
            response_type="education",
        )

    advice_key = "child_advice" if audience_key == "child" else "parent_advice"
    message = (
        f"{topic['definition']} Common warning signs include: {topic['signs']} "
        f"What to do: {topic[advice_key]}"
    )
    label = str(topic["label"])
    risk = str(topic["risk"])
    return _response(
        label=label,
        label_title_value=label_title(label) if label != SAFE_LABEL else "Online Safety",
        tone=label_tone(label),
        confidence=1.0,
        risk_level=risk,
        indicators=f"{topic_key}_education",
        explanation=topic["definition"],
        guidance=topic[advice_key],
        assistant_message=message,
        next_steps=[
            "Save evidence if this is happening to you or your child.",
            "Block or report unsafe accounts when needed.",
            "Ask me to check a specific message if you want a risk analysis.",
        ],
        should_alert_guardian=False,
        response_type="education",
    )


def _advice_response(prompt: str, audience_key: str) -> dict:
    topic_key, topic = _detect_topic(prompt)
    if not topic:
        topic_key = "reporting"
        topic = SAFETY_TOPICS[topic_key]

    advice_key = "child_advice" if audience_key == "child" else "parent_advice"
    label = str(topic["label"])
    risk = str(topic["risk"])
    if risk == "high":
        lead = "This sounds potentially serious. "
    elif risk == "medium":
        lead = "This may need careful handling. "
    else:
        lead = "Here is a safe way to handle it. "

    message = (
        f"{lead}{topic[advice_key]} "
        f"Why it matters: {topic['definition']} Warning signs to watch for: {topic['signs']}"
    )
    next_steps = [
        "Pause before replying or clicking anything.",
        "Save screenshots, usernames, links, dates, and message text.",
        "Block/report the account if there is pressure, threats, sexual content, scams, or repeated harassment.",
    ]
    if audience_key == "child":
        next_steps.insert(0, "Tell a parent, guardian, teacher, or trusted adult if you feel scared or pressured.")
    else:
        next_steps.insert(0, "Talk to the child calmly and avoid blame so they keep sharing concerns.")

    return _response(
        label=label,
        label_title_value=label_title(label) if label != SAFE_LABEL else "Online Safety",
        tone=label_tone(label),
        confidence=1.0,
        risk_level=risk,
        indicators=f"{topic_key}_advice",
        explanation=topic["definition"],
        guidance=topic[advice_key],
        assistant_message=message,
        next_steps=next_steps,
        should_alert_guardian=audience_key == "child" and risk == "high",
        response_type="advice",
    )


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


def _classification_response(prompt: str, audience_key: str, family_id: int | None) -> dict:
    lowered = prompt.lower()
    if _contains_any(lowered, PRIZE_LINK_PATTERNS) and ("link" in lowered or URL_RE.search(lowered)):
        label = "phishing"
        title = label_title(label)
        guidance = LABEL_GUIDANCE[label][audience_key]
        message = (
            "This sounds risky because prize messages with links are a common scam or phishing trick. "
            "They often try to make you click quickly, enter a password, share a code, or give personal information."
        )
        return _response(
            label=label,
            label_title_value=title,
            tone=label_tone(label),
            confidence=0.9,
            risk_level="high",
            indicators="prize_offer,suspicious_link,urgency_manipulation",
            explanation=message,
            guidance=guidance,
            assistant_message=f"{message} {guidance}",
            next_steps=[
                "Do not tap the link or enter any password, code, phone number, or payment details.",
                "Show it to a parent/guardian before doing anything.",
                "Block or report the sender if it came from an unknown account.",
            ],
            should_alert_guardian=audience_key == "child",
            response_type="safety_analysis",
        )

    try:
        prediction = predict_message(prompt, family_id=family_id)
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

    return _response(
        label=label,
        label_title_value=title,
        tone=tone,
        confidence=confidence,
        risk_level=risk_level,
        indicators=indicators,
        explanation=explanation,
        guidance=guidance,
        assistant_message=f"{explanation} {solution}",
        next_steps=next_steps,
        should_alert_guardian=audience_key == "child" and risk_level == "high",
        response_type="safety_analysis",
    )


def build_safety_assistant_response(prompt: str, *, audience: str, family_id: int | None = None) -> dict:
    cleaned_prompt = " ".join(str(prompt or "").split())
    if not cleaned_prompt:
        return {
            "ok": False,
            "error": "Enter a message or question first.",
        }

    audience_key = "child" if audience == "child" else "parent"
    intent = _detect_intent(cleaned_prompt)
    if intent == "greeting":
        intro = _intro_message(audience_key)
        return _response(
            label=SAFE_LABEL,
            label_title_value="Conversation",
            tone="safe",
            confidence=1.0,
            risk_level="none",
            indicators="conversation",
            explanation=intro,
            guidance="Describe the problem in your own words or paste the message you want me to check.",
            assistant_message=intro,
            next_steps=[
                "Ask me to explain an online safety word.",
                "Paste a message, link, screenshot text, or slang you want explained.",
                "Tell me who sent it and whether they asked for secrecy, money, photos, links, or codes.",
            ],
            response_type="greeting",
        )

    if intent == "thanks":
        thanks = _thanks_message(audience_key)
        return _response(
            label=SAFE_LABEL,
            label_title_value="Conversation",
            tone="safe",
            confidence=1.0,
            risk_level="none",
            indicators="conversation",
            explanation=thanks,
            guidance="You can continue the conversation by describing the next concern.",
            assistant_message=thanks,
            next_steps=[
                "Ask another question if you are unsure.",
                "Share the exact words or link if you want a better risk check.",
            ],
            response_type="conversation",
        )

    if intent == "resource_summary":
        return _resource_summary_response(cleaned_prompt, audience_key, family_id)

    resource_matches = search_resource_chunks(
        cleaned_prompt,
        audience=audience_key,
        family_id=family_id,
    )
    if intent == "education":
        return _with_resource_context(
            _education_response(cleaned_prompt, audience_key),
            resource_matches,
        )

    if intent == "advice":
        return _with_resource_context(
            _advice_response(cleaned_prompt, audience_key),
            resource_matches,
        )

    return _with_resource_context(
        _classification_response(cleaned_prompt, audience_key, family_id),
        resource_matches,
    )
