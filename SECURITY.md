# Security Policy

## Supported Versions

The following versions of this project are currently being supported with security updates:

| Version | Supported          |
| ------- | ------------------ |
| 2.x     | :white_check_mark: |
| 1.x     | :x:                |

## Reporting a Vulnerability

We take security issues seriously. If you discover a security vulnerability, please follow these steps:

1.  **Do NOT create a public GitHub issue.** This allows us to fix the vulnerability before it can be exploited.
2.  Email the maintainers privately or use GitHub's "Report a vulnerability" feature if enabled.
3.  Include a detailed description of the vulnerability, steps to reproduce, and potential impact.
4.  We will acknowledge your report within 48 hours and provide an estimated timeline for a fix.

## Security Best Practices

### Secrets Management
*   Never commit secrets (API keys, tokens, passwords) to the repository.
*   Use environment variables (`.env`) for sensitive configuration.
*   The `.gitignore` file is configured to exclude common secret files.

### Dependencies
*   We use Dependabot to keep dependencies up to date.
*   Regular security audits are performed using `pip-audit` and `npm audit`.

### Code Security
*   All code changes must pass automated security scans (SAST using `bandit`).
*   Input validation and sanitization are enforced to prevent injection attacks.
