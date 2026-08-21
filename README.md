# Machine Learning Security

Machine learning is being incorporated into technical products at an explosive rate, but many people, including those with strong technical backgrounds, do not fully understand how these systems work, what they are capable of, or the security risks they introduce.

This repository contains hands-on proof-of-concept projects exploring machine learning, AI, and security. Topics include computer vision, CAPTCHA breaking, image deblurring, regression, classification, adversarial machine learning, and agentic AI.

The projects explore both offensive and defensive concepts, including poisoning and evasion attacks, deep neural rejection, AI-assisted development, and the security implications of increasingly autonomous AI systems.

## Projects

### Personal AI Infrastructure (PAI) and LifeOS

[View the project walkthrough](./personal-ai-infrastructure/README.md)

A hands-on exploration of personal agentic AI infrastructure using Claude Code, PAI, and LifeOS inside an isolated Debian VM.

The project explores:

- setting up PAI and LifeOS with Claude Code
- isolating different AI environments with separate Linux users
- understanding permissions and access available to an agentic system
- comparing an earlier PAI release with the current LifeOS architecture
- configuring persistent instructions for AI-assisted development
- exploring privacy and security considerations
- experimenting with agentic workflows such as email triage

## AI-Assisted Development

Some projects in this repository use Claude Code for AI-assisted development.

A `CLAUDE.md` file provides persistent instructions and behavioral guardrails for the coding agent. The guidelines emphasize:

- stating assumptions before implementation
- asking for clarification when requirements are ambiguous
- preferring simple solutions over unnecessary complexity
- making surgical changes limited to the requested task
- defining clear and verifiable success criteria
- testing and validating changes

This is also part of the security experiment. AI-generated code is only one part of an agentic development system. The instructions, permissions, tools, context, and verification mechanisms given to an agent can also affect the security and reliability of its behavior.

See [`CLAUDE.md`](./CLAUDE.md) for the complete guidelines.

## Repository Structure

```text
Machine-Learning-Security/
│
├── README.md
├── CLAUDE.md
│
└── personal-ai-infrastructure/
    └── README.md
```

## Acknowledgments

The [`CLAUDE.md`](./CLAUDE.md) behavioral guidelines used in this repository are adapted from the [multica-ai/andrej-karpathy-skills project](https://github.com/multica-ai/andrej-karpathy-skills). The project distills common LLM coding failure modes into four development principles: Think Before Coding, Simplicity First, Surgical Changes, and Goal-Driven Execution.

The guidelines are inspired by Andrej Karpathy's observations on LLM-assisted software development and are used here as guardrails for AI-assisted development.