# Saudi Market: Technical Requirements & Architecture Specification

**Version:** 1.0  
**Date:** 2026-04-18  
**Classification:** Confidential — Partner Handoff Document  
**Prepared by:** Genesis AI — CTO Office  

---

## 1. Executive Summary

This document provides the complete technical requirements and system architecture for the Genesis AI platform deployment targeting the Saudi Arabian market. It is intended as a self-contained specification for an external implementation partner.

The Saudi deployment must comply with the **Personal Data Protection Law (PDPL)**, **National Cybersecurity Authority (NCA) Essential Cybersecurity Controls (ECC)**, and Saudi Vision 2030 digital transformation mandates. All data must reside in-kingdom or meet PDPL cross-border transfer rules.

---

## 2. Architecture Overview

### 2.1 High-Level System Design

```
┌─────────────────────────────────────────────────────────────┐
│                    Saudi Deployment Region                  │
│                    (AWS me-south-1 / Bahrain)               │
│                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │  CDN / WAF   │    │  API Gateway │    │  Auth Layer  │  │
│  │(CloudFront + │───▶│  (Kong/APIGW)│───▶│(Cognito/Auth0│  │
│  │  AWS Shield) │    │              │    │ + Absher)    │  │
│  └──────────────┘    └──────┬───────┘    └──────────────┘  │
│                             │                               │
│               ┌─────────────┴──────────────┐               │
│               │                            │               │
│  ┌────────────▼──────┐    ┌────────────────▼──────────┐    │
│  │  Core AI Services │    │   Data Platform            │    │
│  │  - ML Inference   │    │   - PostgreSQL (RDS)       │    │
│  │  - Model Serving  │    │   - S3 (in-region)         │    │
│  │  - Orchestration  │    │   - ElasticSearch          │    │
│  └───────────────────┘    └────────────────────────────┘    │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │           Integration Layer                          │   │
│  │   mada | STC Pay | SADAD | Absher/Nafath | VAT APIs │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Deployment Topology

| Component | Primary | Failover |
|-----------|---------|----------|
| Compute | AWS me-south-1 (Bahrain) | Azure UAE North |
| Database | AWS RDS Multi-AZ (me-south-1) | Read replica in same region |
| Object Storage | AWS S3 me-south-1 | AWS S3 Versioning + Replication |
| CDN | AWS CloudFront (Saudi PoP) | Fastly Riyadh edge |
| DNS | AWS Route 53 (latency routing) | — |

> **Constraint:** All PII and business-critical data MUST remain within AWS me-south-1 or an equivalent in-kingdom/PDPL-compliant region. No cross-region replication of personal data without explicit PDPL cross-border transfer approval.

### 2.3 Data Flow Diagram

```
User (KSA) ──HTTPS──▶ CloudFront WAF ──▶ ALB ──▶ API Gateway
                                                      │
                              ┌───────────────────────┤
                              │                       │
                         AI Services            Auth & Identity
                              │                       │
                         ┌────▼────┐          ┌───────▼──────┐
                         │  Data   │          │ Absher/Nafath│
                         │ Platform│          │  (NafathID)  │
                         └────┬────┘          └──────────────┘
                              │
                    ┌─────────▼──────────┐
                    │  Encrypted at rest  │
                    │  (AES-256, KMS CMK)│
                    │  in me-south-1      │
                    └────────────────────┘
