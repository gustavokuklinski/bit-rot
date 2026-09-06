# AI Disclosure

**Last Updated:** September 1, 2026

## Overview
In the spirit of transparency and open-source collaboration, this document outlines the use of Generative AI in the development of this repository. While AI tools were leveraged to accelerate certain aspects of development, all output has been subject to human review and validation.

---

## AI Models Used
The following Large Language Models (LLMs) were utilized during the development lifecycle:

- **gemma3:31B**
- **Gemini 2.5 Pro**
- **Gemini 3.1 Pro**
- **Qwen3.5**
- **ChatGPT-5o**
- **DeepSeek-R1**

> **Agent Usage:** No autonomous AI agents were deployed. All interactions were session-based, prompt-by-prompt, with no continuous autonomous loops.

---

## Usage Breakdown
The extent of AI involvement varied by domain:

| Domain | Method | Details |
| :--- | :--- | :--- |
| **Code** | **LLM (AI-Assisted)** | AI was used to generate boilerplate, suggest refactors, write utility functions, debug errors, and produce documentation strings (docblocks). All generated code was reviewed, tested, and adapted by human developers before inclusion. |
| **Audio Content** | **LLM (AI-Assisted)** | AI was used to generate audio speak and music files |
| **Content** | **Human** | All written content—including this disclosure, the README, guides, and in-app user-facing text—was authored by humans without AI generation. |
| **Design** | **Human** | The architecture, system design, user experience flows, and visual styling decisions were conceived and executed entirely by human contributors. |

---

## Human Oversight & Review
Every AI-suggested code commit has undergone a rigorous review process to ensure:

- **Security:** No injected vulnerabilities or insecure patterns.
- **Maintainability:** Code aligns with project style guidelines and standards.
- **Accuracy:** Logic correctly implements the intended human-designed architecture.

---

## Disclaimer
While AI assistance significantly sped up development, the contributors assume full responsibility and ownership over the final codebase. Users of this repository should treat the code as human-produced software and apply standard due diligence regarding testing and deployment.

**Questions?** Feel free to open an issue regarding specific AI-generated portions of the code.