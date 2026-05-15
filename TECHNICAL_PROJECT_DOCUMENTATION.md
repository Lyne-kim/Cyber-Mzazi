# CYBER MZAZI: AN AI-ASSISTED CHILD ONLINE SAFETY MONITORING SYSTEM

## Declaration

This project documentation describes the design, development, implementation, and model computations of Cyber Mzazi, an AI-assisted family safety platform for child online protection. The work documented here is based on the current project source code, database schema, Android companion application, and machine-learning artifacts in this repository.

## Dedication

This project is dedicated to families, guardians, educators, and child-safety advocates who work to make digital spaces safer, more transparent, and more supportive for children.

## Acknowledgement

The development of Cyber Mzazi combines web engineering, mobile development, machine learning, database design, and child-safety workflow design. Appreciation goes to the open-source tools and frameworks used in the system, including Flask, SQLAlchemy, MySQL, Android/Kotlin, PyTorch, Transformers, and scikit-learn.

## Abstract

Cyber Mzazi is a consent-led child online safety platform that enables parents or guardians to monitor and review potentially harmful digital messages affecting a child. The system provides a Flask web application, a MySQL database, a machine-learning classifier, and an Android companion app. Parents can register families, manage child profiles, review alerts, approve or deny child logout requests, and create Android device pairing links. Children can report messages through the web platform, while the Android companion can ingest supported notification text from a child phone after pairing and permission setup.

The classification model detects fourteen safety categories: safe, grooming, sexual content, sextortion, betting, phishing, scam, financial fraud, malware, cyberbullying, violence, hate speech, bot activity, and misinformation. The current primary model is a multilingual DistilBERT-based sequence classifier with review-feedback matching and heuristic fallback support. This documentation presents the system architecture, methodology, implementation design, database schema, Android flow, API structure, and model computational equations.

## Acronyms/Abbreviations

- AI - Artificial Intelligence
- API - Application Programming Interface
- APK - Android Package Kit
- CRISP-DM - Cross Industry Standard Process for Data Mining
- DSRM - Design Science Research Methodology
- ML - Machine Learning
- NLP - Natural Language Processing
- ORM - Object Relational Mapper
- QR - Quick Response Code
- REST - Representational State Transfer
- SHA-256 - Secure Hash Algorithm 256-bit
- SQL - Structured Query Language
- TF-IDF - Term Frequency-Inverse Document Frequency
- UI - User Interface

## List of Figures

- Figure 1.1: Cyber Mzazi high-level system architecture
- Figure 3.1: Message processing workflow
- Figure 3.2: Android parent-child pairing workflow
- Figure 4.1: Transformer classification pipeline

## Contents

- Declaration
- Dedication
- Acknowledgement
- Abstract
- Acronyms/Abbreviations
- List of Figures
- 1. INTRODUCTION
- 2. LITERATURE REVIEW
- 3. METHODOLOGY
- 4. MODEL DESIGN
- References

# 1. INTRODUCTION

## 1.1 Background Information

Children increasingly interact with digital communication platforms through mobile phones, social media, messaging applications, and web platforms. These interactions can expose them to grooming, cyberbullying, scams, phishing, sextortion, hate speech, misinformation, and other harmful content. Parents and guardians need tools that provide visibility while preserving a structured, transparent, and consent-led safety workflow.

Cyber Mzazi addresses this need by combining a parent web portal, child reporting workflows, Android notification ingestion, and AI-assisted message classification. The system is designed to support family safety monitoring, alert review, and guided intervention.

## 1.2 Problem Statement

Parents and guardians often lack timely visibility into harmful messages that children may receive through digital channels. Manual reporting alone may be delayed or incomplete, while unrestricted monitoring can raise privacy and trust concerns. There is a need for a controlled system that allows child safety monitoring, message classification, review workflows, and parent-child accountability.

### 1.2.1 Justification of the Problem

Online risks can escalate quickly when harmful messages are not identified early. A safety system that classifies messages, records alerts, and allows parent review can help guardians respond faster. Cyber Mzazi adds value by combining AI classification with family-based authentication, Android device pairing, audit logs, and parent approval workflows.

## 1.3 Objectives

### 1.3.1 General Objective

To design and implement an AI-assisted child online safety monitoring system that classifies digital messages and supports parent or guardian review workflows.

### 1.3.2 Specific Objectives

