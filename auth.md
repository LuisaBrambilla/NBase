# Gen360 — Certificate-Based Authentication (CBA) Analysis

## Executive Summary

This document evaluates replacing the existing **TOTP-based MFA** (Time-based One-Time Password) with **Certificate-Based Authentication (CBA)** in the Gen360 admin panel. It covers options, costs, hardware requirements, certificate types, private PKI support, and implementation approaches specific to our FastAPI + PostgreSQL + vanilla JS stack.

---

## 1. Current Authentication Architecture

### What We Have Today

| Component | Implementation |
|-----------|---------------|
| **Login** | Email + password → JWT (HS256) |
| **MFA** | TOTP (6-digit code, 30s period, ±1 window) |
| **Token** | JWT stored in `localStorage`, 60-min expiry |
| **Password hash** | PBKDF2-SHA256, 200k iterations |
| **Route protection** | FastAPI HTTP middleware + `require_admin()` dependency |
| **Frontend** | Vanilla JS, QRious library for QR code generation |
| **Auth library** | Fully custom (no PyJWT, no pyotp, no bcrypt) |

### Files Involved

**Backend:**
- `api/auth.py` — JWT generation/verification, PBKDF2 hashing, TOTP logic
- `api/main.py` — Middleware, login/register/MFA endpoints
- `api/queries.py` — DB queries for admin CRUD
- `db/models.sql` — Admins table schema
- `db/migracoes/003_admin_mfa.sql` — MFA columns migration

**Frontend:**
- `admin_frontend/admin_auth.js` — Login/register logic
- `admin_frontend/admin_session.js` — Token/session management
- `admin_frontend/admin_profile.js` — MFA setup/disable UI
- `admin_frontend/config.js` — API URL configuration

### Current Flow

```
User → Email + Password → Server validates → MFA required?
  → Yes → User enters 6-digit TOTP from authenticator app → Server validates → JWT issued
  → No  → JWT issued
→ JWT stored in localStorage → Sent as Bearer token on every request
```

---

## 2. What Is Certificate-Based Authentication (CBA)?

CBA uses **X.509 digital certificates** instead of (or in addition to) passwords and OTP codes. The client presents a cryptographic certificate during TLS handshake (mutual TLS / mTLS), proving identity through public-key cryptography rather than shared secrets.

### How It Works

```
Client (browser/device) has:
  ├── Private Key (never leaves device)
  └── X.509 Certificate (signed by trusted CA)

Server has:
  └── Trusted CA certificate(s)

TLS Handshake:
  1. Client connects to server
  2. Server requests client certificate
  3. Client presents certificate
  4. Server validates: signature chain → CA trust → expiration → revocation
  5. If valid → identity extracted from certificate subject/SAN
  6. Authentication complete — no password or OTP needed
```

---

## 3. CBA Options for Gen360

### Option A: Application-Level mTLS (FastAPI + Uvicorn)

**Description:** Configure Uvicorn to require client certificates directly. The FastAPI app validates certificates and extracts identity.

**How it works:**
- Uvicorn starts with an SSL context requiring client certificates
- Python's `ssl` module validates against trusted CA
- FastAPI middleware extracts certificate subject (email, CN) from the TLS connection
- Maps certificate identity to admin record in database

**Pros:**
- Full control over certificate validation logic
- No external services required
- Works in local dev and production
- Free (no cloud service costs)

**Cons:**
- Must manage certificate distribution to users manually
- Browser certificate selection UX can be confusing
- Certificate revocation (CRL/OCSP) must be implemented manually
- More complex deployment (TLS termination at app level vs. reverse proxy)

**Cost:** Free (self-managed PKI + OpenSSL)

**Implementation effort:** Medium-High

---

### Option B: Reverse Proxy mTLS (NGINX / Traefik in front of FastAPI)

**Description:** NGINX or Traefik terminates mTLS, validates client certificates, and forwards verified identity to FastAPI via HTTP headers.

**How it works:**
- NGINX/Traefik configured with `ssl_client_certificate` and `ssl_verify_client on`
- On successful mTLS, forwards `X-Client-Cert-DN` or `X-Client-Cert-Subject` header
- FastAPI reads the header and maps to admin identity
- No TLS handling needed in the Python app

**Pros:**
- Clean separation: proxy handles TLS, app handles business logic
- NGINX/Traefik are battle-tested for TLS
- Easier certificate revocation (NGINX supports CRL files)
- Works well with Docker/Kubernetes

