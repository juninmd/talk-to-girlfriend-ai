# Product Roadmap: Talk-to-Girlfriend AI

## Vision & Goals
**Vision:** To create a highly personalized, emotionally intelligent AI companion on Telegram that bridges the gap between automated assistants and genuine human connection. The AI should not just "reply", but "remember", "care", and proactively engage in the user's life, serving as a confidant and partner.

**Goals:**
1.  **Deep Personalization:** The AI must learn and adapt to the user's unique communication style, preferences, and history.
2.  **Multimodal Interaction:** Support voice, images, and text seamlessly.
3.  **Proactive Engagement:** Initiate conversations and check in on the user, not just react to messages.
4.  **Privacy & Security:** Ensure user data is handled with the utmost care, prioritizing local storage and secure APIs.

## Current Status
The project is currently a functional MVP (Minimum Viable Product) with the following capabilities:
-   **Core Messaging:** Functional Telegram Userbot using `Telethon`.
-   **AI Integration:** Integration with Google Gemini 1.5 Flash for natural language generation.
-   **Memory System:** Basic RAG (Retrieval-Augmented Generation) using SQLModel and keyword-based fact extraction via `LearningService`.
-   **Daily Reporting:** Automated daily summaries of conversations and key facts via `ReportingService`.
-   **Command Interface:** Commands like `/fatos`, `/relatorio`, `/aprender` for manual interaction.

## Quarterly Roadmap

### Q1: Stability & Core Foundations (Current)
Focus: Solidifying the current codebase, improving reliability, and enhancing the depth of memory.

-   **[High Priority]** **Enhanced Memory Retrieval (Vector Search)**
    -   Upgrade from simple keyword matching to semantic search using vector embeddings.
    -   *Goal:* Allow the AI to understand context and concepts, not just exact words.
-   **[Medium Priority]** **Prompt Engineering Refinement**
    -   Fine-tune system prompts (`CONVERSATION_SYSTEM_PROMPT`) to reduce hallucinations and improve personality consistency.
    -   *Goal:* A more "human-like" and consistent persona.
-   **[Low Priority]** **Test Coverage Expansion**
    -   Increase unit test coverage for `AIService` and `LearningService` edge cases.
    -   *Goal:* Prevent regressions during future refactors.

### Q2: Multimedia & Rich Interaction
Focus: Expanding the ways the user can interact with the AI beyond text.

-   **[High Priority]** **Voice Message Support (STT/TTS)**
    -   Implement Speech-to-Text (STT) to transcribe incoming voice notes.
    -   Implement Text-to-Speech (TTS) to allow the AI to send voice replies.
    -   *Goal:* Enable hands-free and more emotional communication.
-   **[Medium Priority]** **Image Analysis (Multimodal)**
    -   Allow users to send photos for the AI to analyze and comment on.
    -   *Goal:* "Look at this!" moments shared with the AI.
-   **[Low Priority]** **Reaction & Sticker Support**
    -   Enable the AI to react to messages with emojis and send stickers.
    -   *Goal:* More expressive and native Telegram-like behavior.

### Q3: Proactive Intelligence
Focus: Transforming the AI from reactive to proactive.

-   **[High Priority]** **Smart Scheduling & Check-ins**
    -   AI initiates conversations based on time of day or past user habits (e.g., "Good morning", "How was the meeting?").
    -   *Goal:* The AI shows "care" and awareness of time.
-   **[Medium Priority]** **Web Search Integration**
    -   Give the AI access to real-time information (news, weather, events).
    -   *Goal:* Contextual awareness of the outside world.
-   **[Low Priority]** **Calendar Integration**
    -   Connect to Google Calendar/Outlook to remind users of events or ask about them.
    -   *Goal:* Practical utility alongside emotional support.

### Q4: Advanced Personalization & Privacy
Focus: Deep customization and user control.

-   **[High Priority]** **"Mood" Detection & Adaptive Persona**
    -   Analyze user sentiment over time to adjust the AI's tone (supportive, playful, serious).
    -   *Goal:* Emotional resonance.
