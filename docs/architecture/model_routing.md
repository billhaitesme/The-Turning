# Model Routing

## Overview

Model routing selects the appropriate model or capability for the current request. The goal is not to overcomplicate the system, but to allow different tasks to use different models without entangling the rest of the architecture.

## Current Routing

The current system uses a simple model routing strategy:

- technical requests route to a technical-oriented model
- general requests use the default general model
- vision requests use a vision-capable model

## Technical Model

Used for technical or implementation-oriented work.

## General Model

Used for general conversational assistance and high-level requests.

## Vision Model

Used for vision and multimodal scenarios.

## Future Internet Model

Planned future support for web or internet-assisted reasoning.

## Future Planner Model

Planned support for planning-oriented tasks that depend on goals and evidence.

## Future Reasoning Model

Planned support for evidence-heavy reasoning and analysis tasks that should not be delegated to a generic conversational model.

## Design Intent

Routing remains a capability layer. It should not become the place where domain logic is encoded. Domain logic belongs in the services and evidence layers.