**Cons:**
- Additional infrastructure component (NGINX container)
- Must trust the proxy (header injection protection needed)
- Not applicable to Azure App Service directly (App Service has its own mechanism)

**Cost:** Free (NGINX is open source)

**Implementation effort:** Medium

---

### Option C: Azure App Service Client Certificates

**Description:** Azure App Service natively supports requiring client certificates. The certificate is forwarded to the app via the `X-ARR-ClientCert` header.

**How it works:**
- Enable "Client certificate mode" in Azure App Service settings (Required or Optional)
- Azure terminates TLS and forwards the Base64-encoded client certificate in `X-ARR-ClientCert` header
- FastAPI reads and validates the certificate from the header
- Maps certificate subject to admin record

**Pros:**
- Native Azure integration, no extra infrastructure
- Azure handles TLS termination
- Works with existing deployment pipeline
- Supports certificate thumbprint/subject validation

**Cons:**
- **Requires Basic tier or higher** (not available on Free/Shared)
- Azure doesn't validate the certificate against a CA — your app must do it
- Certificate distribution still manual
- Browser cert selection UX varies

**Cost:** Azure App Service Basic plan starts at ~$13/month (B1). Current plan may already be Basic+ (check your App Service Plan).

**Implementation effort:** Medium

---

### Option D: Microsoft Entra ID CBA (Azure AD)

**Description:** Delegate authentication to Microsoft Entra ID (formerly Azure AD) with CBA enabled. Users authenticate via Entra with their certificates, and Gen360 trusts the Entra tokens.

**How it works:**
- Configure Entra ID CBA authentication policy
- Upload trusted CA certificates to Entra
- Gen360 becomes an Entra-registered application
- Users sign in via Entra (certificate prompt in browser)
- Gen360 receives OAuth2/OIDC tokens from Entra
- Major refactor: replace custom JWT with MSAL/OIDC flow

**Pros:**
- Enterprise-grade, Microsoft-managed
- Supports smart cards, YubiKeys, TPM-backed certificates
- Centralized user management and audit logs
- Phishing-resistant (FIDO2-level assurance)
- CRL/OCSP handled by Entra

**Cons:**
- **Requires Entra ID P1 or P2 license** for full CBA features
- Significant refactor: must replace entire custom auth with OIDC/OAuth2
- Adds Microsoft dependency
- More complex for a small admin panel

**Cost:** Entra ID P1 ~$6/user/month, P2 ~$9/user/month. Free tier has limited CBA support.

**Implementation effort:** High

---

### Option E: Hybrid — CBA + Existing Password/MFA (Phased Approach)

**Description:** Add CBA as an additional authentication method alongside existing password+TOTP. Admins can choose either method.

**How it works:**
- Implement Option A, B, or C for CBA
- Keep existing login flow as fallback
- Admin record in DB tracks `auth_method` preference (`totp`, `certificate`, or `both`)
- Login page offers "Sign in with certificate" button alongside password form
- Gradually migrate users to CBA

**Pros:**
- Zero disruption — existing auth continues working
- Graceful migration path
- Users can fall back to TOTP if certificate issues arise
- Test CBA with a subset of admins first

**Cons:**
- More code to maintain (two auth paths)
- Must manage both TOTP secrets and certificate mappings

**Cost:** Same as chosen CBA option

**Implementation effort:** Medium (additive, not replacement)

---

## 4. Comparison Matrix

| Criteria | Option A (App mTLS) | Option B (Proxy mTLS) | Option C (Azure App Service) | Option D (Entra ID) | Option E (Hybrid) |
|----------|---------------------|----------------------|-------------------------------|---------------------|--------------------|
| **Cost** | Free | Free | ~$13/mo (Basic plan) | ~$6-9/user/mo | Varies by base |
| **Hardware needed** | No (soft certs) | No | No | Optional (smart cards) | No |
| **Private PKI** | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes |
| **Implementation effort** | Medium-High | Medium | Medium | High | Medium |
| **Code changes** | Moderate | Moderate | Moderate | Major refactor | Additive |
| **Phishing resistance** | ✅ Strong | ✅ Strong | ✅ Strong | ✅ Strongest | ✅ Strong |
| **Works locally** | ✅ Yes | ✅ Yes (Docker) | ❌ Azure only | ❌ Azure only | ✅ Yes |
| **Production ready** | ⚠️ Manual ops | ✅ Yes | ✅ Yes | ✅ Enterprise | ✅ Yes |
| **User experience** | Browser cert picker | Browser cert picker | Browser cert picker | Entra login + cert | Choice of methods |
| **Disruption** | Full replacement | Full replacement | Full replacement | Full replacement | Zero disruption |