```

---

## 3. Data Residency & Compliance

### 3.1 Saudi PDPL Requirements

The Personal Data Protection Law (Royal Decree M/19, effective Sep 2023) applies to any processing of Saudi residents' personal data.

| Requirement | Implementation |
|-------------|----------------|
| Data Residency | All PII stored exclusively in AWS me-south-1 |
| Cross-Border Transfer | Prohibited unless: (a) consent obtained, (b) contractual necessity, or (c) SDAIA approval for specific use cases |
| Data Minimization | Collect only fields required for the stated purpose |
| Retention Policy | Define per-category; default max 5 years post-relationship end |
| Subject Rights | API endpoints for access, correction, deletion requests (30-day SLA) |
| Breach Notification | Notify SDAIA within 72 hours of discovery; notify affected individuals without undue delay |
| Privacy Policy | Arabic-language privacy policy required; plain-language, legally reviewed |
| Data Processor Agreements | DPA required with all sub-processors (AWS, analytics vendors, etc.) |

### 3.2 Data Classification

| Class | Examples | Controls |
|-------|----------|----------|
| PII-Sensitive | National ID, biometrics, health data | Encrypt in transit + at rest; strict access logs; no cross-border |
| PII-General | Name, email, phone, IP address | Encrypt at rest; audit logs |
| Business Data | Transaction records, usage analytics | Encrypt at rest; regional storage |
| Public | Marketing content, documentation | Standard CDN delivery |

### 3.3 NCA Cybersecurity Requirements

Compliance with **NCA Essential Cybersecurity Controls (ECC-1:2018)** and **Cloud Cybersecurity Controls (CCC-1:2020)** is mandatory for entities operating in the Kingdom.

**Key ECC domains applicable to this deployment:**

- **ECC-1: Cybersecurity Governance** — appoint a data protection officer equivalent; maintain cybersecurity policy documentation in Arabic and English
- **ECC-2: Cybersecurity Defense** — implement IDS/IPS (AWS GuardDuty + WAF), endpoint protection, SIEM
- **ECC-3: Cybersecurity Resilience** — BCP/DR plan tested annually; RTO ≤ 4 hours, RPO ≤ 1 hour
- **ECC-4: Third-Party Cybersecurity** — vendor risk assessments; partner must comply with NCA controls
- **ECC-5: Cybersecurity in ICT** — secure SDLC, static/dynamic code analysis, dependency scanning

---

## 4. Infrastructure Requirements

### 4.1 Cloud Hosting

**Primary:** AWS `me-south-1` (Bahrain) — closest AWS region with full service coverage  
**Alternative:** Azure UAE North or Qatar (if client has existing Azure footprint)  
**Local option:** STC Cloud (Riyadh) — for maximum in-kingdom compliance, but limited managed services

**Recommended:** AWS me-south-1 with STC Cloud as a backup/compliance fallback for the most sensitive data tier.

### 4.2 Compute Sizing (Initial Production)

| Service | Instance Type | Count | Notes |
|---------|--------------|-------|-------|
| API Gateway / Load Balancer | AWS ALB | 1 (HA) | Auto-scales |
| Application Servers | t3.large (ECS Fargate) | 2–10 | Auto-scaling group |
| AI/ML Inference | g4dn.xlarge (or Inf1) | 2 | GPU for inference; reserved instances |
| Database (Primary) | db.r6g.large RDS PostgreSQL | 1 Multi-AZ | Encrypted, in me-south-1 |
| Cache | cache.r6g.large (ElastiCache Redis) | 1 | Session + API cache |
| Search | m6g.large.search (OpenSearch) | 3-node | Arabic analyzer required |

### 4.3 Latency & Performance Targets

| Metric | Target | Measurement Point |
|--------|--------|-------------------|
| API P95 Latency | < 200ms | Riyadh end-user |
| Page Load (LCP) | < 2.5s | 4G mobile, Riyadh |
| AI Inference P95 | < 3s | API response |
| Availability SLA | 99.9% | Monthly uptime |
| CDN Cache Hit Rate | > 85% | Static assets |

### 4.4 CDN Configuration

- **Provider:** AWS CloudFront with Saudi Arabia edge PoPs (Riyadh)
- **WAF Rules:** AWS Managed Rules + OWASP Core Rule Set; custom rules for Arabic content injection
- **DDoS Protection:** AWS Shield Standard (upgrade to Advanced for production)
- **SSL/TLS:** TLS 1.2 minimum; TLS 1.3 preferred; HSTS enabled; Saudi CA certificates if required by government clients

### 4.5 Network Architecture

```
VPC (me-south-1)
├── Public Subnet (AZ-a, AZ-b)
│   └── ALB, NAT Gateway
├── Private Subnet — App Tier (AZ-a, AZ-b)
│   └── ECS Fargate tasks, Lambda functions
└── Private Subnet — Data Tier (AZ-a, AZ-b)
    └── RDS, ElastiCache, OpenSearch
