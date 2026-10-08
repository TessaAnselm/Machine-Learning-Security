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

### CAPTCHA Breaking

[View the project walkthrough](./captcha-breaking/README.md)

An end-to-end offense/defense demo: a real distorted-text CAPTCHA server, and a
CNN trained to break it — reaching a 92% live solve rate via transfer learning from a
pretrained ResNet18.

The project explores:

- generating and training against a real, self-hosted CAPTCHA server
- why a classic segmentation-based OCR attack fails against modern noise/distortion
- iterating from a from-scratch CNN (52-62%) to pretrained-backbone transfer learning (92%)
- measuring both offline (validation) and live attack accuracy
- what actually defends against this class of attack in practice

### ThreatVote AI

[View the project walkthrough](./threatvote-ai/README.md)

An interactive cybersecurity detection lab comparing ensemble learning
methods — Decision Tree, Random Forest, AdaBoost, and a Voting Classifier —
on labeled network traffic (CIC-IDS2017-style flows), with a Streamlit
dashboard for live hyperparameter tuning and false-positive/false-negative
analysis.

The project explores:

- bagging vs. boosting ensembles for network intrusion detection
- avoiding data leakage (identifier columns, duplicate flows, train/test separation)
- how hyperparameters (tree depth, boosting iterations, learning rate) shift the accuracy/recall tradeoff
- where each model's false positives and false negatives land, by attack family

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
├── personal-ai-infrastructure/
│   └── README.md
│
├── captcha-breaking/
│   └── README.md
│
└── threatvote-ai/
    └── README.md
```

## Acknowledgments

The [`CLAUDE.md`](./CLAUDE.md) behavioral guidelines used in this repository are adapted from the [multica-ai/andrej-karpathy-skills project](https://github.com/multica-ai/andrej-karpathy-skills). The project distills common LLM coding failure modes into four development principles: Think Before Coding, Simplicity First, Surgical Changes, and Goal-Driven Execution.

The guidelines are inspired by Andrej Karpathy's observations on LLM-assisted software development and are used here as guardrails for AI-assisted development.