---

## 5. Certificate Types Supported

### X.509 Client Certificates (Standard)

All CBA options use **X.509 v3** certificates. These support:

| Algorithm | Key Size | Recommended | Notes |
|-----------|----------|-------------|-------|
| **RSA** | 2048-bit | ✅ Yes | Most compatible, widely supported |
| **RSA** | 4096-bit | ✅ Yes | Higher security, slightly slower |
| **ECDSA** | P-256 | ✅ Yes | Smaller keys, faster, modern |
| **ECDSA** | P-384 | ✅ Yes | Higher security elliptic curve |
| **Ed25519** | 256-bit | ⚠️ Limited | Not supported by all browsers |

### Certificate Fields Used for Authentication

```
Subject:
  CN = Admin Full Name
  E  = admin@example.com          ← Primary identity mapping
  O  = Organization Name
  OU = Department

Subject Alternative Name (SAN):
  email: admin@example.com         ← Preferred identity field
  URI:   urn:gen360:admin:<uuid>   ← Optional: direct admin ID mapping

Key Usage:
  Digital Signature                ← Required for client auth
  Key Encipherment                 ← Required for TLS

Extended Key Usage:
  Client Authentication (1.3.6.1.5.5.7.3.2)  ← Required
```

### Certificate Storage Options

| Storage | Security Level | Hardware Required | Notes |
|---------|---------------|-------------------|-------|
| **OS Certificate Store** | Medium | No | Windows, macOS, Linux built-in |
| **Browser Certificate Store** | Medium | No | Firefox has its own store |
| **Smart Card (PIV)** | High | Yes (~$30-100) | YubiKey, Thales, SafeNet |
| **USB Security Key** | High | Yes (~$25-70) | YubiKey 5 NFC, Feitian |
| **TPM** | High | No (built into most PCs) | Trusted Platform Module |
| **PKCS#12 (.p12/.pfx) file** | Low-Medium | No | Password-protected file |

---

## 6. Private PKI Support

### Can We Use Our Own Certificate Authority?