```

- All inter-service communication over private subnets
- No public IPs on compute or data tier
- VPC Flow Logs enabled; forwarded to SIEM
- AWS PrivateLink for S3 and KMS access

---

## 5. Localization Technical Specification

### 5.1 RTL UI Support

| Requirement | Implementation Detail |
|-------------|----------------------|
| CSS Direction | `direction: rtl; unicode-bidi: embed` on `<html>` when locale = `ar-SA` |
| Layout Mirroring | Use CSS Logical Properties (`margin-inline-start`, `padding-inline-end`) — NOT hardcoded `left`/`right` |
| Icon Mirroring | Directional icons (arrows, progress bars) mirrored via `transform: scaleX(-1)` or separate RTL asset set |
| Framework | If React: use `@mui/material` RTL support or `styled-components` `StyleSheetManager` with RTL plugin |
| Testing | Automated RTL layout tests using Chromatic or Percy with `ar-SA` locale fixture |

### 5.2 Arabic Text Handling

- **Font Stack:** `'Noto Naskh Arabic'`, `'Cairo'`, `'IBM Plex Arabic'` — subset for performance
- **Text Shaping:** Rely on browser HarfBuzz / OS-level shaping; do NOT use manual glyph substitution
- **BiDi Algorithm:** Unicode BiDi auto-applied by browsers; wrap mixed-direction strings with `<bdi>` elements
- **Normalization:** Store Arabic text as NFC-normalized Unicode; apply `String.normalize('NFC')` on input
- **Search:** OpenSearch Arabic analyzer (`arabic` built-in stemmer + stop words); support diacritics-insensitive search
- **Input Method:** Test with Windows Arabic keyboard layout and iOS Arabic keyboard
- **Numbers:** Support both Arabic-Indic numerals (٠١٢٣) and Western numerals based on context; use `Intl.NumberFormat('ar-SA')` for formatting

### 5.3 Locale & Timezone

| Setting | Value |
|---------|-------|
| Primary Locale | `ar-SA` |
| Secondary Locale | `en-US` |
| Timezone | `Asia/Riyadh` (UTC+3, no DST) |
| Date Format | `DD/MM/YYYY` (Arabic) or ISO 8601 for APIs |
| Currency | SAR (Saudi Riyal, ر.س) — `Intl.NumberFormat('ar-SA', {style: 'currency', currency: 'SAR'})` |
| Calendar | Gregorian primary; Hijri calendar display optional (use `Intl.DateTimeFormat` with `u-ca-islamic-umalqura`) |

### 5.4 Bilingual Content Management

- All user-facing strings stored in i18n resource files: `en.json`, `ar.json`
- CMS (if applicable) must support dual-language fields with independent rich-text editors per locale
- Fallback chain: `ar-SA` → `ar` → `en-US`
- Translation workflow: human review required for all Arabic-facing customer communications (machine translation not sufficient for legal/compliance text)
- **SEO:** Separate `hreflang` tags; Arabic URLs use transliterated slugs or Arabic script based on SEO strategy

---

## 6. Integration Points

### 6.1 Payment Gateways

#### mada (Saudi Domestic Debit Network)

| Item | Detail |
|------|--------|
| Provider | Direct integration via Hyper Pay, Checkout.com, or PayTabs (certified mada acquirers) |
| Protocol | REST API; PCI-DSS Level 1 compliant gateway |
| Authentication | OAuth 2.0 + HMAC-SHA256 request signing |
| 3DS | 3D Secure 2.0 mandatory for card-not-present |
| Currency | SAR only |
| Sandbox | Provided by acquirer — test with mada test card numbers |
| Webhook | Payment result callbacks signed with shared secret; verify signature before updating order state |

#### STC Pay

| Item | Detail |
|------|--------|
| Integration | STC Pay Merchant API (REST) |
| Auth | Client credentials (client_id + client_secret) via STC Pay developer portal |
| Payment Initiation | `POST /api/v1/payments` — returns payment URL for redirect flow |
| Callback | Signed webhook; validate `X-STC-Signature` header |
| Refunds | `POST /api/v1/refunds` |
| Sandbox | STC Pay sandbox environment available upon merchant registration |

#### SADAD (Bill Payment)

| Item | Detail |
|------|--------|
| Use Case | Subscription invoicing; government entity payments |
| Integration | SADAD Online (REST API) via Saudi Payments platform |
| Bill Registration | `POST /sadad/api/v1/bills` — register payable bill for customer |
| Reconciliation | Daily settlement file (CSV) via SFTP |
| Biller Registration | Must register as a biller with Saudi Payments; ~2–4 week process |

### 6.2 National Identity — Absher / NafathID

| Item | Detail |
|------|--------|
| Purpose | KYC verification; high-assurance authentication for regulated use cases |
| Nafath (preferred) | Saudi national digital identity app — OIDC-compatible; use Nafath SDK or OIDC redirect flow |
| Scope | `openid profile iqama_number national_id` |
| Response | JWT with verified national ID number, name (AR + EN), date of birth |
| Eligibility | Saudi nationals and Iqama holders only; non-Saudi users use passport + manual KYC |
| Onboarding | Registration via NCSC / National Information Center (NIC); allow 4–6 weeks |
| Fallback | Manual document upload + human review queue for identity verification failures |

### 6.3 VAT / ZATCA Integration

| Item | Detail |
|------|--------|
| Requirement | 15% VAT applies; e-invoicing (Fatoorah) mandatory per ZATCA Phase 2 |
| Integration | ZATCA Fatoorah API — generate and report e-invoices in real time |
| Invoice Format | XML (UBL 2.1) with QR code; QR encoded per ZATCA specification |
| Reporting | Real-time clearance for B2B invoices > SAR 1,000; simplified for B2C |
| Sandbox | ZATCA Fatoorah simulation environment available |

### 6.4 SMS / OTP (Local Carrier)

- **Provider:** Use a Saudi-licensed aggregator: Taqniyat, Unifonic, or Msegat
- **Alpha Sender IDs:** Register sender ID with CITC (Communications and Information Technology Commission); allow 2–3 weeks
- **OTP TTL:** 5 minutes; 3 attempts max before lockout
- **Regulatory:** SMS content must comply with CITC rules; no unsolicited marketing without opt-in

---

## 7. Security & Compliance

### 7.1 NCA ECC Compliance Checklist

| Control Domain | Required Action | Owner |
|---------------|----------------|-------|
| Identity & Access | MFA on all admin accounts; RBAC enforced; PAM for privileged access | Partner |
| Encryption | AES-256 at rest; TLS 1.2+ in transit; AWS KMS CMK per data class | Partner |
| Vulnerability Management | Monthly automated scans; critical CVEs patched within 72h | Partner |
| Logging & Monitoring | Centralized SIEM; 90-day hot log retention; 1-year cold | Partner |
| Incident Response | Documented IR plan; 24/7 on-call; CERT-SA notification capability | Partner |
| Backup & Recovery | Daily encrypted backups; quarterly DR drill; RTO 4h / RPO 1h | Partner |
| Secure Development | SAST/DAST in CI pipeline; OWASP Top 10 mitigated; dependency audit | Partner |
| Physical Security | AWS shared responsibility model covers physical; document in compliance register | N/A (AWS) |

### 7.2 Penetration Testing Requirements

- **Frequency:** Annual full-scope pentest + quarterly targeted tests on new features
- **Scope:** External network, web application (OWASP WSTG), API, mobile apps
- **Standard:** OWASP Testing Guide v4.2; PTES
- **Tester Qualification:** OSCP, CEH, or equivalent; must be a recognized Saudi-licensed security firm for NCA compliance reporting
- **Reporting:** Full report including CVSS scores; critical/high findings must be remediated before go-live
- **Coordination:** Partner must provide pentest reports to Genesis AI within 5 business days of completion

### 7.3 Encryption Standards

| Layer | Standard | Key Management |
|-------|----------|---------------|
| Data at Rest | AES-256-GCM | AWS KMS CMK; automatic annual rotation |
| Data in Transit | TLS 1.3 (TLS 1.2 minimum) | ACM-managed certificates; auto-renewal |
| Database | AWS RDS encryption; transparent data encryption | KMS CMK |
| S3 | SSE-KMS | Customer-managed key per bucket |
| Secrets | AWS Secrets Manager | Automatic rotation; no hardcoded credentials |
| Backups | AES-256 encrypted; same KMS CMK | |

### 7.4 Authentication & Authorization

- **Authentication:** OAuth 2.0 + OIDC; JWT access tokens (15-min expiry); refresh tokens (7-day, rotated)
- **MFA:** TOTP (Google Authenticator-compatible) mandatory for all users; SMS OTP as fallback
- **Session Management:** Secure, HttpOnly, SameSite=Strict cookies; session invalidation on logout
- **Authorization:** RBAC with roles: `admin`, `operator`, `viewer`, `api_client`; attribute-based access control for data isolation
- **API Security:** Rate limiting (per-IP and per-user); API keys for machine-to-machine; JWT for user-facing APIs

### 7.5 Audit Logging Requirements

All the following events MUST be logged with timestamp, actor, resource, action, source IP:

- User authentication events (success, failure, MFA)
- Admin actions (user management, configuration changes)
- Data access to PII fields
- Payment transaction initiation and completion
- API key creation/revocation
- Policy/permission changes

Log format: JSON structured logs → CloudWatch Logs → S3 archival (1 year)

---

## 8. API & SDK Documentation for Partner

### 8.1 API Architecture

- **Style:** RESTful JSON API; OpenAPI 3.1 specification provided separately
- **Base URL:** `https://api.sa.genesisai.com/v1` (production); `https://api-sandbox.sa.genesisai.com/v1` (sandbox)
- **Authentication:** Bearer token (JWT) in `Authorization` header
- **Versioning:** URI versioning (`/v1`, `/v2`); 12-month deprecation notice for breaking changes
- **Error Format:** RFC 7807 Problem Details (`application/problem+json`)