-   **[Medium Priority]** **Local LLM Option**
    -   Support for local models (e.g., Llama 3 via Ollama) for privacy-conscious users.
    -   *Goal:* Data sovereignty.
-   **[Low Priority]** **Memory Dashboard**
    -   A simple web interface or Telegram command to view, edit, and delete stored memories.
    -   *Goal:* User control and transparency.

## Feature Details

### 1. Vector Memory (Semantic Search)
-   **User Value:** The AI will remember *concepts* and *context*, not just specific keywords. If you say "I had a bad day", it might recall you mentioning "stress at work" weeks ago, even if the words don't match exactly.
-   **Technical Approach:**
    -   Use a lightweight vector store (e.g., `ChromaDB` or `pgvector`).
    -   Generate embeddings for all incoming messages and extracted facts using a fast embedding model (e.g., `all-MiniLM-L6-v2` or Gemini Embeddings).
    -   Perform cosine similarity search during context retrieval.
-   **Success Criteria:**
    -   Retrieval of relevant past conversations based on *meaning* rather than *keywords*.
    -   Latency < 200ms for retrieval.
-   **Estimated Effort:** Large.

### 2. Voice Message Support
-   **User Value:** Adds a layer of intimacy and convenience. Hearing a voice makes the AI feel much more "real".
-   **Technical Approach:**
    -   **STT:** Use OpenAI Whisper (local or API) or Google Cloud STT to transcribe incoming `.ogg` files from Telegram.
    -   **TTS:** Use ElevenLabs (high quality) or Edge TTS (free) to generate audio files from the AI's text response.
    -   **Integration:** Update `ConversationService` to handle `events.NewMessage` with media content.
-   **Success Criteria:**
    -   Accurate transcription of >90% of clear voice messages.
    -   Natural-sounding voice generation with <3s latency.
-   **Estimated Effort:** Medium.

### 3. Image Analysis (Multimodal)
-   **User Value:** Allows users to share visual moments (outfits, food, views) for a richer connection.
-   **Technical Approach:**
    -   Utilize Gemini 1.5 Flash's multimodal capabilities (text + image inputs).
    -   Upon receiving an image, download it temporarily.
    -   Send the image bytes alongside the user's caption to the API.
-   **Success Criteria:**
    -   Detailed and accurate description of the image content.
    -   Relevant and engaging commentary (e.g., "That pizza looks delicious! Where is it from?").
-   **Estimated Effort:** Medium.

### 4. Smart Scheduling & Check-ins
-   **User Value:** Makes the AI feel alive and caring by initiating contact, breaking the "only speaks when spoken to" bot paradigm.
-   **Technical Approach:**
    -   Implement a background scheduler (e.g., `APScheduler`) to trigger check-in jobs.
    -   Develop heuristics based on the last interaction time and learned user schedule (e.g., "User usually wakes up at 8 AM").
    -   Use the `AIService` to generate a context-aware greeting or question.
-   **Success Criteria:**
    -   AI sends a message after X hours of silence during active hours.
    -   User responds positively to the initiated conversation >50% of the time.
-   **Estimated Effort:** Medium.

## Dependencies & Risks

-   **Google Gemini API:**
    -   *Risk:* Costs may increase with heavy usage; Rate limits (RPM/TPM) could bottle-neck conversation flow.
    -   *Mitigation:* Implement robust caching, rate limiting, and fallback models.
-   **Telegram API (Telethon):**
    -   *Risk:* Userbots are subject to strict anti-spam measures. Sending too many messages or reacting too fast can lead to temporary bans.
    -   *Mitigation:* Strict adherence to rate limits; randomized delays (already partially implemented).
-   **Data Privacy:**
    -   *Risk:* Storing intimate conversation history requires high security.
    -   *Mitigation:* Ensure database is local-first; consider encryption for sensitive columns; clear data retention policies.