- To develop a Flask web application with separate parent and child experiences.
- To implement secure authentication for parent and child accounts.
- To design a MySQL database for families, users, messages, activity logs, logout approvals, safety documents, and Android devices.
- To build an Android companion app with parent and child role flows.
- To implement Android QR/device pairing for child notification ingestion.
- To integrate a multilingual machine-learning classifier for message safety prediction.
- To provide parent alert review, feedback correction, and logout approval features.
- To document the computational equations used by the classification model.

## 1.4 Research Questions

- How can AI-assisted classification help identify harmful child-facing messages?
- How can parent and child workflows be separated while using the same platform?
- How can Android notification ingestion be paired securely with a child profile?
- How can parent review feedback improve or override future predictions?
- Which computational steps are used to convert message text into a safety label?

## 1.5 Significance of the Study

Cyber Mzazi is significant because it provides a practical family-safety workflow that combines message reporting, Android ingestion, machine learning, review feedback, and parent accountability. It can help guardians identify risks earlier and maintain a record of child-safety events.

## 1.6 Scope of the Project

### 1.6.1 Geographical Scope

The system is suitable for families using internet-connected web browsers and Android devices. It supports multilingual safety classification through a multilingual transformer model and includes English/Swahili-oriented dataset preparation.

### 1.6.2 Subject Scope

The project covers child online safety monitoring, message classification, parent alerts, Android notification ingestion, authentication, review feedback, and family activity logging.

### 1.6.3 Time Scope

The current project version covers the implemented Flask backend, MySQL setup, Android companion flow, model artifacts, and technical documentation available as of the current development stage.

## 1.7 Assumptions

- Parents and guardians use the system transparently and lawfully.
- Android notification access is enabled only on the child device.
- The model supports decision assistance and does not replace human judgment.
- Families have access to a configured backend and database.
- Model predictions may require parent review and correction.

## 1.8 Limitations

- Model performance depends on training data quality and class balance.
- Some Android vendors may restrict notification access or APK installation.
- The system cannot inspect encrypted message content unless it appears in accessible notification text or is manually reported.
- The current model still needs broader real-world validation and automated testing.

## 1.9 Definition of Terms

- Android companion app: The native Android application used by parents or children.
- Child device: The Android phone paired to a child profile for notification ingestion.
- Ingestion token: A secure token generated by the backend and stored as a SHA-256 hash.
- Message classification: The process of assigning a safety label to message text.
- Parent review feedback: A reviewed label supplied by a parent that can override similar future predictions.
- Risk indicators: Human-readable terms explaining why a label may be risky.

# 2. LITERATURE REVIEW

## 2.1 Introduction

Digital child safety systems often combine reporting tools, content moderation, parental controls, and automated classification. Cyber Mzazi follows this direction by integrating family workflows with AI-assisted NLP classification and mobile notification ingestion.

### 2.1.1 Child Online Safety and Digital Risk

Children may encounter grooming, bullying, scams, phishing links, hate speech, misinformation, and coercive content online. Early detection tools can support guardians by surfacing potential risks for review.

## 2.2 Literature Related to the First Objective: Data Collection and Integration

The project uses normalized datasets from multiple safety domains. The training pipeline consolidates CSV, Excel, and JSON sources into a common structure:

- text
- threat_type
- risk_indicators
- language
- source_name

This allows heterogeneous datasets to be merged into one classification task.

## 2.3 Current Solutions

Current safety approaches include manual reporting, parental control apps, content filters, platform moderation, and AI-based moderation systems. Cyber Mzazi differs by combining family-specific workflows, child logout approval, Android pairing, parent review feedback, and local or remote model inference options.

## 2.4 Artificial Intelligence and Machine Learning in Safety Classification

NLP models can classify message text by learning language patterns associated with harmful or safe content. Transformer models such as DistilBERT are effective for sequence classification because they capture contextual relationships between words and phrases.

## 2.5 Android Platforms for Child Safety Monitoring

Android notification listener services can capture notification metadata and text when the user grants permission. Cyber Mzazi uses this mechanism only in child mode and blocks parent-mode capture to avoid mixing parent-device notifications with child monitoring.

## 2.6 Theoretical Framework

The project uses an AI-assisted decision-support framework. The model predicts labels and confidence scores, while parents remain responsible for reviewing alerts and correcting predictions where necessary.

## 2.7 Conceptual Framework

