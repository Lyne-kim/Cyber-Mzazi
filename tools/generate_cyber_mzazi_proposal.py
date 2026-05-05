from __future__ import annotations

from pathlib import Path
from zipfile import ZipFile
from xml.sax.saxutils import escape


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_PATH = Path(r"C:\Users\Admin\OneDrive\Documents\New folder (6)\Project Proposal.docx")
OUTPUT_PATH = Path(r"C:\Users\Admin\OneDrive\Documents\New folder (6)\Cyber Mzazi Project Proposal.docx")
FALLBACK_OUTPUT_PATH = Path(r"C:\Users\Admin\OneDrive\Documents\New folder (6)\Cyber Mzazi Project Proposal With Diagrams.docx")


def paragraph(
    text: str = "",
    *,
    bold: bool = False,
    center: bool = False,
    page_break_before: bool = False,
) -> str:
    parts: list[str] = ["<w:p>"]
    if center:
        parts.append("<w:pPr><w:jc w:val=\"center\"/></w:pPr>")
    if page_break_before:
        parts.append("<w:r><w:br w:type=\"page\"/></w:r>")
    if text:
        run_props = "<w:rPr><w:b/></w:rPr>" if bold else ""
        parts.append(
            f"<w:r>{run_props}<w:t xml:space=\"preserve\">{escape(text)}</w:t></w:r>"
        )
    parts.append("</w:p>")
    return "".join(parts)


def build_document_xml(paragraphs: list[str]) -> str:
    body = "".join(paragraphs)
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document
    xmlns:wpc="http://schemas.microsoft.com/office/word/2010/wordprocessingCanvas"
    xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006"
    xmlns:o="urn:schemas-microsoft-com:office:office"
    xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math"
    xmlns:v="urn:schemas-microsoft-com:vml"
    xmlns:wp14="http://schemas.microsoft.com/office/word/2010/wordprocessingDrawing"
    xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
    xmlns:w10="urn:schemas-microsoft-com:office:word"
    xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    xmlns:w14="http://schemas.microsoft.com/office/word/2010/wordml"
    xmlns:w15="http://schemas.microsoft.com/office/word/2012/wordml"
    xmlns:wpg="http://schemas.microsoft.com/office/word/2010/wordprocessingGroup"
    xmlns:wpi="http://schemas.microsoft.com/office/word/2010/wordprocessingInk"
    xmlns:wne="http://schemas.microsoft.com/office/word/2006/wordml"
    xmlns:wps="http://schemas.microsoft.com/office/word/2010/wordprocessingShape"
    mc:Ignorable="w14 w15 wp14">
  <w:body>
    {body}
    <w:sectPr>
      <w:pgSz w:w="12240" w:h="15840"/>
      <w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440" w:header="708" w:footer="708" w:gutter="0"/>
      <w:cols w:space="708"/>
      <w:docGrid w:linePitch="360"/>
    </w:sectPr>
  </w:body>
