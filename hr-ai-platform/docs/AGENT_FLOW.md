# PulseHR AI — Agent Flow Architecture

## 1. High-Level Orchestrator Flow

```mermaid
flowchart TD
    A[👤 User sends message] --> B["POST /api/chat"]
    B --> C[Load last 5 conversations from DB]
    C --> D[Build HRState]
    D --> E["🧠 Router — LLM Intent Classifier"]

    E -->|employee_complaint| F{Agent active?}
    E -->|leave_request| G{Agent active?}
    E -->|payroll_query| H{Agent active?}
    E -->|policy_question| I{Agent active?}
    E -->|general_query| J["💬 Default Agent"]

    F -->|Yes| K["🚨 Complaint Agent"]
    F -->|No| J
    G -->|Yes| L["📅 Leave Agent"]
    G -->|No| J
    H -->|Yes| M["💰 Payroll Agent"]
    H -->|No| J
    I -->|Yes| N["📜 Policy Agent"]
    I -->|No| J

    K --> O[Save to DB]
    L --> O
    M --> O
    N --> O
    J --> O
    O --> P["Return ChatResponse to user"]

    style E fill:#6366f1,color:#fff
    style K fill:#ef4444,color:#fff
    style L fill:#3b82f6,color:#fff
    style M fill:#f59e0b,color:#fff
    style N fill:#10b981,color:#fff
    style J fill:#6b7280,color:#fff
```

---

## 2. Intent Router (LLM Classification)

```mermaid
flowchart LR
    MSG["User Message + Last 5 Conversations"] --> LLM["🧠 LLM\n(Structured Output)"]
    LLM --> CLS["IntentClassification"]
    CLS --> I1["employee_complaint"]
    CLS --> I2["leave_request"]
    CLS --> I3["payroll_query"]
    CLS --> I4["policy_question"]
    CLS --> I5["general_query"]

    style LLM fill:#6366f1,color:#fff
```

> The router includes conversation history so short follow-ups like "yes" / "no"
> during a complaint flow still classify as `employee_complaint`.

---

## 3. Complaint Agent — Multi-Turn Conversational Flow

This is the most complex agent. It asks follow-up questions like a real HR
assistant before creating a ticket.

```mermaid
flowchart TD
    START((Start)) --> CL["🏷️ Classify\ntype · emotion · severity"]
    CL --> SC["🛡️ Safety Check\nimmediate danger?"]
    SC -->|danger detected| SC2["Set severity → CRITICAL"]
    SC -->|no danger| LH
    SC2 --> LH

    LH["📂 Load History\nlast 10 complaint conversations\n+ max historical severity"] --> PC["📋 Policy Check\n(first message only)\nvector search policies"]
    PC --> CC{"✅ Check Completeness\n(LLM decides)"}

    CC -->|GATHERING| FU["❓ Ask Follow-up\nask ONE specific question\nabout missing details"]
    CC -->|CONFIRMING| CF["🤝 Ask Confirmation\nanything else to add?"]
    CC -->|COMPLETE| GS["📝 Generate Summary\nprofessional ticket description"]

    FU --> SM["💾 Save to Memory"]
    CF --> SM
    GS --> WC["💛 Warm Closing\nempathetic closing message"]
    WC --> ESC["⚡ Escalate"]
    ESC --> ER["🎫 Enrich Response\nappend ticket card"]
    ER --> SM
    SM --> END((End))

    style CL fill:#f59e0b,color:#fff
    style SC fill:#ef4444,color:#fff
    style CC fill:#6366f1,color:#fff
    style FU fill:#3b82f6,color:#fff
    style CF fill:#8b5cf6,color:#fff
    style GS fill:#10b981,color:#fff
    style ESC fill:#ef4444,color:#fff
```

### Completeness Decision Logic

```mermaid
flowchart TD
    A["Check Completeness"] --> B{First message?}
    B -->|Yes| C["→ GATHERING\n(always ask follow-up)"]
    B -->|No| D{User confirmed\nafter confirmation prompt?}
    D -->|Yes| E["→ COMPLETE\n(create ticket)"]
    D -->|No| F{Exchange count\n≥ limit?}
    F -->|"Critical/High: ≥ 2\nMedium/Low: ≥ 3"| G["→ CONFIRMING\n(ask to confirm)"]
    F -->|No| H["🧠 LLM Decides\nbased on info checklist"]
    H -->|Enough info| G
    H -->|Need more| C

    style A fill:#6366f1,color:#fff
    style C fill:#3b82f6,color:#fff
    style E fill:#10b981,color:#fff
    style G fill:#8b5cf6,color:#fff
```

### Info Checklist (what the agent gathers)

| #   | Detail                   | Example Question                          |
| --- | ------------------------ | ----------------------------------------- |
| 1   | **What happened**        | "Can you describe what exactly occurred?" |
| 2   | **When it happened**     | "When did this take place — date/time?"   |
| 3   | **Who was involved**     | "Who was the person involved?"            |
| 4   | **Witnesses / evidence** | "Were there any witnesses or evidence?"   |
| 5   | **Impact on employee**   | "How is this affecting your work?"        |

---

## 4. Escalation Rules