### 8.2 Core Endpoint Categories

| Category | Base Path | Description |
|----------|-----------|-------------|
| Authentication | `/v1/auth` | Login, token refresh, MFA, logout |
| Users | `/v1/users` | User CRUD, profile, preferences |
| AI Services | `/v1/ai` | Model inference, pipeline execution |
| Payments | `/v1/payments` | Initiate, confirm, refund, history |
| Content | `/v1/content` | Bilingual content delivery |
| Admin | `/v1/admin` | User management, configuration |
| Webhooks | `/v1/webhooks` | Register/manage webhook endpoints |
| Health | `/v1/health` | Liveness and readiness probes |

### 8.3 Authentication Flow

```
1. POST /v1/auth/login
   Body: { email, password }
   Response: { mfa_required: true, mfa_token: "..." }

2. POST /v1/auth/mfa/verify
   Body: { mfa_token, otp_code }
   Response: { access_token, refresh_token, expires_in: 900 }

3. API calls: Authorization: Bearer <access_token>

4. POST /v1/auth/refresh
   Body: { refresh_token }
   Response: { access_token, refresh_token (rotated) }
```

### 8.4 Webhook Specification

- **Delivery:** HTTP POST to partner-registered URL; JSON body
- **Signature:** `X-Genesis-Signature: sha256=<HMAC-SHA256(secret, body)>` — verify before processing
- **Retry Policy:** Exponential backoff; 3 retries over 24 hours on non-2xx response
- **Event Types:** `payment.completed`, `payment.failed`, `user.created`, `ai.job.completed`, `ai.job.failed`
- **Idempotency:** Each event has a unique `event_id`; partner must handle duplicate delivery