**Yes, all options support private PKI.** You do NOT need to purchase certificates from a public CA (like DigiCert, Let's Encrypt, etc.) for client authentication.

### Setting Up a Private PKI with OpenSSL (Free)

```bash
# 1. Create Root CA
openssl genrsa -out ca-key.pem 4096
openssl req -new -x509 -key ca-key.pem -out ca-cert.pem -days 3650 \
  -subj "/C=BR/O=Gen360/CN=Gen360 Root CA"

# 2. Create Intermediate CA (recommended for production)
openssl genrsa -out intermediate-key.pem 4096
openssl req -new -key intermediate-key.pem -out intermediate.csr \
  -subj "/C=BR/O=Gen360/CN=Gen360 Intermediate CA"
openssl x509 -req -in intermediate.csr -CA ca-cert.pem -CAkey ca-key.pem \
  -CAcreateserial -out intermediate-cert.pem -days 1825

# 3. Issue Client Certificate for an Admin
openssl genrsa -out admin-key.pem 2048
openssl req -new -key admin-key.pem -out admin.csr \
  -subj "/C=BR/O=Gen360/CN=Thiago Beier/emailAddress=thiago.beier@gmail.com"
openssl x509 -req -in admin.csr -CA intermediate-cert.pem -CAkey intermediate-key.pem \
  -CAcreateserial -out admin-cert.pem -days 365

# 4. Package for browser import (PKCS#12)
openssl pkcs12 -export -out admin.p12 \
  -inkey admin-key.pem -in admin-cert.pem -certfile intermediate-cert.pem \
  -name "Gen360 Admin - Thiago Beier"
```

### Private PKI Options Comparison

| PKI Solution | Cost | Complexity | Best For |
|-------------|------|------------|----------|
| **OpenSSL (manual)** | Free | Low (few users) | Small teams, dev/test |
| **step-ca (Smallstep)** | Free (open source) | Medium | Automated cert lifecycle |
| **EJBCA Community** | Free (open source) | High | Enterprise, compliance |
| **HashiCorp Vault PKI** | Free (open source) | Medium | DevOps/cloud-native |
| **Microsoft AD CS** | Windows Server license | High | Windows-centric orgs |
| **Microsoft Cloud PKI** | Intune license req. | Medium | Azure/Entra integrated |
| **AWS Private CA** | ~$400/mo per CA | Low | AWS-centric orgs |

---

## 7. Hardware Requirements

### Is Hardware Required?

**No.** CBA can work entirely with software-based certificates (stored in OS certificate stores or .p12 files). Hardware is optional but recommended for highest security.

### Hardware Options (If Desired)

| Device | Price | Features | Notes |
|--------|-------|----------|-------|
| **YubiKey 5 NFC** | ~$50 | USB-A/NFC, PIV, FIDO2 | Most popular, cross-platform |
| **YubiKey 5C NFC** | ~$55 | USB-C/NFC, PIV, FIDO2 | For modern laptops |
| **YubiKey 5 Nano** | ~$50 | USB-A, always inserted | For desktop workstations |
| **Feitian ePass** | ~$25 | USB-A, PIV | Budget option |
| **Thales SafeNet** | ~$50-100 | USB, smart card | Enterprise standard |
| **Smart Card + Reader** | ~$15 card + $15 reader | Traditional PIV | Government/military |

### When Hardware Is Recommended

- Admins accessing sensitive government data (Gen360 handles DODF/legal norms)
- Compliance requirements (FIPS 140-2, Common Criteria)
- Protection against key theft (private key never leaves hardware)
- Remote/untrusted device scenarios

### When Software Certs Are Sufficient

- Small admin team (currently 1 admin)
- Internal/trusted network
- Dev/test environments
- Cost-sensitive deployments

---

## 8. Cost Analysis

### Option A/B: Self-Managed mTLS (Recommended for Gen360)

| Item | One-Time Cost | Monthly Cost |
|------|--------------|--------------|
| OpenSSL PKI setup | $0 (free) | $0 |
| Certificate generation | $0 (free) | $0 |
| NGINX (if Option B) | $0 (free) | $0 |
| Code implementation | Developer time | $0 |
| **Total** | **$0** | **$0** |

### Option C: Azure App Service CBA

| Item | One-Time Cost | Monthly Cost |
|------|--------------|--------------|
| App Service Basic plan | $0 | ~$13/mo (if upgrading from Free) |
| Certificate generation | $0 (private PKI) | $0 |
| Code implementation | Developer time | $0 |
| **Total** | **$0** | **~$13/mo** |

### Option D: Microsoft Entra ID CBA

| Item | One-Time Cost | Monthly Cost |
|------|--------------|--------------|
| Entra ID P1 license | $0 | ~$6/user/mo |
| App registration | $0 | $0 |
| MSAL library integration | Developer time | $0 |
| Code refactor | Developer time (significant) | $0 |
| **Total** | **$0** | **~$6/user/mo** |

### Optional Hardware Add-On (Any Option)

| Item | One-Time Cost | Monthly Cost |
|------|--------------|--------------|
| YubiKey 5 NFC (per admin) | ~$50/key | $0 |
| Smart Card + Reader | ~$30/set | $0 |

---

## 9. Recommendation for Gen360

### 🏆 Recommended: Option E (Hybrid) with Option A (App-Level mTLS) as base

**Why:**

1. **Zero cost** — Private PKI with OpenSSL, no cloud service fees
2. **Zero disruption** — Existing TOTP auth continues working during migration
3. **Works locally** — Full dev/test without Azure dependency
4. **Small team** — Only 1 admin currently; manual cert management is trivial
5. **Full control** — Custom implementation matches existing codebase style
6. **Phishing-resistant** — Certificates cannot be phished like TOTP codes
7. **Gradual migration** — Test CBA thoroughly before removing TOTP

### Implementation Phases

**Phase 1: Infrastructure** (Private PKI + Certificate Generation)
- Set up OpenSSL CA (root + intermediate)
- Generate admin client certificate
- Create certificate management scripts

**Phase 2: Backend** (FastAPI mTLS Support)
- Add certificate validation middleware
- Add `cert_thumbprint` and `cert_subject` columns to admins table
- Create certificate-based authentication endpoint
- Keep existing JWT issuance (certificate auth → JWT → existing session flow)

**Phase 3: Frontend** (Certificate Login Option)
- Add "Sign in with Certificate" button on login page
- Handle browser certificate selection prompt
- Graceful fallback to password+TOTP

**Phase 4: Production** (Azure App Service Integration)
- Enable client certificates on Azure App Service
- Upload CA certificate
- Test with production admin(s)

**Phase 5: Migration** (Optional — Remove TOTP)
- Once all admins have certificates → make CBA mandatory
- Remove TOTP columns and code (or keep as emergency fallback)

---

## 10. Quick-Start Guide: What You Need to Begin

### Prerequisites (All Free)

- [x] OpenSSL (comes with Git for Windows)
- [x] Python 3.10+ (already have)
- [x] FastAPI (already have)
- [ ] `cryptography` Python package (for cert parsing — `pip install cryptography`)

### First Steps

1. **Generate a test CA and client certificate** (30 minutes)
2. **Add certificate auth endpoint to FastAPI** (2-4 hours)
3. **Test locally with browser** (1 hour)
4. **Add "Sign in with Certificate" to frontend** (2-3 hours)

### Files That Need Changes

| File | Changes |
|------|---------|
| `api/auth.py` | Add `validar_certificado()`, `extrair_identidade_cert()` |
| `api/main.py` | Add `/admin/login/cert` endpoint, update middleware |
| `api/queries.py` | Add `obter_admin_por_cert_thumbprint()`, `atualizar_admin_cert()` |
| `db/migracoes/005_admin_cert.sql` | Add `cert_thumbprint`, `cert_subject`, `auth_method` columns |
| `admin_frontend/admin_login.html` | Add certificate login button |
| `admin_frontend/admin_auth.js` | Add certificate login handler |
| `admin_frontend/admin_profile.js` | Add certificate management UI |
| `requirements.txt` | Add `cryptography` |
| **New:** `scripts/gen_certs.sh` | PKI setup and cert generation scripts |
| **New:** `certs/` directory | CA cert, CRL (NOT private keys) |

---

## 11. Security Comparison: CBA vs Current TOTP

| Attack Vector | TOTP (Current) | CBA (Proposed) |
|--------------|----------------|----------------|
| **Phishing** | ⚠️ Vulnerable (code can be relayed) | ✅ Immune (private key never transmitted) |
| **Credential stuffing** | ⚠️ Password still needed | ✅ No password to stuff |
| **Man-in-the-middle** | ⚠️ TOTP can be intercepted in real-time | ✅ TLS mutual auth prevents MITM |
| **Key theft (software)** | ⚠️ TOTP secret in DB plaintext | ⚠️ Private key on disk (mitigated with hardware) |
| **Key theft (hardware)** | N/A | ✅ Private key locked in hardware token |
| **Social engineering** | ⚠️ User can be tricked to share code | ✅ Certificate can't be "shared" verbally |
| **Replay attacks** | ✅ TOTP expires in 30s | ✅ TLS challenge-response prevents replay |
| **Account recovery** | ✅ Easy (reset TOTP) | ⚠️ Must reissue certificate |
| **User convenience** | ⚠️ Must open authenticator app | ✅ Automatic (browser selects cert) |

---

## 12. Glossary

| Term | Definition |
|------|-----------|
| **CBA** | Certificate-Based Authentication |
| **mTLS** | Mutual TLS — both client and server present certificates |
| **PKI** | Public Key Infrastructure — system for managing certificates |
| **CA** | Certificate Authority — trusted entity that signs certificates |
| **X.509** | Standard format for digital certificates |
| **TOTP** | Time-based One-Time Password (current MFA method) |
| **CRL** | Certificate Revocation List — list of revoked certificates |
| **OCSP** | Online Certificate Status Protocol — real-time revocation check |
| **PKCS#12** | File format (.p12/.pfx) for bundling certificate + private key |
| **PIV** | Personal Identity Verification — smart card standard |
| **SAN** | Subject Alternative Name — certificate field for identities |
| **HSM** | Hardware Security Module — secure key storage device |

---

## 13. References

- [Microsoft Entra CBA Setup Guide](https://learn.microsoft.com/en-us/entra/identity/authentication/how-to-certificate-based-authentication)
- [Azure App Service mTLS Configuration](https://learn.microsoft.com/en-us/azure/app-service/app-service-web-configure-tls-mutual-auth)
- [FastAPI mTLS with Self-Signed Certificates](https://github.com/sergioaz/FastAPI-mTLS)
- [OpenSSL Certificate Authority Guide](https://openssl-ca.readthedocs.io/)
- [Smallstep step-ca (Automated PKI)](https://smallstep.com/docs/step-ca/)
- [NIST SP 800-63B (Digital Identity Guidelines)](https://pages.nist.gov/800-63-3/sp800-63b.html)
- [RFC 5280 (X.509 PKI Certificates)](https://tools.ietf.org/html/rfc5280)
- [RFC 6238 (TOTP Algorithm)](https://tools.ietf.org/html/rfc6238)

---

*Document generated: April 2026*
*Project: Gen360 — Resolução de Normas DODF*
*Current auth: Custom JWT + TOTP MFA*
*Recommended path: Hybrid CBA (Option E) with App-Level mTLS (Option A)*