```text
Child message or notification
        |
        v
Text preprocessing and tokenization
        |
        v
ML prediction / feedback override / fallback heuristic
        |
        v
MessageRecord stored in MySQL
        |
        v
Parent alert review and action
```

## 2.8 Summary of Literature and Research Gaps

Many parental control tools focus on blocking or surveillance. Cyber Mzazi focuses on a reviewable safety workflow: classification, explanation through risk indicators, parent feedback, child-device pairing, and activity logs.

# 3. METHODOLOGY

## 3.1 Introduction

The project methodology combines DSRM for system development and CRISP-DM for the machine-learning pipeline.

## 3.2 Design Science Research Methodology (DSRM)

The DSRM process is applied as follows:

- Problem identification: harmful child-facing messages are difficult for guardians to detect quickly.
- Objective definition: build a parent-child safety monitoring platform.
- Design and development: implement the Flask backend, MySQL schema, Android app, and ML classifier.
- Demonstration: ingest child reports and Android notifications, classify them, and show parent alerts.
- Evaluation: use model metrics, build verification, and device testing.
- Communication: document the architecture, flow, and equations.

## 3.3 CRISP-DM for the Machine Learning Pipeline

### 3.3.1 Data Collection

The training pipeline loads supported safety datasets from CSV, Excel, and JSON files. Source loaders normalize fields into a shared schema.

### 3.3.2 Data Analysis

The pipeline removes empty text, normalizes labels, filters unsupported classes, removes duplicates, and caps rows by source and label to reduce imbalance.

### 3.3.3 Modelling Phase

The model uses a multilingual transformer sequence classifier. The current training configuration includes:

- base model: distilbert-base-multilingual-cased or a previous stage artifact
- max sequence length: 160
- batch size: 8
- optimizer: AdamW
- learning rate: 2e-5
- gradient clipping: 1.0
- validation split: 20 percent

### 3.3.4 Remaining CRISP-DM Phases

Evaluation uses validation accuracy, macro F1, per-class precision, recall, and F1 score. Deployment is supported through local artifacts, remote model API configuration, and a heuristic fallback mode.

## 3.4 System Design

### 3.4.1 Integrated System Architecture

```text
Parent Web / Parent Android
        |
        v
Flask API -------> MySQL Database
        |                ^
        v                |
Prediction Service       |
        |                |
        |-- Review feedback
        |-- Transformer model
        |-- Remote model API
        `-- Heuristic fallback
                         ^
Child Web / Child Android+
```

### 3.4.2 Use Case Design

Main actors:

- Parent/Guardian
- Child
- Android child device
- ML prediction service
- MySQL database

Main use cases:

- Register family
- Login as parent or child
- Submit child message
- Pair child Android phone
- Ingest Android notification
- Predict safety label
- Review parent alerts
- Approve or deny child logout

### 3.4.3 System Flowchart

```text
Start
 |
 v
Authenticate user or verify Android token
 |
 v
Receive message text
 |
 v
Check review feedback
 |
 v
Run local/remote/heuristic prediction
 |
 v
Verify message label
 |
 v
Store message and activity log
 |
 v
Notify or show parent alert
 |
 v
