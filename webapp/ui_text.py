from __future__ import annotations

from flask import session


SUPPORTED_LANGUAGES = {
    "en": "English",
    "sw": "Kiswahili",
}


TRANSLATIONS = {
    "sw": {
        "Alerts": "Tahadhari",
        "Dashboard": "Dashibodi",
        "Child Profile": "Wasifu wa Mtoto",
        "Activity Log": "Kumbukumbu",
        "Alert Settings": "Mipangilio ya Tahadhari",
        "Family Hub": "Kitovu cha Familia",
        "Safety Resources": "Rasilimali za Usalama",
        "Help & Support": "Msaada",
        "Privacy Center": "Faragha",
        "System Status": "Hali ya Mfumo",
        "Insights": "Mwenendo",
        "Language": "Lugha",
        "Language Settings": "Mipangilio ya Lugha",
        "Notification Log": "Kumbukumbu ya Arifa",
        "Trusted Contacts": "Watu wa Kuaminika",
        "Home": "Nyumbani",
        "My Safety": "Usalama Wangu",
        "Talk": "Ongea",
        "Help": "Msaada",
        "Settings": "Mipangilio",
        "Safety Check": "Ukaguzi wa Usalama",
        "Parent Dashboard": "Dashibodi ya Mzazi",
        "Child Safety App": "Programu ya Usalama ya Mtoto",
        "Primary": "Msingi",
        "Support": "Msaada",
        "Show More": "Ona Zaidi",
        "Selected child": "Mtoto aliyechaguliwa",
        "Child selector": "Chagua mtoto",
        "Online": "Mtandaoni",
        "Open alerts": "Tahadhari wazi",
        "High-risk items": "Hatari kubwa",
        "Reviewed checks": "Ukaguzi uliopitiwa",
        "Pending child request": "Ombi la mtoto linasubiri",
        "Approve child logout": "Idhinisha kutoka",
        "Approve logout": "Idhinisha kutoka",
        "No logout request pending.": "Hakuna ombi la kutoka linalosubiri.",
        "Requested on": "Liliombwa",
        "Current child": "Mtoto wa sasa",
        "Overview": "Muhtasari",
        "Quick Stats": "Takwimu",
        "Recent Safety Checks": "Ukaguzi wa Karibuni",
        "Recent summaries": "Muhtasari wa karibuni",
        "Upload documents": "Pakia nyaraka",
        "Choose files": "Chagua faili",
        "Add placeholders": "Ongeza nafasi",
        "English": "Kiingereza",
        "Swahili": "Kiswahili",
        "Save language": "Hifadhi lugha",
        "Request sign-out": "Omba kutoka",
        "Waiting for parent approval": "Inasubiri idhini ya mzazi",
        "Parent approval received": "Idhini ya mzazi imepatikana",
        "This request ends only the current child session on this device.": "Ombi hili linafunga tu kipindi cha sasa cha mtoto kwenye kifaa hiki.",
        "Ask to end this child session on this device.": "Omba kufunga kipindi hiki cha mtoto kwenye kifaa hiki.",
        "Send request": "Tuma ombi",
        "Optional note": "Ujumbe wa hiari",
        "Who sent it?": "Nani alituma?",
        "Which app was it on?": "Ilikuwa kwenye programu gani?",
        "Link or app page": "Kiungo au ukurasa wa programu",
        "Paste the message they sent": "Bandika ujumbe waliotuma",
        "Run safety check": "Endesha ukaguzi",
        "Parent lock": "Kufuli ya mzazi",
        "Friendly reminders": "Vikumbusho",
        "Protected sign-out": "Kutoka kulikolindwa",
        "Incoming third-party messages and links": "Ujumbe na viungo kutoka kwa watu wengine",
        "Shared family session": "Kikao cha familia",
    }
}


def get_language() -> str:
    language = session.get("ui_language", "en")
    return language if language in SUPPORTED_LANGUAGES else "en"


def t(text: str) -> str:
    return TRANSLATIONS.get(get_language(), {}).get(text, text)
