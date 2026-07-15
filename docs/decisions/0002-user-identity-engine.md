\# ADR 0002 — User Identity Engine



\*\*Status:\*\* Accepted



\*\*Date:\*\* 2026-07-14



\## Context



OMEGA-ARC requires long-term understanding of the user.



Identity and memory are different systems.



Memory records experiences.



Identity records facts.



These responsibilities must remain separate.



\---



\## Decision



Create a dedicated User Identity Engine.



Identity facts are stored independently from preferences.



Each fact contains:



\- value

\- source

\- confidence



Example:



```json

{

&#x20; "age": {

&#x20;   "value": 40,

&#x20;   "source": "explicit\_user\_statement",

&#x20;   "confidence": 1.0

&#x20; }

}

```



Explicit user statements override inferred information.



Unknown facts remain unknown.



Derived values (such as age group) are calculated from authoritative facts rather than stored.



\---



\## Consequences



Benefits:



\- Eliminates contradictory identity.

\- Prevents profile hallucinations.

\- Supports future expansion.

\- Makes prompt generation deterministic.



\---



\## Future Work



Identity Engine v2 will support:



\- Name

\- Pronouns

\- Occupation

\- Projects

\- Interests

\- Long-term knowledge graph

