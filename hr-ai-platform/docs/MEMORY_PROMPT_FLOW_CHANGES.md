# Memory And Prompt Flow Changes

This file explains the backend improvements in simple words.

## Goal

We improved how the HR AI platform:

- remembers ongoing complaint conversations
- decides when it has enough complaint details
- sends cleaner context into prompts
- handles memory save failures

The main purpose was to make the system more stable, safer, and less confusing in multi-turn chats.

## 1. Complaint Thread Memory

### What changed

- We added a `thread_id` for complaint-related conversations.
- This `thread_id` is now stored on:
  - conversations
  - complaints
  - tickets
- When the complaint agent loads old complaint history, it now reads only from the same complaint thread instead of using all old complaints from that user.

### Why this was needed

Before this change, if one employee had multiple complaints over time, the bot could mix them together.

Example:

- old complaint was `critical`
- new complaint was only `medium`
- bot could accidentally carry old severity into the new complaint

That made the system unreliable.

### How it works now

- When chat starts, backend checks whether the user already has an active complaint flow.
- If yes, it reuses the same `thread_id`.
- If not, it creates a new `thread_id`.
- The complaint agent uses that `thread_id` when loading complaint history and past severity.

## 2. Cleaner Prompt Context

### What changed

- We added a helper file: `hr-ai-platform/utils/context.py`
- This helper now:
  - keeps only a few recent turns
  - shortens long messages
  - removes large ticket registration UI text before sending history to the model

### Why this was needed

Before this change, prompts were carrying too much raw history.

That caused problems like:

- bigger token usage
- slower responses
- noisy model behavior
- assistant reading its own long ticket blocks again and again

### How it works now

- The router uses compact history
- The default agent uses compact history
- Leave, payroll, and policy agents also use compact history
- Complaint history is also cleaned before reuse

This gives the model only the useful context, not the clutter.

## 3. Stronger Complaint Completion Rules

### What changed

- The complaint agent no longer depends only on the LLM to decide if intake is complete.
- We added code-based checks for required complaint details.

The system now checks for:

- person's name
- what happened
- when it happened

### Why this was needed

Before this change, the complaint flow could still create a ticket even when important details were missing.

Example:

- bot asked follow-up questions
- exchange count became high
- flow moved toward confirmation
- user replied briefly
- ticket got created even if the target name was still missing

That produced weak ticket summaries and weaker HR handling.

### How it works now

- The system still uses the LLM for help
- But the code now performs a final rule check
- If required details are still missing, it goes back to `GATHERING`
- It does not move forward just because:
  - enough turns happened
  - the user replied after a confirmation prompt

This makes complaint intake more reliable.

## 4. Memory Save Success Tracking

### What changed

- Memory save methods now return `True` or `False`
- This applies to:
  - conversation save
  - complaint save
- Agents now record whether saving worked

### Why this was needed

Before this change, if the database write failed, the app mostly just logged the error and continued.

That was risky because:

- user got a normal reply
- but the conversation may not have been saved
- next turn could forget important context

### How it works now

- Save methods in the memory layer return a success flag
- Agents attach this information into metadata like `memory_persisted`
- Complaint escalation also tracks whether complaint persistence succeeded

This makes failures easier to detect and debug.

## 5. Better Policy Fallback

### What changed

- Policy search no longer returns the entire policy collection when it cannot find a direct keyword match
- It now returns a small fallback set with a note saying the match is weak

### Why this was needed

Before this change, a weak or unclear query could dump too much policy text into the prompt.

That caused:

- larger prompts
- weaker focus
- more chances of confusing answers

### How it works now

- If policy search finds good matches, it returns the best few results
- If not, it returns only a compact fallback set
- The prompt is told to answer carefully when policy match is weak

## 6. Files Updated

Main files changed:

- [hr-ai-platform/api/routes/chat.py](/home/vedp/my-project/IntentBot/hr-ai-platform/api/routes/chat.py)
- [hr-ai-platform/agents/complaint/graph.py](/home/vedp/my-project/IntentBot/hr-ai-platform/agents/complaint/graph.py)
- [hr-ai-platform/agents/complaint/escalation.py](/home/vedp/my-project/IntentBot/hr-ai-platform/agents/complaint/escalation.py)
- [hr-ai-platform/agents/complaint/tools.py](/home/vedp/my-project/IntentBot/hr-ai-platform/agents/complaint/tools.py)
- [hr-ai-platform/orchestrator/router.py](/home/vedp/my-project/IntentBot/hr-ai-platform/orchestrator/router.py)
- [hr-ai-platform/orchestrator/graph.py](/home/vedp/my-project/IntentBot/hr-ai-platform/orchestrator/graph.py)
- [hr-ai-platform/memory/store.py](/home/vedp/my-project/IntentBot/hr-ai-platform/memory/store.py)
- [hr-ai-platform/memory/schemas.py](/home/vedp/my-project/IntentBot/hr-ai-platform/memory/schemas.py)
- [hr-ai-platform/db/models.py](/home/vedp/my-project/IntentBot/hr-ai-platform/db/models.py)
- [hr-ai-platform/app/main.py](/home/vedp/my-project/IntentBot/hr-ai-platform/app/main.py)
- [hr-ai-platform/agents/policy/tools.py](/home/vedp/my-project/IntentBot/hr-ai-platform/agents/policy/tools.py)
- [hr-ai-platform/utils/context.py](/home/vedp/my-project/IntentBot/hr-ai-platform/utils/context.py)

## 7. Final Result

After these changes, the system is better because:

- complaint conversations are separated properly
- prompts are smaller and cleaner
- ticket creation is stricter and safer
- memory failures are more visible
- policy answers are more focused

In simple words:

The bot now remembers the right thing, asks better follow-up questions, and is less likely to create a bad or incomplete complaint ticket.
