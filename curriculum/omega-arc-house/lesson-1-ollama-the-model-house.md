# Lesson 1 — Ollama, the Model House

Every language model the runtime speaks through is served by Ollama, running locally at the
address http://127.0.0.1:11434. The runtime talks to Ollama over plain HTTP on that port. All
inference happens on this machine; no conversation is sent to any remote service.

The runtime seats models by role. The voice seat is the active chat model, chosen by the operator
and recorded under Model Lock. The study seat is the model that answers quizzes during tutelage;
by default the study seat follows the active chat model. Memory embeddings are produced by the
embeddinggemma model. A vision model is registered but dormant, and the router model is disabled
under Model Lock.

The active voice is a thinking-capable model, but the runtime disables the hidden thinking phase
deterministically: every chat call is sent with think set to false. This keeps answers direct and
fast, and any leaked reasoning text is stripped before it is shown or graded.

Ollama decides hardware placement by itself. It loads each model onto the video card up to the
available memory, and when a model is larger than the card, the remainder spills to the CPU and
runs slower. Models up to about seven gigabytes run fully on this machine's video card.

Served models are quantized GGUF files. Quantization stores weights in fewer bits so large models
fit small machines; the default voice is stored in the Q4_K_M format, which uses roughly four and
a half bits per weight. Changing which model sits in any seat is an explicit operator action,
recorded under Model Lock — the runtime never substitutes a model silently.