End
```

### 3.4.4 Sequence Diagram of Android Notification Processing

```text
Android App -> API: POST notification payload + token
API -> Database: verify token hash
API -> Prediction Service: predict_message(text)
Prediction Service -> API: label, confidence, risk indicators
API -> Database: save MessageRecord
API -> Parent Alert Service: send alert if needed
API -> Android App: return stored message result
```

## 3.5 Ethical Considerations and Data Privacy

The system should be used transparently and with appropriate consent. Parent monitoring must follow local law, child protection guidance, platform policies, and family trust principles. The backend stores only hashed Android ingestion tokens, not raw tokens.

## 3.6 Pilot Implementation and Evaluation Plan

Evaluation should include:

- backend API testing
- Android parent and child role testing
- two-phone QR pairing validation
- notification ingestion testing
- model prediction review
- parent feedback override testing
- database record verification

# 4. MODEL DESIGN

## 4.1 Introduction

The model design explains how Cyber Mzazi converts message text into safety labels. The main classifier is a transformer sequence classification model with fallback mechanisms.

### 4.1.1 Overview of the Cyber Mzazi Model

The classifier supports fourteen labels:

- safe
- grooming
- sexual_content
- sextortion
- betting
- phishing
- scam
- financial_fraud
- malware
- cyberbullying
- violence
- hate_speech
- bot_activity
- misinformation

### 4.1.2 Purpose: Predicting Message Safety Labels

Given a message, the model predicts:

```text
prediction = {label, confidence, risk_indicators}
```

### 4.1.3 Importance of Machine Learning in Cyber Safety

Machine learning allows the system to identify patterns in message text that may indicate risk. The prediction assists parents by prioritizing messages for review.

## 4.2 Dataset Description

### 4.2.1 Dataset Overview

The stage-3 training metrics show:

- dataset rows: 1,239
- validation support: 248 rows
- validation accuracy: 0.5806
- validation macro F1: 0.6405
- validation loss: 1.1391
- device: CPU
- epochs: 1
- batch size: 8
- max length: 160

### 4.2.2 Feature Variables

The main input feature is message text:

```text
x = message_text
```

Additional metadata can be stored with messages:

- source_platform
- source_app_package
- sender_handle
- browser_origin
- notification_title
- capture_method

### 4.2.3 Target Variable

The target variable is:

```text
y = threat_type
```

where `y` belongs to one of the fourteen supported labels.

### 4.2.4 Data Preprocessing

The training pipeline:

- normalizes quote characters
- collapses whitespace
- lowercases labels
- removes empty text
- removes unsupported labels
- removes duplicate text-label pairs
- caps rows per source-label group
- caps rows per label

### 4.2.5 Dataset Availability

Training artifacts and metrics are stored under:

```text
artifacts/
```

Large transformer model files should be handled carefully in deployment because they may be too large for normal GitHub storage.

## 4.3 Feature Engineering

### 4.3.1 Tokenization

Transformer tokenization maps text into model-readable IDs:

```text
T(x) = {input_ids, attention_mask}
```

The maximum length is:

```text
L = 160
```

### 4.3.2 Attention Masking

The attention mask identifies real tokens and padding tokens:

```text
attention_mask_i = 1 if token_i is real
attention_mask_i = 0 if token_i is padding
```

### 4.3.3 Class Encoding

Each label is mapped to an integer:

```text
class_to_index(label_k) = k
```

For fourteen classes:

```text
k in {0, 1, 2, ..., 13}
```

### 4.3.4 Review Signature Engineering

Parent-reviewed messages are normalized into review signatures:

```text
s = normalize(text)[0:512]
```

The signature is used for exact and approximate review-feedback matching.

### 4.3.5 Legacy Feature Engineering

The legacy model path supports TF-IDF and SVD:

```text
v = TFIDF(text)
d = SVD(v)
```

## 4.4 Mathematical Computations

### 4.4.1 Transformer Mathematical Framework

Let the cleaned message be:

```text
x = clean(message_text)
```

Tokenization produces:

```text
T(x) = {input_ids, attention_mask}
```

The transformer encoder computes hidden states:

```text
H = Transformer(input_ids, attention_mask)
```

The classification head uses the pooled representation:

```text
h = pool(H)
```

For `K = 14` classes, logits are computed as:

```text
z = W h + b
```

where:

```text
z in R^K
W in R^(K x d)
h in R^d
b in R^K
```

### 4.4.2 Softmax Probability Framework

The probability for class `i` is:

```text
p_i = exp(z_i) / sum_j exp(z_j)
```

The probability vector satisfies:

```text
0 <= p_i <= 1
sum_i p_i = 1
```

### 4.4.3 Prediction and Confidence Framework

The predicted class index is:

```text
y_hat = argmax_i p_i
```

The confidence score is:

```text
c = max_i p_i
```

The returned label is:

```text
label = classes[y_hat]
```

### 4.4.4 Cross-Entropy Loss

For one training example with true class `y`:

```text
L_ce = -log(p_y)
```

For a batch of `N` examples:

```text
L_batch = -(1/N) sum_n log(p_(n,y_n))
```

### 4.4.5 AdamW Optimization

The optimizer uses learning rate:

```text
eta = 2 x 10^-5
```

Gradient:

```text
g_t = grad_theta L_t
```

First moment:

```text
m_t = beta1 m_(t-1) + (1 - beta1) g_t
```

Second moment:

```text
v_t = beta2 v_(t-1) + (1 - beta2) g_t^2
```

Parameter update:

```text
theta_t = theta_(t-1) - eta * m_hat_t / (sqrt(v_hat_t) + epsilon) - eta * lambda * theta_(t-1)
```

Gradient clipping:

```text
||g||_2 <= 1.0
```

### 4.4.6 Evaluation Metrics

Accuracy:

```text
accuracy = correct_predictions / total_predictions
```

Precision for class `k`:

```text
precision_k = TP_k / (TP_k + FP_k)
```

Recall for class `k`:

```text
recall_k = TP_k / (TP_k + FN_k)
```

F1 score:

```text
F1_k = 2 * precision_k * recall_k / (precision_k + recall_k)
```

Macro F1:

```text
macro_F1 = (1/K) sum_k F1_k
```

### 4.4.7 Keyword Hint Adjustment

Let:

```text
matches_l = number of keyword hints for label l found in text
```

If two or more hints match:

```text
label = l
confidence = max(confidence, 0.80)
```

If one hint matches and confidence is weak:

```text
label = l
confidence = max(confidence, 0.60)
```

For high-signal labels, one hint can override when:

```text
confidence < 0.55
```

### 4.4.8 Review Feedback Mathematical Framework

Exact parent review match:

```text
if signature(text) == signature(reviewed_text):
    confidence = 0.99
    label = reviewed_label
