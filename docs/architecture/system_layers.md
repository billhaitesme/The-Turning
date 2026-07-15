# System Layers

## Overview

OMEGA-ARC is organized as layered services. Each layer has a clear role and a clear boundary. The architecture favors composability over monolithic control flow.

## 1. UI

### Purpose
Provide the user-facing interaction surface.

### Responsibilities
- receive user input
- display generated responses
- present system state when helpful

### Inputs
- user messages
- UI state

### Outputs
- requests to the API
- rendered assistant responses

### Dependencies
- FastAPI API layer

### Future evolution
The UI may evolve into a richer interface, but the core model remains the same: the UI should remain thin and not contain domain logic.

## 2. API

### Purpose
Serve the application boundary.

### Responsibilities
- receive requests
- coordinate session data
- assemble prompt context
- return responses

### Inputs
- conversation messages
- profile and preference context
- runtime state

### Outputs
- prompt context
- final assistant response

### Dependencies
- conversation pipeline
- awareness and identity components

### Future evolution
The API should stay stable as more subsystems are introduced.

## 3. Conversation

### Purpose
Maintain the conversational context that surrounds an interaction.

### Responsibilities
- assemble history
- preserve the immediate user intent
- pass context into the reasoning pipeline

### Inputs
- user message
- prior history
- stored memories

### Outputs
- a structured conversation context

### Dependencies
- evidence, identity, memory, and prompt composition

### Future evolution
The conversation layer may eventually support richer multi-turn state, but it should remain focused on context assembly.

## 4. Evidence

### Purpose
Track what the system knows, how it knows it, and how current it is.

### Responsibilities
- represent facts as evidence records
- preserve provenance
- manage confidence and freshness
- invalidate dependent belief when dependencies change

### Inputs
- user declarations
- configuration values
- observations
- verification results

### Outputs
- evidence records
- prompt-safe evidence summaries

### Dependencies
- none directly, but used by nearly every subsystem

### Future evolution
This layer will become the backbone of future reasoning, planning, and environment awareness.

## 5. Cognition

### Purpose
Extract structured candidates from conversation.

### Responsibilities
- detect goals, projects, corrections, and configuration statements
- produce candidate facts for downstream subsystems

### Inputs
- conversation content

### Outputs
- cognition candidates

### Dependencies
- evidence engine

### Future evolution
Cognition will become more structured and more explicit about what it believes versus what it merely proposes.

## 6. Identity

### Purpose
Handle user identity and profile facts.

### Responsibilities
- maintain identity traits
- respect explicit declarations over inference
- prevent unsupported age or personal assumptions

### Inputs
- user statements
- stored profile data

### Outputs
- identity state

### Dependencies
- evidence engine

### Future evolution
Identity will grow into a richer and more persistent personal model.

## 7. Memory

### Purpose
Preserve relevant conversational and semantic context.

### Responsibilities
- store and retrieve memories
- help the system remain context-aware

### Inputs
- conversation signals
- extracted facts

### Outputs
- memory context blocks

### Dependencies
- evidence and cognition

### Future evolution
Memory will become more selective and more evidence-aware over time.

## 8. Goals

### Purpose
Represent durable intentions and desired outcomes.

### Responsibilities
- create and update goals
- track progress and status
- separate aspiration from current certainty

### Inputs
- goal candidates
- user updates

### Outputs
- persistent goal state

### Dependencies
- evidence engine

### Future evolution
Goals will later participate in planning and action evaluation.

## 9. Knowledge

### Purpose
Store structured knowledge and relationships.

### Responsibilities
- represent nodes and edges
- preserve domain relationships
- connect facts that belong together

### Inputs
- knowledge candidates
- observed relationships

### Outputs
- knowledge graph state

### Dependencies
- evidence engine

### Future evolution
Knowledge will expand into richer semantic graphs and cross-system dependency views.

## 10. Reflection

### Purpose
Convert observed behavior into reusable signals.

### Responsibilities
- notice corrections and lessons
- produce reflection summaries

### Inputs
- conversation events
- user corrections

### Outputs
- reflection candidates

### Dependencies
- cognition and evidence

### Future evolution
Reflection will become more diagnostic as the system gains more structured awareness.

## 11. Curiosity

### Purpose
Support gentle follow-up behavior when it improves clarity.

### Responsibilities
- offer optional questions
- avoid unnecessary interruptions
- preserve the conversation’s momentum

### Inputs
- current context
- available evidence

### Outputs
- optional curiosity prompt

### Dependencies
- evidence and conversation state

### Future evolution
Curiosity will become more strategic and less conversational over time.

## 12. Prompt Composition

### Purpose
Translate the internal state into an instruction set for the model.

### Responsibilities
- compose prompts from identity, awareness, memory, goals, and evidence
- preserve clarity without overloading the model

### Inputs
- conversation context
- subsystem state
- evidence summaries

### Outputs
- assembled prompt text

### Dependencies
- all prior layers

### Future evolution
Prompt composition will increasingly reflect structured reasoning context rather than long informal context blocks.

## 13. Routing

### Purpose
Choose the most suitable model for the task.

### Responsibilities
- route technical requests to technical models
- route vision requests to vision models
- preserve generalist fallback behavior

### Inputs
- task type
- prompt characteristics

### Outputs
- selected model identity

### Dependencies
- prompt composition

### Future evolution
Routing will become a more explicit planning and capability selection layer.

## 14. Models

### Purpose
Provide the language capabilities that make the system conversational.

### Responsibilities
- generate text
- assist with reasoning and synthesis
- act as a conversational interface

### Inputs
- prompt content

### Outputs
- assistant responses

### Dependencies
- router and prompt composition

### Future evolution
Models will remain the interface layer, while reasoning and planning grow into separate internal systems.
