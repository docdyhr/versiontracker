# Security and Vulnerability Disclosure Policy

Thank you for your interest in helping keep VersionTracker secure. We take security seriously.
We appreciate responsible disclosure of vulnerabilities.

## Reporting a Security Vulnerability

If you discover a security issue in VersionTracker, please report it privately and responsibly:

- Email: <security@versiontracker.dev>  
- PGP Key (optional):  

  ```text
  mQINBF/... (PGP key fingerprint here)
  ```

- Subject line: `VersionTracker Vulnerability Report`

Include the following information in your report:

1. **Description** of the vulnerability and its impact.  
2. **Steps to reproduce** or a minimal proof-of-concept.  
3. Version of VersionTracker and environment details (OS, Python version).  
4. Any relevant logs or screenshots (avoid sharing sensitive data).

## Response Process

1. **Acknowledgment**  
   We aim to respond within 3 business days confirming receipt of your report.

2. **Initial Triage**  
   We will assess the severity and scope, and may request further details.

3. **Remediation**  
   - Critical/high severity: patch released in 30 days or less.  
   - Medium severity: patch released in 60 days.  
   - Low severity: patch released in 90 days.  
   We may provide interim mitigations if a full fix cannot be delivered immediately.

4. **Public Disclosure**  
   We will coordinate a disclosure timeline with you.
   Public advisories will be published here once a fix is available.

## Supported Versions

We backport security fixes to the following supported releases:

- **Latest stable minor** (e.g., 2.x)  
- **Previous minor**, if still within its maintenance window

Please include the version you are using in your report to help us determine support.

## Confidentiality and Safe Harbor

All reports and communications will be treated as confidential. We commit to:

- Not initiating legal action against researchers acting in good faith.  
- Acknowledging your contribution in release notes or an acknowledgments file (unless you request anonymity).

## Disclosure Exceptions

If after 90 days a fix is not released, or the issue has not been addressed, you may publicly disclose in accordance
with any applicable laws or regulations.

## Security Practices

We continuously improve our security posture by:

- Running static analysis (Bandit, CodeQL).  
- Checking dependencies for vulnerabilities (Safety, pip-audit).  
- Performing secret scanning (TruffleHog).  
- Keeping dependencies up to date via Dependabot.

## Thank You

We appreciate the assistance of the security community.
Your responsible disclosure helps protect all users of VersionTracker.
