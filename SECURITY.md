# Security Policy

## Disclaimer of Liability

**USE AT YOUR OWN RISK.**  
This software is provided **"AS IS"**, without any warranty of any kind, express or implied, including but not limited to the warranties of merchantability, fitness for a particular purpose, or non-infringement.

The project owner and contributors are **not responsible or liable** for any damage, data loss, system failure, or any other issues—whether direct, indirect, incidental, or consequential—that may arise from using, running, modifying, or deploying this code on any machine, server, or environment.

You are solely responsible for testing, validating, and securing your own systems before using this software. By using this repository, you accept full responsibility for any outcomes.

---

## Supported Versions

Only the **latest stable release** (the `main` branch) receives active security consideration. Older versions, experimental branches, or forks are not supported.

| Version | Supported |
| :--- | :--- |
| **Latest (main)** | ✅ Active monitoring |
| All other versions / branches | ❌ Not supported |

---

## Reporting a Vulnerability or Getting in Contact

**For any security concerns, questions, or general inquiries, please open a GitHub Issue.**

We do **not** use private email for support or security reports—everything goes through the public issue tracker to keep communication transparent and traceable.

### If you are reporting a **security vulnerability**:

1. **Open a new Issue** and include `[SECURITY]` at the beginning of the title (e.g., `[SECURITY] SQL injection in login endpoint`).
2. In the issue description, **provide a high-level summary** of the vulnerability.
3. **Do NOT include full exploit details, proof-of-concept code, or step-by-step attack paths** in the public issue—this prevents malicious actors from abusing the information before a fix is released.
4. If we need more details, we will reply and may coordinate with you through GitHub's private security features (if available) or request that you share additional information securely via a direct message.

For **non-security questions** (e.g., setup help, feature clarification, or general feedback), simply open a regular issue using our [question template](.github/ISSUE_TEMPLATE/question.md) (if available) or create a blank issue with a clear description.

---

## Response & Disclosure Process

Once a security issue is reported via GitHub Issues:

1. **Acknowledgment** – We will acknowledge your report within **48–72 hours** by commenting on your issue.
2. **Validation** – We will validate the report and assess its severity.
3. **Fix Development** – A patch will be developed and tested (typically on the `main` branch).
4. **Release** – The fix will be merged and a new version will be made available.
5. **Public Disclosure** – We will close the issue and credit the reporter (if they wish) in the release notes after the fix is live.

> We appreciate **responsible disclosure**. Please refrain from sharing detailed exploit information publicly until we have released a fix.

---

## Our Commitment to Security

- All code—whether human-written or AI-assisted—undergoes human review before merging (see our [AI_DISCLOSURE.md](AI_DISCLOSURE.md) and [CONTRIBUTING.md](CONTRIBUTING.md)).
- We periodically review dependencies for known vulnerabilities.
- We rely on the community to help us identify and fix issues.

---

## License & Contribution Reminder

By submitting a security fix or any other contribution via Pull Request, you agree that your contributions become the property of the project owner under the terms of our [LICENSE](LICENSE). You may **not** re-upload, redistribute, or claim our code as your own—even if you contributed to it.

---

## Contact

**The only official way to contact us regarding security or anything else is through [GitHub Issues](https://github.com/your-username/your-repo/issues).**

Please use the appropriate issue template or prefix your issue with `[SECURITY]` for vulnerability reports.

---

Thank you for helping us keep this project safe and transparent!