```

Similar review match:

```text
similarity = SequenceMatcher(signature(text), signature(reviewed_text)).ratio()
```

If:

```text
similarity >= 0.92
```

Then:

```text
label = reviewed_label
confidence = max(similarity, 0.85)
```

### 4.4.9 Heuristic Fallback Framework

For each label:

```text
score_l = sum keyword_match_l
```

The fallback label is:

```text
y_hat = argmax_l(score_l, priority_l)
```

Fallback confidence:

```text
c = min(0.55 + 0.15 * score_y_hat, 0.90)
```

If no score exists:

```text
label = safe
confidence = 0.92
```

### 4.4.10 Legacy Model Mathematical Framework

The legacy model computes:

```text
v = TFIDF(text)
d = SVD(v)
```

Linear model probabilities:

```text
p_linear = softmax(linear_model(d))
```

Random forest probabilities:

```text
p_rf = random_forest.predict_proba(d)
```

Blended probability:

```text
p = 0.45 * p_linear + 0.55 * p_rf
```

Prediction:

```text
y_hat = argmax_i p_i
confidence = max_i p_i
```

## 4.5 System Implementation

### 4.5.1 Backend Implementation

The backend uses Flask, Flask-Login, SQLAlchemy, and MySQL. Main backend modules include:

- `webapp/api.py`
- `webapp/models.py`
- `webapp/services/prediction_service.py`
- `webapp/services/ml_service.py`
- `webapp/services/review_feedback.py`
- `webapp/services/verification.py`

### 4.5.2 Database Implementation

Core tables:

- family
- user
- message_record
- activity_log
- logout_request
- safety_resource_document
- notification_ingestion_device

Android tokens are stored as hashes:

```text
token_hash = SHA256(token)
```

### 4.5.3 Android Implementation

The Android app is implemented in Kotlin and supports:

- Home
- Authentication
- QR Code
- Settings
- Capture
- Filters
- Status
- Logs

The `Save settings` button appears only when settings have unsaved changes.

### 4.5.4 API Implementation

Important endpoints:

- `POST /api/auth/register`
- `POST /api/auth/login`
- `POST /api/auth/logout`
- `GET /api/parent/dashboard`
- `GET /api/parent/alerts`
- `POST /api/parent/android-devices`
- `POST /api/device-ingest/android-notifications`
- `POST /api/child/messages`
- `POST /api/child/logout-request`
- `GET /api/health`

## 4.6 Testing and Evaluation

Testing should cover:

- parent login
- child login
- family registration
- Android QR pairing
- Android notification access
- Android notification ingestion
- message classification
- parent alert review
- logout approval and denial
- review-feedback override
- database persistence

## Conclusion

Cyber Mzazi implements a practical AI-assisted child online safety monitoring system with web, mobile, database, and machine-learning components. The system provides parent and child authentication, Android device pairing, message ingestion, safety classification, parent review, activity logging, and feedback-based prediction correction. The model design combines transformer classification, review feedback, keyword hints, heuristic fallback, and legacy model support.

## References

- Flask documentation
- SQLAlchemy documentation
- MySQL documentation
- Android developer documentation
- PyTorch documentation
- Hugging Face Transformers documentation
- scikit-learn documentation
- Cyber Mzazi project source code and artifacts