### 8.5 Rate Limits

| Tier | Limit | Window |
|------|-------|--------|
| Unauthenticated | 20 req/IP | 1 minute |
| Authenticated (Standard) | 300 req/user | 1 minute |
| AI Inference | 60 req/user | 1 minute |
| Admin | 100 req/admin | 1 minute |

Headers: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`  
Exceeded: `429 Too Many Requests` with `Retry-After` header

---

## 9. Acceptance Criteria

### 9.1 Pre-Launch Checklist

The partner delivery will be validated against the following criteria before Genesis AI signs off on go-live:

#### Infrastructure & Operations
- [ ] All services deployed in AWS me-south-1 (or approved equivalent)
- [ ] No PII stored outside approved regions
- [ ] Multi-AZ deployment confirmed for all stateful services
- [ ] Auto-scaling configured and load-tested to 3× projected peak traffic
- [ ] DR failover tested with RTO ≤ 4h and RPO ≤ 1h demonstrated
- [ ] Monitoring dashboards live (CloudWatch + alerting to on-call channel)
- [ ] SIEM ingesting all required log streams

#### Security & Compliance
- [ ] NCA ECC self-assessment completed and submitted
- [ ] Penetration test completed; all critical/high findings remediated
- [ ] PDPL data mapping documented
- [ ] ZATCA e-invoicing integration live and tested
- [ ] Encryption verified (at rest + in transit) via AWS Config rules
- [ ] Secrets Manager in use; zero hardcoded credentials in codebase
- [ ] WAF rules active and tested

#### Localization
- [ ] Full Arabic RTL UI rendering verified across Chrome, Firefox, Safari, mobile
- [ ] Arabic text search returning correct results (diacritics-insensitive)
- [ ] Hijri calendar display working where required
- [ ] All legal/compliance text (privacy policy, terms) translated and legally reviewed in Arabic
- [ ] Currency, number, and date formatting using `ar-SA` locale

#### Integrations
- [ ] mada payment: end-to-end test transaction in sandbox and production
- [ ] STC Pay: end-to-end test in sandbox and production
- [ ] SADAD: bill registration and reconciliation tested
- [ ] Nafath ID verification: successful identity verification in staging
- [ ] ZATCA Fatoorah: sample invoice generated and validated
- [ ] SMS OTP delivery tested with Saudi mobile numbers

#### Performance
- [ ] Load test results: P95 API latency < 200ms at 2× peak load
- [ ] LCP < 2.5s on simulated 4G from Riyadh
- [ ] CDN cache hit rate > 85% for static assets

#### Documentation
- [ ] Runbook for all operational procedures
- [ ] Architecture diagrams updated and versioned
- [ ] API documentation (OpenAPI spec) current and accurate
- [ ] Incident response contacts and escalation matrix provided

### 9.2 Acceptance Sign-Off Process

1. Partner submits delivery package: code, IaC, documentation, test results
2. Genesis AI CTO reviews architecture and security posture (5 business days)
3. Independent pentest conducted (Genesis AI commissioned)
4. Staged rollout: 5% → 25% → 100% traffic over 2 weeks
5. Post-launch 30-day hypercare period: partner on-call SLA ≤ 4h response

---

## 10. Partner Engagement Rules

- **Code Ownership:** All source code, IaC (Terraform/CDK), and documentation delivered to Genesis AI as work-for-hire
- **Subcontracting:** Any subcontractors must be pre-approved in writing; must sign Genesis AI NDA and comply with PDPL
- **Communication:** Weekly status calls; Slack/Teams channel for day-to-day; critical issues via dedicated escalation path
- **Change Control:** Any scope changes require signed change request; no unilateral modifications to security or compliance controls
- **Credentials:** All cloud credentials provisioned via IAM with least-privilege; partner receives temporary credentials via AWS IAM Identity Center; revoked on contract end

---

## 11. Open Questions / Decisions Required

| # | Question | Owner | Due |
|---|----------|-------|-----|
| 1 | Confirm cloud provider: AWS me-south-1 vs STC Cloud vs hybrid | Genesis AI CEO + Partner | Pre-contract |
| 2 | Nafath integration required from day 1, or phase 2? | Business/Legal | Week 1 |
| 3 | SADAD biller registration timeline — start immediately | Business Dev | ASAP |
| 4 | Arabic content translation vendor selection | CMO | Week 2 |
| 5 | STC Pay or other wallet priority over mada? | Product | Week 1 |
| 6 | Government/enterprise clients: additional NCA controls (CSCC)? | CTO + Legal | Week 2 |

---

*Document prepared by Genesis AI CTO Office. Last updated: 2026-04-18. For questions, contact the CTO office before implementation begins.*