</w:document>
"""


def diagram_block(title: str, lines: list[str]) -> list[str]:
    block = [paragraph(title, bold=True)]
    block.extend(paragraph(line) for line in lines)
    block.append(paragraph())
    return block


def build_paragraphs() -> list[str]:
    p: list[str] = []

    p.extend(
        [
            paragraph("JARAMOGI OGINGA ODINGA UNIVERSITY OF SCIENCE AND TECHNOLOGY", bold=True, center=True),
            paragraph("SCHOOL OF INFORMATICS AND INNOVATIVE SYSTEMS", bold=True, center=True),
            paragraph("DEPARTMENT OF COMPUTER SCIENCE AND SOFTWARE ENGINEERING", bold=True, center=True),
            paragraph(),
            paragraph("PROJECT TITLE: CYBER MZAZI - AI-POWERED FAMILY DIGITAL SAFETY PLATFORM", bold=True, center=True),
            paragraph("RESEARCH PROPOSAL", bold=True, center=True),
            paragraph("Date of Submission: 20th April 2026", center=True),
            paragraph(),
            paragraph(
                "A Capstone Project Submitted to the School of Informatics and Innovative Systems at Jaramogi Oginga Odinga University of Science and Technology in Partial Fulfilment of the Requirements for the Award of a Degree in Information Technology / Computer Science.",
                center=True,
            ),
            paragraph(),
            paragraph("By:", bold=True, center=True),
            paragraph("Lynete Kimanthi", center=True),
            paragraph("Registration Number: ____________________", center=True),
            paragraph(),
            paragraph("Supervisor: ____________________", center=True),
        ]
    )

    p.extend(
        [
            paragraph(page_break_before=True),
            paragraph("DECLARATION", bold=True),
            paragraph(
                "This project proposal is my original work and has not been presented in this or any other institution for academic award."
            ),
            paragraph("Student Name: Lynete Kimanthi"),
            paragraph("Registration Number: ____________________"),
            paragraph("Signature: ____________________            Date: ____________________"),
            paragraph(),
            paragraph("Supervisor Approval", bold=True),
            paragraph("Supervisor Name: ____________________"),
            paragraph("Signature: ____________________            Date: ____________________"),
            paragraph(),
            paragraph("DEDICATION", bold=True),
            paragraph(
                "This project is dedicated to parents, guardians, children, educators, and digital safety advocates who continue to seek safer and more transparent online experiences for families."
            ),
            paragraph(),
            paragraph("ACKNOWLEDGEMENT", bold=True),
            paragraph(
                "I thank the Almighty God for life, strength, and wisdom throughout the development of this project. I also sincerely appreciate my lecturers, supervisor, classmates, family, and friends for their guidance, encouragement, and support. Their contribution has been instrumental in shaping the Cyber Mzazi concept into a practical and socially relevant digital safety solution."
            ),
            paragraph(),
            paragraph("ABSTRACT", bold=True),
            paragraph(
                "Families increasingly face risky online interactions across messaging apps, social platforms, and linked mobile devices, yet many existing safety tools are either too invasive, too expensive, or not designed around transparent family workflows. Cyber Mzazi is proposed as an AI-powered family digital safety platform that supports parent or guardian visibility, child-safe reporting, and approved Android companion integration in a consent-led manner. The platform combines a Flask-based web application, MySQL database, message classification pipeline, role-based parent and child interfaces, and an Android companion workflow for notification-based message ingestion where families explicitly enable it."
            ),
            paragraph(
                "The system is designed to classify incoming third-party digital messages into safety-related categories such as grooming, phishing, cyberbullying, violence, misinformation, sextortion, and financial fraud, while still allowing parents to review and correct model output. Cyber Mzazi also supports alert workflows, logout approval requests, safety-resource sharing, multilingual interaction, and one-APK Android direction with role selection for parent or guardian and child users. The expected outcome is a practical, privacy-respecting family safety platform that improves awareness, supports timely intervention, and creates a structured record of risky online incidents for participating families."
            ),
        ]
    )

    p.extend(
        [
            paragraph(page_break_before=True),
            paragraph("TABLE OF CONTENTS", bold=True),
            paragraph("Declaration"),
            paragraph("Dedication"),
            paragraph("Acknowledgement"),
            paragraph("Abstract"),
            paragraph("Acronyms and Abbreviations"),
            paragraph("Chapter 1: Introduction"),
            paragraph("Chapter 2: Literature Review"),
            paragraph("Chapter 3: Methodology"),
            paragraph("Chapter 4: System and Model Design"),
            paragraph("Project Diagrams"),
            paragraph("Project Timeline"),
            paragraph("Project Budget"),
            paragraph("References"),
            paragraph(),
            paragraph("ACRONYMS AND ABBREVIATIONS", bold=True),
            paragraph("AI - Artificial Intelligence"),
            paragraph("ML - Machine Learning"),
            paragraph("NLP - Natural Language Processing"),
            paragraph("API - Application Programming Interface"),
            paragraph("SMS - Short Message Service"),
            paragraph("APK - Android Package Kit"),
            paragraph("DBMS - Database Management System"),
            paragraph("UML - Unified Modeling Language"),
        ]
    )

    p.extend(
        [
            paragraph(page_break_before=True),
            paragraph("CHAPTER 1: INTRODUCTION", bold=True),
            paragraph("1.1 Background Information", bold=True),
            paragraph(
                "The digital environment has become a central part of family life. Children and teenagers now interact daily through messaging applications, social platforms, SMS, online communities, and mobile apps. While these tools support communication and learning, they also expose users to cyberbullying, phishing, grooming, misinformation, financial fraud, and manipulative digital behaviour. Parents and guardians often struggle to obtain timely, actionable visibility into such risks without violating trust or resorting to invasive surveillance tools."
            ),
            paragraph(
                "At the same time, many digital safety solutions available in the market are designed for enterprise monitoring, are too technically complex for ordinary families, or focus heavily on covert tracking rather than transparent family-centered protection. There is therefore a growing need for a localized, practical, and consent-led family safety platform that allows children to report harmful experiences, enables parents or guardians to review flagged incidents, and supports controlled mobile-device integration where needed."
            ),
            paragraph(
                "Cyber Mzazi is proposed to address this gap. The platform combines web-based parent and child experiences, AI-assisted message classification, auditable family safety workflows, and Android-ready notification ingestion through an approved companion model. The project is designed around transparency, human review, and structured intervention rather than secret monitoring."
            ),
            paragraph("1.2 Problem Statement", bold=True),
            paragraph(
                "Families face increasing exposure to harmful digital interactions, yet many lack an accessible system for identifying, reviewing, and responding to risky online messages in a structured and transparent way. Children may receive suspicious links, abusive messages, manipulation attempts, or exploitative content across multiple platforms, but parents or guardians are often notified too late or not at all. Existing tools either provide limited protection, require technical expertise, or rely on invasive surveillance practices that can damage trust."
            ),
            paragraph(
                "As a result, families remain vulnerable to digital harms such as grooming, phishing, cyberbullying, sextortion, financial scams, and online abuse. Without a dedicated family-centered platform that combines AI-supported detection, human review, alerting, reporting, and mobile-device support, many incidents go unnoticed, unrecorded, or unresolved."
            ),
            paragraph("1.2.1 Justification of the Problem", bold=True),
            paragraph(
                "The problem is urgent because digital harm increasingly affects both emotional wellbeing and financial safety. A child exposed to harmful or manipulative content may suffer psychological distress, social withdrawal, fear, or direct exploitation. Families may also lose money through scams, betting traps, fake opportunities, malicious links, or fraudulent requests. A practical system that supports awareness and response is therefore important for digital wellbeing, online trust, and household safety."
            ),
            paragraph("1.3 Objectives", bold=True),
            paragraph("1.3.1 General Objective", bold=True),
            paragraph(
                "To design and develop Cyber Mzazi, an AI-powered family digital safety platform that helps parents or guardians and children identify, review, and respond to risky online interactions through consent-led web and Android workflows."
            ),
            paragraph("1.3.2 Specific Objectives", bold=True),
            paragraph("1. To design separate but linked parent or guardian and child interfaces for structured family safety workflows."),
            paragraph("2. To develop a backend system for capturing, storing, reviewing, and auditing risky digital message reports."),
            paragraph("3. To implement an AI-assisted message classification pipeline for detecting common categories of online harm such as grooming, phishing, cyberbullying, misinformation, violence, sextortion, and financial fraud."),
            paragraph("4. To integrate reviewed parent labels into future prediction workflows for better feedback-driven classification."),
            paragraph("5. To support approved Android companion workflows for notification-based ingestion of incoming third-party content."),
            paragraph("6. To implement parent alerting, logout approval workflows, activity history, and safety-resource sharing."),
            paragraph("7. To build one Android application with role selection for parent or guardian and child use cases."),
            paragraph("1.4 Research Questions", bold=True),
            paragraph("1. How can a family-centered digital safety platform support transparent monitoring without relying on covert surveillance?"),
            paragraph("2. How effectively can AI-assisted classification help detect harmful incoming digital messages in a family-safety context?"),
            paragraph("3. How can parent review improve future classification outcomes in a human-in-the-loop workflow?"),
            paragraph("4. What system design best supports both parent or guardian visibility and child-safe reporting in a single platform?"),
            paragraph("1.5 Significance of the Study", bold=True),
            paragraph("Parents and guardians will benefit from improved visibility into risky online interactions and faster alerts when intervention may be needed."),
            paragraph("Children will benefit from a safer, more guided reporting environment that supports family intervention without exposing them to complex tools."),
            paragraph("Researchers and developers will benefit from a practical case study on consent-led family digital safety workflows and AI-supported moderation."),
            paragraph("Institutions and digital-safety practitioners may use the findings to inform future family-oriented online safety systems."),
            paragraph("1.6 Scope of the Project", bold=True),
            paragraph("1.6.1 Functional Scope", bold=True),
            paragraph(
                "The project covers family registration, parent or guardian and child authentication, AI-assisted message safety checks, parent review workflows, alerting, activity logs, safety resources, child logout approval or denial, Android notification ingestion, and a role-based one-APK Android direction."
            ),
            paragraph("1.6.2 Technical Scope", bold=True),
            paragraph(
                "Cyber Mzazi is implemented using Flask for the backend, server-rendered HTML for the web interface, MySQL for structured data storage, Python-based AI training and inference workflows, and Android support through Kotlin and notification-listener integration."
            ),
            paragraph("1.6.3 Geographical and User Scope", bold=True),
            paragraph(
                "The system is designed for family use and can be deployed for households, schools, or family-safety initiatives where parent or guardian and child workflows are relevant. It is not limited to one county or one school environment."
            ),
            paragraph("1.7 Assumptions", bold=True),
            paragraph("1. Parents or guardians and children will use the platform with informed participation and role-based access."),
            paragraph("2. Families who enable Android notification ingestion will do so willingly on linked devices."),
            paragraph("3. Internet access will be available at least intermittently for web-based interaction and synchronization."),
            paragraph("4. The initial AI model will support safety classification, while reviewed labels will progressively improve practical system usefulness."),
            paragraph("1.8 Limitations", bold=True),
            paragraph("1. Free-tier deployment resources limit the use of heavy production transformer inference in the live environment."),
            paragraph("2. The Android role-selection experience is still under completion and requires full end-to-end testing on both parent or guardian and child devices."),
            paragraph("3. AI classification may still produce false positives or false negatives and therefore depends on parent review and oversight."),
            paragraph("1.9 Definition of Terms", bold=True),
            paragraph("Cyberbullying - repeated harmful or abusive digital communication directed at a person."),
            paragraph("Grooming - manipulative interaction intended to build exploitative trust with a child or vulnerable person."),
            paragraph("Sextortion - coercion involving sexual content, threats, or demands."),
            paragraph("Consent-led monitoring - a family safety approach based on informed participation rather than covert surveillance."),
        ]
    )

    p.extend(
        [
            paragraph(page_break_before=True),
            paragraph("CHAPTER 2: LITERATURE REVIEW", bold=True),
            paragraph("2.1 Introduction", bold=True),
            paragraph(
                "This chapter reviews major themes relevant to Cyber Mzazi: online child safety, family digital supervision, AI-assisted message classification, human-in-the-loop moderation, and mobile-supported reporting environments."
            ),
            paragraph("2.2 Digital Family Safety and Child Online Protection", bold=True),
            paragraph(
                "Recent scholarship on digital child protection emphasizes that children increasingly encounter online harm through ordinary communication channels such as messaging applications, social media, and links shared by peers or strangers. Researchers have highlighted the need for tools that balance safety, trust, privacy, and parental responsibility."
            ),
            paragraph("2.3 AI and Message Classification", bold=True),
            paragraph(
                "Machine learning and natural language processing are widely used to classify harmful or suspicious text. In the context of family safety, such models can support early detection of phishing attempts, abusive language, manipulation, threats, or exploitative requests. However, AI classification is most effective when supported by curated labels, realistic datasets, and human oversight."
            ),
            paragraph("2.4 Human-in-the-Loop Review", bold=True),
            paragraph(
                "A recurring finding in moderation and AI safety literature is that automated systems alone are rarely sufficient. Human-in-the-loop designs allow users or reviewers to correct mistakes, improve future outputs, and maintain accountability. In Cyber Mzazi, parent or guardian review is therefore not a secondary feature but a central design principle."
            ),
            paragraph("2.5 Consent, Privacy, and Ethics", bold=True),
            paragraph(
                "Family safety systems must be designed ethically. Covert surveillance or forced account access may provide short-term visibility but undermine trust, privacy, and digital autonomy. Consent-led approaches are more sustainable because they combine safety with transparency and documented family workflows."
            ),
            paragraph("2.6 Mobile Device Integration", bold=True),
            paragraph(
                "Mobile devices are a central point of online interaction for both children and adults. Notification-based ingestion offers a practical compromise for safety workflows because it can surface third-party messages without requiring direct access to private accounts, provided it is enabled explicitly by the family."
            ),
            paragraph("2.7 Research Gap", bold=True),
            paragraph(
                "Although there are many parental-control tools, messaging moderation tools, and enterprise security products, there is limited focus on transparent, family-centered platforms that combine parent review, child-safe reporting, activity audit trails, and approved Android notification workflows. Cyber Mzazi addresses this gap by aligning AI-supported detection with a practical family safety process."
            ),
        ]
    )

    p.extend(
        [
            paragraph(page_break_before=True),
            paragraph("CHAPTER 3: METHODOLOGY", bold=True),
            paragraph("3.1 Introduction", bold=True),
            paragraph(
                "The development of Cyber Mzazi follows an applied system-development methodology that combines requirements analysis, iterative design, implementation, testing, and user-centered refinement. The project also uses human-reviewed feedback to support improvement of AI-supported classification."
            ),
            paragraph("3.2 Research and Development Approach", bold=True),
            paragraph(
                "The project adopts a practical design-and-build approach. Problem identification was guided by the need for family-safe digital visibility. Requirements were derived from the parent or guardian use case, child protection needs, consent-led system boundaries, and realistic deployment constraints on the web and Android."
            ),
            paragraph("3.3 Data and Model Methodology", bold=True),
            paragraph(
                "For AI training, the project combines multiple datasets related to online harm categories such as cyberbullying, grooming, phishing, scams, malware, misinformation, and financial fraud. DistilBERT-based training workflows were explored locally for richer classification, while a lightweight heuristic production mode was maintained for free-tier deployment stability. Parent-reviewed labels are also incorporated into future prediction workflows through live review-feedback matching and retraining support."
            ),
            paragraph("3.4 System Development Method", bold=True),
            paragraph(
                "Implementation is modular. The project separates authentication, parent workflows, child workflows, JSON API endpoints, database models, AI utilities, deployment scripts, and Android companion support. This modular structure supports easier maintenance and progressive extension."
            ),
            paragraph("3.5 Testing Strategy", bold=True),
            paragraph("Testing includes backend route checks, schema verification, AI prediction checks, role-based page validation, mobile responsiveness review, and Android build or install validation."),
            paragraph("3.6 Ethical Considerations", bold=True),
            paragraph(
                "The project intentionally excludes covert spyware behaviour, hidden persistence, and forced account access. The goal is not secret surveillance but practical family safety coordination through visible, consent-led workflows."
            ),
        ]
    )

    p.extend(
        [
            paragraph(page_break_before=True),
            paragraph("CHAPTER 4: SYSTEM AND MODEL DESIGN", bold=True),
            paragraph("4.1 Introduction", bold=True),
            paragraph(
                "This chapter outlines the architecture, major modules, AI design, technology stack, project timeline, and estimated budget for Cyber Mzazi."
            ),
            paragraph("4.2 System Modules", bold=True),
            paragraph("1. Parent or Guardian Web Module - alerts, reviews, logs, settings, safety resources, and family management."),
            paragraph("2. Child Web Module - safety check reporting, My Safety, settings, and request sign-out workflow."),
            paragraph("3. API Module - structured endpoints for web and Android interactions."),
            paragraph("4. AI Module - message classification, label taxonomy, review-feedback matching, and retraining support."),
            paragraph("5. Android Module - one Android app with role selection for parent or guardian and child flows."),
            paragraph("4.3 AI Model Design", bold=True),
            paragraph(
                "The project supports expanded classification labels including safe, grooming, sexual content, sextortion, betting, phishing, scam, financial fraud, malware, cyberbullying, violence, hate speech, bot activity, and misinformation. DistilBERT-based training was used locally to improve classification quality, while production-safe heuristics were maintained for live deployment on constrained infrastructure. The system now also incorporates reviewed parent feedback to influence future matching predictions."
            ),
            paragraph("4.4 Technology Stack", bold=True),
            paragraph("Frontend: HTML, CSS, Jinja templates, responsive mobile layouts."),
            paragraph("Backend: Python, Flask, Flask-Login, Flask-SQLAlchemy, Flask-CORS."),
            paragraph("Database: MySQL with SQLAlchemy ORM and managed-database support."),
            paragraph("AI: Python, pandas, scikit-learn, transformers, PyTorch, DistilBERT experiments, and heuristic fallback logic."),
            paragraph("Android: Kotlin, Android SDK tools, notification listener workflow, signed APK release path."),
            paragraph("Deployment: GitHub, Render, Gunicorn, optional Hugging Face Space experimentation."),
            paragraph("4.5 High-Level Architecture", bold=True),
            paragraph("Child Web / Android Companion -> Flask Backend -> MySQL Database"),
            paragraph("Parent Dashboard -> Flask Backend -> Alerts / Reviews / Logs / Documents"),
            paragraph("Flask Backend -> AI Classification Layer -> Prediction + Review Feedback"),
            paragraph("4.6 Project Diagrams", bold=True),
        ]
    )

    p.extend(
        diagram_block(
            "Figure 4.1: Use Case Diagram",
            [
                "[Parent/Guardian] -> Register family account",
                "[Parent/Guardian] -> Log in",
                "[Parent/Guardian] -> View alerts",
                "[Parent/Guardian] -> Review flagged messages",
                "[Parent/Guardian] -> Approve or deny child logout",
                "[Parent/Guardian] -> Manage safety resources",
                "[Child] -> Log in",
                "[Child] -> Run safety check",
                "[Child] -> Submit message report",
                "[Child] -> Request sign-out",
                "[Android App] -> Pair device",
                "[Android App] -> Send notification content",
                "[Android App] -> Role selection",
            ],
        )
    )

    p.extend(
        diagram_block(
            "Figure 4.2: System Architecture Diagram",
            [
                "[Parent/Guardian Web] --> [Flask Backend]",
                "[Child Web] --> [Flask Backend]",
                "[Android App] --> [Flask Backend]",
                "[Flask Backend] --> [MySQL Database]",
                "[Flask Backend] --> [AI Classification Layer]",
                "[Flask Backend] --> [Email Service]",
                "[AI Classification Layer] --> [DistilBERT Local Experimental Path]",
                "[AI Classification Layer] --> [Heuristic Production Path]",
            ],
        )
    )

    p.extend(
        diagram_block(
            "Figure 4.3: Entity Relationship Diagram",
            [
                "FAMILY 1..* USER",
                "FAMILY 1..* MESSAGE_RECORD",
                "FAMILY 1..* ACTIVITY_LOG",
                "FAMILY 1..* LOGOUT_REQUEST",
                "FAMILY 1..* SAFETY_RESOURCE_DOCUMENT",
                "FAMILY 1..* NOTIFICATION_INGESTION_DEVICE",
                "USER 1..* MESSAGE_RECORD",
                "USER 1..* ACTIVITY_LOG",
                "USER 1..* LOGOUT_REQUEST",
            ],
        )
    )

    p.extend(
        diagram_block(
            "Figure 4.4: Sequence Diagram for Child Safety Check",
            [
                "Child -> Child Web/App: Submit suspicious message",
                "Child Web/App -> Backend: POST message",
                "Backend -> AI Layer: Classify message",
                "AI Layer -> Backend: Return label and confidence",
                "Backend -> Database: Save message record",
                "Backend -> Parent/Guardian: Trigger alert",
                "Backend -> Child Web/App: Return result",
                "Child Web/App -> Child: Show safety outcome",
            ],
        )
    )

    p.extend(
        diagram_block(
            "Figure 4.5: Sequence Diagram for Logout Approval Flow",
            [
                "Child -> Backend: Request sign-out",
                "Backend -> Database: Save pending logout request",
                "Backend -> Parent/Guardian: Send alert or notification",
                "Parent/Guardian -> Backend: Approve or deny request",
                "Backend -> Database: Update request status",
                "Backend -> Child: Show approved or denied status",
            ],
        )
    )

    p.extend(
        [
            paragraph("4.7 Project Timeline", bold=True),
            paragraph("Week 1: Problem analysis, proposal preparation, and requirement gathering."),
            paragraph("Week 2: Core backend structure, database schema, and authentication workflows."),
            paragraph("Week 3: Parent and child interfaces, alerts, logs, and review workflows."),
            paragraph("Week 4: AI classification, review-feedback integration, and testing."),
            paragraph("Week 5: Android role-selection direction, device-link flows, and signed APK preparation."),
            paragraph("Week 6: Deployment, user testing, documentation, and final refinement."),
            paragraph("4.8 Estimated Project Budget", bold=True),
            paragraph("Laptop / development device support - KES 80,000"),
            paragraph("Internet and connectivity - KES 10,000"),
            paragraph("Testing devices / Android setup - KES 15,000"),
            paragraph("Contingency and documentation costs - KES 5,000"),
            paragraph("Estimated Total - KES 110,000"),
            paragraph("4.9 Expected Outputs", bold=True),
            paragraph("1. A working Cyber Mzazi web platform with parent or guardian and child workflows."),
            paragraph("2. AI-supported message safety classification with reviewed-label feedback support."),
            paragraph("3. Family alerting, audit logs, and child logout approval or denial workflows."),
            paragraph("4. Android companion infrastructure and one-app role-selection direction."),
            paragraph("5. A documented, deployable family digital safety prototype."),
        ]
    )

    p.extend(
        [
            paragraph(page_break_before=True),
            paragraph("REFERENCES", bold=True),
            paragraph("Selected references should include literature on child online safety, AI-assisted text classification, human-in-the-loop moderation, family digital wellbeing, and ethical monitoring systems."),
            paragraph("Project codebase references: README.md, PROJECT_DOCUMENTATION.md, FRONTEND_API.md, ANDROID_COMPANION.md, and related Cyber Mzazi technical documents."),
        ]
    )

    return p


def create_docx() -> None:
    document_xml = build_document_xml(build_paragraphs()).encode("utf-8")

    with ZipFile(TEMPLATE_PATH, "r") as source:
        files = {name: source.read(name) for name in source.namelist()}

    files["word/document.xml"] = document_xml

    output_path = OUTPUT_PATH
    try:
        with ZipFile(output_path, "w") as target:
            for name, content in files.items():
                target.writestr(name, content)
    except PermissionError:
        output_path = FALLBACK_OUTPUT_PATH
        with ZipFile(output_path, "w") as target:
            for name, content in files.items():
                target.writestr(name, content)
    return output_path


if __name__ == "__main__":
    print(create_docx())
