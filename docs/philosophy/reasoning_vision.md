# Reasoning Vision

## Overview

The next major stage is a Reasoning Engine that operates over structured evidence. This is not a replacement for the language model, but a separate internal analyst.

## What the Reasoning Engine Should Answer

The system should be able to answer questions such as:

- What do I know?
- What evidence supports it?
- What conflicts exist?
- What changed?
- What remains uncertain?
- What should be updated?

## Intended Architecture

The reasoning engine will sit above evidence and below the conversational interface. It will evaluate the state of the system and highlight the most important issues.

## Planned Responsibilities

- identify the strongest-supported beliefs
- identify blocked or uncertain goals
- identify stale observations
- identify contradictions requiring attention
- trace the ripple effects of dependency changes
- recommend the next highest-value action

## Design Intent

The reasoning engine should make the system more deliberate, not more speculative. Its job is not to invent certainty. Its job is to make the existing evidence easier to interpret and act on.