```mermaid
flowchart LR
    S["Severity"] --> C["🔴 Critical"]
    S --> H["🟠 High"]
    S --> M["🟡 Medium"]
    S --> L["🟢 Low"]

    C --> A1["📧 Notify HR + Authority\n🎫 Create Ticket"]
    H --> A2["📧 Notify HR\n🎫 Create Ticket"]
    M --> A3["🎫 Create Ticket"]
    L --> A4["📝 Log Only"]

    style C fill:#ef4444,color:#fff
    style H fill:#f97316,color:#fff
    style M fill:#eab308,color:#fff
    style L fill:#22c55e,color:#fff
```

---

## 5. Leave Agent Flow

```mermaid
flowchart LR
    START((Start)) --> PR["📋 Parse Request\nset agent_used"]
    PR --> CB["🔍 Check Balance\nfetch leave balance data"]
    CB --> RS["🧠 LLM Respond\nusing balance data +\nconversation history"]
    RS --> END((End))

    style CB fill:#3b82f6,color:#fff
    style RS fill:#6366f1,color:#fff
```

---

## 6. Payroll Agent Flow

```mermaid
flowchart LR
    START((Start)) --> PQ["📋 Parse Query\nset agent_used"]
    PQ --> FD["🔍 Fetch Data\nfetch salary info"]
    FD --> RS["🧠 LLM Respond\nusing salary data +\nconversation history"]
    RS --> END((End))

    style FD fill:#f59e0b,color:#fff
    style RS fill:#6366f1,color:#fff
```

---

## 7. Policy Agent Flow

```mermaid
flowchart LR
    START((Start)) --> SP["🔍 Search Policies\nvector search over\npolicy documents"]
    SP --> RS["🧠 LLM Respond\ngrounded ONLY in\nretrieved policies"]
    RS --> END((End))

    style SP fill:#10b981,color:#fff
    style RS fill:#6366f1,color:#fff
```

> The policy agent **never makes up rules** — it only cites what's found in the
> actual policy documents.

---

## 8. Default Agent Flow

```mermaid
flowchart TD
    START((Start)) --> CHK{Agent unavailable\nredirect?}
    CHK -->|Yes| UA["Return 'service unavailable'\nmessage naming the service"]
    CHK -->|No| LLM["🧠 LLM Respond\ngreetings · small talk\nmention available services"]
    UA --> END((End))
    LLM --> END

    style CHK fill:#6b7280,color:#fff
    style LLM fill:#6366f1,color:#fff
```

---

## 9. Complete End-to-End Example (Complaint)

```mermaid
sequenceDiagram
    participant U as 👤 Employee
    participant API as 🌐 Chat API
    participant R as 🧠 Router
    participant CA as 🚨 Complaint Agent
    participant DB as 🗄️ Database
    participant HR as 📧 HR Team

    U->>API: "My manager threatened me"
    API->>R: Classify intent
    R-->>API: employee_complaint (0.95)
    API->>CA: Run complaint subgraph

    Note over CA: Classify → Safety → Load History → Policy Check
    Note over CA: Completeness = GATHERING (first message)

    CA-->>API: "That's very serious. When did this happen?"
    API->>DB: Save conversation
    API-->>U: Follow-up question

    U->>API: "Yesterday in the office, around 3 PM"
    API->>R: Classify intent
    R-->>API: employee_complaint (0.92)
    API->>CA: Run complaint subgraph

    Note over CA: Load history → Completeness check
    Note over CA: GATHERING: need who + witnesses

    CA-->>API: "Were there any witnesses present?"
    API->>DB: Save conversation
    API-->>U: Follow-up question

    U->>API: "Yes, two colleagues saw it"
    API->>R: Classify intent
    R-->>API: employee_complaint (0.90)
    API->>CA: Run complaint subgraph

    Note over CA: Exchange count ≥ 2 (critical) → CONFIRMING

    CA-->>API: "Is there anything else to add before I take this forward?"
    API->>DB: Save conversation
    API-->>U: Confirmation prompt

    U->>API: "No, that's all"
    API->>R: Classify intent
    R-->>API: employee_complaint (0.88)
    API->>CA: Run complaint subgraph

    Note over CA: User confirmed → COMPLETE
    Note over CA: Generate summary → Warm closing → Escalate

    CA->>DB: Create ticket (TKT-xxx)
    CA->>HR: 📧 Email notification (critical)
    CA-->>API: Response + ticket card
    API->>DB: Save conversation
    API-->>U: "Your complaint has been registered ✅\nTicket: TKT-xxx | Priority: 🔴 CRITICAL"
```

---

## Architecture Summary

| Component           | Technology                    | Purpose                               |
| ------------------- | ----------------------------- | ------------------------------------- |
| **Orchestrator**    | LangGraph `StateGraph`        | Routes messages to the right agent    |
| **Router**          | LLM + Structured Output       | Intent classification (5 categories)  |
| **Dispatcher**      | Python function               | Agent activation check + routing      |
| **Complaint Agent** | LangGraph subgraph (12 nodes) | Multi-turn HR intake interview        |
| **Leave Agent**     | LangGraph subgraph (3 nodes)  | Leave balance lookup + response       |
| **Payroll Agent**   | LangGraph subgraph (3 nodes)  | Salary data lookup + response         |
| **Policy Agent**    | LangGraph subgraph (2 nodes)  | Vector search + grounded response     |
| **Default Agent**   | Inline LLM call               | Greetings + fallback                  |
| **Memory**          | PostgreSQL                    | Conversation + ticket persistence     |
| **Escalation**      | Rules engine + SMTP           | Ticket creation + email notifications |
