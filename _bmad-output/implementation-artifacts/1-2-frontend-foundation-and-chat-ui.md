# Story 1.2: Frontend Foundation & Chat UI

## Status: backlog

## Story

As a **user**,
I want a clean, dark chat interface where I can type my workflow description,
So that I can start building agents without friction.

## Acceptance Criteria (ACs)

### AC1: Entry Screen Layout
Given the user opens the app,
When the page loads,
Then they see a clean-slate entry screen with:
- Dark background (`#0a0a0a`) filling the full viewport
- "Frankenstein" logo centered, 28px, weight 700, color `#fafafa`
- Tagline "Describe your workflow. Get working AI agents." directly below the logo, 14px, color `#737373` (tertiary)
- A single PromptInput box centered in the viewport, surface-elevated background (`#262626`), with placeholder "Describe the workflow you want to automate..."
- No PipelineSidebar visible
- No other elements competing for attention

### AC2: First Prompt Submission
Given the user types a prompt and hits Enter,
When the message is submitted,
Then:
- The chat message appears as a user variant: transparent background, 48px left indent, 15px text, `#fafafa`
- A TypingIndicator appears immediately below (opacity pulse 0.4 → 1 → 0.4, 1.5s cycle)
- The layout transitions from single-column entry to two-panel grid (`1fr 240px`)
- The PipelineSidebar fades in from the right over 300ms showing all 8 pipeline stages

### AC3: System Message Arrival
Given the system sends a response via WebSocket (`chat.message` type),
When the message payload renders,
Then a system ChatMessage appears:
- Background `#262626` (surface-elevated), full-width within the chat column
- 15px body text, line-height 1.6, color `#fafafa`
- Fade-up entry animation: translates from `translateY(12px)` to `translateY(0)`, opacity 0 → 1, 250ms ease-out
- No left indent

### AC4: Message Spacing Rules
Given consecutive messages are rendered in the chat thread,
When messages of the same sender type appear back-to-back,
Then they have an 8px gap between them.
When messages switch sender type (user → system or system → user),
Then they have a 16px gap between them.
When a phase boundary is crossed,
Then a 32px vertical margin appears above and below a PhaseDivider component.

### AC5: PipelineSidebar Stage States
Given the PipelineSidebar is visible,
When a stage is in `pending` state,
Then it renders a 20px gray dot (`#737373`), stage name at 13px weight 500.
When a stage is `active`,
Then it renders a 20px amber pulsing dot (`#f59e0b` with CSS pulse animation), stage name 13px weight 500, description text at 11px color `#a1a1a1`.
When a stage transitions to `done`,
Then the dot is replaced by a 20px green checkmark icon (`#22c55e`), with a 50ms scale animation from 0.8 → 1.

### AC6: Scroll Behavior & New Message Indicator
Given the user has not scrolled up in the chat thread,
When new messages arrive,
Then the view auto-scrolls to the newest message (smooth, 300ms).
Given the user has scrolled up in the chat history,
When new messages arrive,
Then auto-scroll is suppressed and a "New messages ↓" indicator appears anchored at the bottom of the chat column; clicking it scrolls to bottom and dismisses the indicator.

### AC7: Input Disabled During Autonomous Phases
Given the pipeline is in an autonomous phase (status WebSocket sends `stage_update` for stages: Architecture Design, Security Review, Building, Testing, Learning),
When the input is rendered,
Then the PromptInput textarea is disabled, its placeholder reads "Frankenstein is working...", and the Send button is non-interactive.
Given the pipeline returns to a human checkpoint,
Then the input is re-enabled and the placeholder resets to "Describe the workflow you want to automate..." (or a checkpoint-specific prompt).

### AC8: Responsive Breakpoint
Given the viewport width is below 1024px,
When the layout is rendered,
Then the PipelineSidebar collapses (display: none) and the chat column takes full width.
Given the viewport width is 1024px or above,
Then the two-panel grid (`grid-template-columns: 1fr 240px`) is active.

---

## Technical Implementation Notes

### Architecture

#### Project Initialization (run once before implementing components)

```bash
# From repo root
npm create vite@latest frontend -- --template react-ts
cd frontend

# Core dependencies
npm install

# Tailwind + PostCSS
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p

# shadcn/ui CLI (installs Radix primitives + clsx + tailwind-merge)
npx shadcn-ui@latest init
# When prompted:
#   Style: Default
#   Base color: Neutral
#   CSS variables: Yes

# shadcn components used in this story
npx shadcn-ui@latest add button
npx shadcn-ui@latest add textarea
npx shadcn-ui@latest add toast

# Geist font
npm install geist

# Utility
npm install clsx tailwind-merge lucide-react
```

#### Files to Create (this story)

All paths relative to `frontend/`:

```
frontend/
├── index.html                          # Update: add Geist font meta
├── tailwind.config.ts                  # Full design token config
├── tsconfig.json                       # Strict mode, path aliases
├── vite.config.ts                      # Proxy to backend :8000
└── src/
    ├── index.css                       # Tailwind directives + Geist import
    ├── main.tsx                        # ReactDOM.createRoot
    ├── App.tsx                         # Root layout: entry vs two-panel
    ├── components/
    │   ├── ChatMessage.tsx             # user + system variants
    │   ├── PipelineSidebar.tsx         # Right panel, 240px fixed
    │   ├── StageIndicator.tsx          # Single stage row
    │   ├── PhaseDivider.tsx            # Phase boundary label
    │   ├── TypingIndicator.tsx         # Opacity pulse
    │   ├── PromptInput.tsx             # Fixed bottom input
    │   ├── QuestionGroup.tsx           # STUB ONLY — story 1.3
    │   └── RequirementsCard.tsx        # STUB ONLY — story 1.4
    ├── hooks/
    │   ├── useWebSocket.ts             # Manages both WS connections
    │   └── usePipelineState.ts         # Derived state helpers
    ├── context/
    │   ├── PipelineContext.tsx         # Provider + useContext export
    │   └── pipelineReducer.ts          # Pure reducer, all action types
    ├── types/
    │   ├── messages.ts                 # Mirrors backend messages.py
    │   └── pipeline.ts                 # PipelineStage, StageStatus, etc.
    └── utils/
        └── formatters.ts              # formatTimestamp, cn() helper
```

---

### Tailwind Configuration

Full `tailwind.config.ts` — every design token from the UX spec:

```typescript
import type { Config } from 'tailwindcss'

const config: Config = {
  darkMode: ['class'],
  content: [
    './index.html',
    './src/**/*.{ts,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        // Base surface palette
        background: '#0a0a0a',
        surface: '#171717',
        'surface-elevated': '#262626',
        border: '#2e2e2e',

        // Text
        'text-primary': '#fafafa',
        'text-secondary': '#a1a1a1',
        'text-tertiary': '#737373',

        // Amber accent
        accent: {
          DEFAULT: '#f59e0b',
          hover: '#d97706',
          muted: 'rgba(245, 158, 11, 0.10)',
        },

        // Semantic (contextual only — never decorative)
        critical: 'rgba(239, 68, 68, 0.80)',
        warning: 'rgba(245, 158, 11, 0.80)',
        success: 'rgba(34, 197, 94, 0.80)',
        info: 'rgba(59, 130, 246, 0.60)',
      },

      fontFamily: {
        sans: ['Geist', 'Inter', 'system-ui', 'sans-serif'],
        mono: ['Geist Mono', 'JetBrains Mono', 'monospace'],
      },

      fontSize: {
        // Type scale
        'page-title':  ['24px', { lineHeight: '1.3', letterSpacing: '-0.02em', fontWeight: '600' }],
        'section-heading': ['18px', { lineHeight: '1.4', letterSpacing: '-0.01em', fontWeight: '600' }],
        'chat-body':   ['15px', { lineHeight: '1.6', letterSpacing: '0' }],
        'card-title':  ['14px', { lineHeight: '1.4', letterSpacing: '0', fontWeight: '500' }],
        'body':        ['14px', { lineHeight: '1.6', letterSpacing: '0' }],
        'label':       ['12px', { lineHeight: '1.4', letterSpacing: '0.02em', fontWeight: '500' }],
        'caption':     ['11px', { lineHeight: '1.4', letterSpacing: '0.02em' }],
      },

      spacing: {
        // Design system spacing scale
        'xs': '4px',
        'sm': '8px',
        'md': '16px',
        'lg': '24px',
        'xl': '32px',
        '2xl': '48px',
        '3xl': '64px',
      },

      borderRadius: {
        card: '12px',
        input: '8px',
        badge: '4px',
      },

      maxWidth: {
        'chat': '720px',
        'spec': '840px',
      },

      width: {
        'sidebar': '240px',
      },

      keyframes: {
        // Fade-up entry for chat messages
        'fade-up': {
          '0%':   { opacity: '0', transform: 'translateY(12px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        // Opacity pulse for TypingIndicator
        'opacity-pulse': {
          '0%, 100%': { opacity: '0.4' },
          '50%':      { opacity: '1' },
        },
        // Sidebar slide in from right
        'slide-in-right': {
          '0%':   { opacity: '0', transform: 'translateX(16px)' },
          '100%': { opacity: '1', transform: 'translateX(0)' },
        },
        // Stage completion checkmark pop
        'checkmark-pop': {
          '0%':   { transform: 'scale(0.8)' },
          '100%': { transform: 'scale(1)' },
        },
        // Phase divider fade
        'fade-in': {
          '0%':   { opacity: '0' },
          '100%': { opacity: '1' },
        },
        // Amber dot pulse for active stage
        'dot-pulse': {
          '0%, 100%': { opacity: '1', transform: 'scale(1)' },
          '50%':      { opacity: '0.6', transform: 'scale(0.85)' },
        },
      },

      animation: {
        'fade-up':        'fade-up 250ms ease-out forwards',
        'opacity-pulse':  'opacity-pulse 1.5s ease-in-out infinite',
        'slide-in-right': 'slide-in-right 300ms ease-out forwards',
        'checkmark-pop':  'checkmark-pop 50ms ease-out forwards',
        'fade-in':        'fade-in 400ms ease-out forwards',
        'dot-pulse':      'dot-pulse 1.5s ease-in-out infinite',
      },

      transitionTimingFunction: {
        // No bounce — ever
        'standard': 'ease-out',
        'progress': 'ease-in-out',
      },
    },
  },
  plugins: [require('tailwindcss-animate')],
}

export default config
```

Install the animate plugin: `npm install -D tailwindcss-animate`

---

### index.css

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

/* Geist font import */
@import url('https://fonts.googleapis.com/css2?family=Geist:wght@400;500;600;700&family=Geist+Mono:wght@400;500&display=swap');

/* Alternatively, if using the npm geist package: */
/* @import 'geist/dist/geist.css'; */

@layer base {
  :root {
    --background: #0a0a0a;
    --surface: #171717;
    --surface-elevated: #262626;
    --border: #2e2e2e;
  }

  * {
    box-sizing: border-box;
  }

  html, body, #root {
    height: 100%;
    margin: 0;
    padding: 0;
    background-color: #0a0a0a;
    color: #fafafa;
    font-family: 'Geist', 'Inter', system-ui, sans-serif;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
  }

  /* Reduced motion: disable all animations */
  @media (prefers-reduced-motion: reduce) {
    *, *::before, *::after {
      animation-duration: 0.01ms !important;
      animation-iteration-count: 1 !important;
      transition-duration: 0.01ms !important;
    }
  }

  /* Focus indicator: 2px amber outline (WCAG AA) */
  :focus-visible {
    outline: 2px solid #f59e0b;
    outline-offset: 2px;
  }

  /* Scrollbar — minimal dark */
  ::-webkit-scrollbar { width: 6px; }
  ::-webkit-scrollbar-track { background: #0a0a0a; }
  ::-webkit-scrollbar-thumb { background: #2e2e2e; border-radius: 3px; }
  ::-webkit-scrollbar-thumb:hover { background: #404040; }
}
```

---

### vite.config.ts

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
    proxy: {
      // REST endpoints
      '/sessions': 'http://localhost:8000',
      '/sessions/': 'http://localhost:8000',
      // WebSocket endpoints — vite proxy handles WS upgrades
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true,
      },
    },
  },
})
```

---

### TypeScript Types

#### `src/types/messages.ts`

Mirrors `backend/app/models/messages.py` exactly. Any change to backend types must be reflected here.

```typescript
// WebSocket message envelope — all WS messages follow this shape
export interface WSMessage<T = unknown> {
  type: MessageType
  payload: T
  timestamp: string   // ISO 8601 UTC
  session_id: string
}

// All valid dot-notation message type strings
export type MessageType =
  | 'chat.message'
  | 'chat.question_group'
  | 'chat.checkpoint'
  | 'status.stage_update'
  | 'status.progress'
  | 'status.complete'
  | 'error.llm_failure'
  | 'error.pipeline_failure'
  | 'control.approve'
  | 'control.reject'
  | 'control.user_input'

// Payloads per message type

export interface ChatMessagePayload {
  content: string
  sender: 'system' | 'user'
  phase?: PipelinePhase   // optional — triggers PhaseDivider if set
}

export interface QuestionGroupPayload {
  category: string
  questions: string[]
  round: number           // 1-3
}

export interface CheckpointPayload {
  checkpoint_id: string   // 'checkpoint_1' | 'checkpoint_2'
  title: string
  content: Record<string, unknown>   // RequirementsDoc or AgentSpec
}

export interface StageUpdatePayload {
  stage: PipelineStageName
  status: StageStatus
  description?: string    // shown under stage name when active
}

export interface ProgressPayload {
  stage: PipelineStageName
  percent: number         // 0-100
  message: string         // user-friendly plain language
}

export interface CompletePayload {
  success: boolean
  partial: boolean        // true = partial success (amber variant)
  summary: BuildSummary
}

export interface ErrorPayload {
  stage: PipelineStageName | 'unknown'
  message: string         // user-friendly, never raw error
  recoverable: boolean
}

export interface ControlPayload {
  checkpoint_id?: string
  content?: string        // for user_input
}

// Supporting types

export type PipelineStageName =
  | 'elicitor'
  | 'checkpoint_1'
  | 'architect'
  | 'critic'
  | 'checkpoint_2'
  | 'builder'
  | 'tester'
  | 'learner'

export type PipelinePhase =
  | 'understanding'
  | 'requirements_summary'
  | 'blueprint'
  | 'building'
  | 'delivery'

export type StageStatus = 'pending' | 'active' | 'done' | 'error'

export interface BuildSummary {
  agent_count: number
  framework: 'crewai' | 'langgraph'
  tests_passed: number
  tests_total: number
  build_time_seconds: number
  files: string[]
}
```

#### `src/types/pipeline.ts`

```typescript
import type { PipelineStageName, StageStatus, PipelinePhase } from './messages'

export interface PipelineStage {
  id: PipelineStageName
  label: string           // Display label in sidebar
  description: string     // Shown when active (plain language)
  phase: PipelinePhase    // Which phase this stage belongs to
  status: StageStatus
}

// The 8 stages in sidebar order
export const PIPELINE_STAGES: PipelineStage[] = [
  {
    id: 'elicitor',
    label: 'Understanding',
    description: 'Analyzing your workflow and asking clarifying questions...',
    phase: 'understanding',
    status: 'pending',
  },
  {
    id: 'checkpoint_1',
    label: 'Requirements Review',
    description: 'Waiting for your approval on the requirements summary...',
    phase: 'requirements_summary',
    status: 'pending',
  },
  {
    id: 'architect',
    label: 'Architecture Design',
    description: 'Designing your agent architecture...',
    phase: 'blueprint',
    status: 'pending',
  },
  {
    id: 'critic',
    label: 'Security Review',
    description: 'Stress-testing the architecture for compatibility issues...',
    phase: 'blueprint',
    status: 'pending',
  },
  {
    id: 'checkpoint_2',
    label: 'Blueprint Review',
    description: 'Waiting for your approval on the agent blueprint...',
    phase: 'blueprint',
    status: 'pending',
  },
  {
    id: 'builder',
    label: 'Building',
    description: 'Compiling your agent architecture into working code...',
    phase: 'building',
    status: 'pending',
  },
  {
    id: 'tester',
    label: 'Testing',
    description: 'Running your agents against test cases...',
    phase: 'building',
    status: 'pending',
  },
  {
    id: 'learner',
    label: 'Learning',
    description: 'Storing patterns to improve future builds...',
    phase: 'delivery',
    status: 'pending',
  },
]

// Phases that disable user input
export const AUTONOMOUS_STAGES: PipelineStageName[] = [
  'architect',
  'critic',
  'builder',
  'tester',
  'learner',
]

// Phase display labels (for PhaseDivider)
export const PHASE_LABELS: Record<PipelinePhase, string> = {
  understanding: 'Understanding your needs',
  requirements_summary: 'Requirements Summary',
  blueprint: 'Your Blueprint',
  building: 'Building',
  delivery: 'Delivery',
}
```

---

### State Management

#### `src/context/pipelineReducer.ts`

The reducer is **pure** — zero side effects. All WebSocket events dispatch into this.

```typescript
import type { WSMessage, ChatMessagePayload, StageUpdatePayload, CompletePayload, ErrorPayload } from '@/types/messages'
import type { PipelineStage } from '@/types/pipeline'
import { PIPELINE_STAGES } from '@/types/pipeline'

// ---- Chat thread entry types ----

export interface ChatEntry {
  id: string
  kind: 'user_message' | 'system_message' | 'typing_indicator' | 'phase_divider'
  payload: ChatMessagePayload | { phase: string; label: string } | null
  timestamp: string
}

// ---- State shape ----

export interface PipelineState {
  sessionId: string | null
  hasStarted: boolean           // true after first user prompt submitted
  chatEntries: ChatEntry[]
  stages: PipelineStage[]
  isTyping: boolean
  isInputDisabled: boolean
  isComplete: boolean
  hasError: boolean
  lastErrorMessage: string | null
  userScrolledUp: boolean       // suppress auto-scroll when true
  hasNewMessages: boolean       // show "New messages ↓" indicator
}

export const initialState: PipelineState = {
  sessionId: null,
  hasStarted: false,
  chatEntries: [],
  stages: PIPELINE_STAGES,
  isTyping: false,
  isInputDisabled: false,
  isComplete: false,
  hasError: false,
  lastErrorMessage: null,
  userScrolledUp: false,
  hasNewMessages: false,
}

// ---- Action types ----

export type PipelineAction =
  | { type: 'SESSION_INIT'; sessionId: string }
  | { type: 'USER_MESSAGE_SENT'; content: string; timestamp: string }
  | { type: 'CHAT_MESSAGE'; message: WSMessage<ChatMessagePayload> }
  | { type: 'STAGE_UPDATE'; message: WSMessage<StageUpdatePayload> }
  | { type: 'TYPING_START' }
  | { type: 'TYPING_STOP' }
  | { type: 'COMPLETE'; message: WSMessage<CompletePayload> }
  | { type: 'ERROR'; message: WSMessage<ErrorPayload> }
  | { type: 'USER_SCROLLED_UP' }
  | { type: 'USER_SCROLLED_TO_BOTTOM' }
  | { type: 'NEW_MESSAGES_DISMISSED' }

// ---- Helpers ----

function makeId(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`
}

function isAutonomousStage(stageName: string): boolean {
  return ['architect', 'critic', 'builder', 'tester', 'learner'].includes(stageName)
}

// ---- Reducer ----

export function pipelineReducer(state: PipelineState, action: PipelineAction): PipelineState {
  switch (action.type) {

    case 'SESSION_INIT':
      return { ...state, sessionId: action.sessionId }

    case 'USER_MESSAGE_SENT': {
      const entry: ChatEntry = {
        id: makeId(),
        kind: 'user_message',
        payload: { content: action.content, sender: 'user' },
        timestamp: action.timestamp,
      }
      return {
        ...state,
        hasStarted: true,
        chatEntries: [...state.chatEntries, entry],
        isTyping: true,
      }
    }

    case 'CHAT_MESSAGE': {
      const { payload } = action.message
      const entries: ChatEntry[] = []

      // Insert a PhaseDivider when a phase is explicitly signaled
      if (payload.phase) {
        entries.push({
          id: makeId(),
          kind: 'phase_divider',
          payload: { phase: payload.phase, label: '' }, // label resolved in component via PHASE_LABELS
          timestamp: action.message.timestamp,
        })
      }

      entries.push({
        id: makeId(),
        kind: 'system_message',
        payload,
        timestamp: action.message.timestamp,
      })

      return {
        ...state,
        chatEntries: [...state.chatEntries, ...entries],
        isTyping: false,
        // Notify of new messages only when user has scrolled up
        hasNewMessages: state.userScrolledUp ? true : state.hasNewMessages,
      }
    }

    case 'STAGE_UPDATE': {
      const { stage, status } = action.message.payload
      const updatedStages = state.stages.map((s) =>
        s.id === stage ? { ...s, status } : s
      )
      const inputDisabled = status === 'active' && isAutonomousStage(stage)
      return {
        ...state,
        stages: updatedStages,
        isInputDisabled: inputDisabled,
      }
    }

    case 'TYPING_START':
      return { ...state, isTyping: true }

    case 'TYPING_STOP':
      return { ...state, isTyping: false }

    case 'COMPLETE':
      return {
        ...state,
        isComplete: true,
        isTyping: false,
        isInputDisabled: false,
      }

    case 'ERROR':
      return {
        ...state,
        hasError: true,
        isTyping: false,
        isInputDisabled: false,
        lastErrorMessage: action.message.payload.message,
      }

    case 'USER_SCROLLED_UP':
      return { ...state, userScrolledUp: true }

    case 'USER_SCROLLED_TO_BOTTOM':
      return { ...state, userScrolledUp: false, hasNewMessages: false }

    case 'NEW_MESSAGES_DISMISSED':
      return { ...state, userScrolledUp: false, hasNewMessages: false }

    default:
      return state
  }
}
```

#### `src/context/PipelineContext.tsx`

```typescript
import React, { createContext, useContext, useReducer, type ReactNode } from 'react'
import { pipelineReducer, initialState } from './pipelineReducer'
import type { PipelineState, PipelineAction } from './pipelineReducer'

interface PipelineContextValue {
  state: PipelineState
  dispatch: React.Dispatch<PipelineAction>
}

const PipelineContext = createContext<PipelineContextValue | null>(null)

export function PipelineProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(pipelineReducer, initialState)
  return (
    <PipelineContext.Provider value={{ state, dispatch }}>
      {children}
    </PipelineContext.Provider>
  )
}

export function usePipeline(): PipelineContextValue {
  const ctx = useContext(PipelineContext)
  if (!ctx) throw new Error('usePipeline must be used inside PipelineProvider')
  return ctx
}
```

---

### WebSocket Integration

#### `src/hooks/useWebSocket.ts`

Manages both WebSocket connections. Dispatches typed actions into the reducer. Auto-reconnects on disconnect.

```typescript
import { useEffect, useRef, useCallback } from 'react'
import { usePipeline } from '@/context/PipelineContext'
import type { WSMessage, ChatMessagePayload, StageUpdatePayload, CompletePayload, ErrorPayload } from '@/types/messages'

const BACKEND_WS_BASE = 'ws://localhost:8000'
const RECONNECT_DELAY_MS = 2000

export function useWebSocket(sessionId: string | null) {
  const { dispatch } = usePipeline()
  const chatWsRef = useRef<WebSocket | null>(null)
  const statusWsRef = useRef<WebSocket | null>(null)
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const mountedRef = useRef(true)

  // ---- Message router for chat WS ----
  const handleChatMessage = useCallback((raw: MessageEvent) => {
    try {
      const msg: WSMessage = JSON.parse(raw.data as string)
      switch (msg.type) {
        case 'chat.message':
          dispatch({ type: 'CHAT_MESSAGE', message: msg as WSMessage<ChatMessagePayload> })
          break
        case 'chat.question_group':
          // story 1.3 handles this — dispatch generic for now
          dispatch({ type: 'CHAT_MESSAGE', message: { ...msg, payload: { content: '', sender: 'system' } } as WSMessage<ChatMessagePayload> })
          break
        case 'chat.checkpoint':
          dispatch({ type: 'TYPING_STOP' })
          break
        case 'error.llm_failure':
        case 'error.pipeline_failure':
          dispatch({ type: 'ERROR', message: msg as WSMessage<ErrorPayload> })
          break
        default:
          break
      }
    } catch {
      console.error('[useWebSocket] Failed to parse chat message')
    }
  }, [dispatch])

  // ---- Message router for status WS ----
  const handleStatusMessage = useCallback((raw: MessageEvent) => {
    try {
      const msg: WSMessage = JSON.parse(raw.data as string)
      switch (msg.type) {
        case 'status.stage_update':
          dispatch({ type: 'STAGE_UPDATE', message: msg as WSMessage<StageUpdatePayload> })
          break
        case 'status.complete':
          dispatch({ type: 'COMPLETE', message: msg as WSMessage<CompletePayload> })
          break
        case 'error.pipeline_failure':
          dispatch({ type: 'ERROR', message: msg as WSMessage<ErrorPayload> })
          break
        default:
          break
      }
    } catch {
      console.error('[useWebSocket] Failed to parse status message')
    }
  }, [dispatch])

  // ---- Connection factory with auto-reconnect ----
  const connectChat = useCallback(() => {
    if (!sessionId || !mountedRef.current) return
    const ws = new WebSocket(`${BACKEND_WS_BASE}/ws/chat/${sessionId}`)
    chatWsRef.current = ws

    ws.onopen = () => {
      console.debug('[WS:chat] connected')
    }
    ws.onmessage = handleChatMessage
    ws.onclose = () => {
      if (!mountedRef.current) return
      console.debug('[WS:chat] disconnected — reconnecting in', RECONNECT_DELAY_MS, 'ms')
      reconnectTimerRef.current = setTimeout(connectChat, RECONNECT_DELAY_MS)
    }
    ws.onerror = (e) => {
      console.error('[WS:chat] error', e)
      ws.close()
    }
  }, [sessionId, handleChatMessage])

  const connectStatus = useCallback(() => {
    if (!sessionId || !mountedRef.current) return
    const ws = new WebSocket(`${BACKEND_WS_BASE}/ws/status/${sessionId}`)
    statusWsRef.current = ws

    ws.onopen = () => {
      console.debug('[WS:status] connected')
    }
    ws.onmessage = handleStatusMessage
    ws.onclose = () => {
      if (!mountedRef.current) return
      console.debug('[WS:status] disconnected — reconnecting in', RECONNECT_DELAY_MS, 'ms')
      setTimeout(connectStatus, RECONNECT_DELAY_MS)
    }
    ws.onerror = (e) => {
      console.error('[WS:status] error', e)
      ws.close()
    }
  }, [sessionId, handleStatusMessage])

  // ---- Connect on sessionId available ----
  useEffect(() => {
    if (!sessionId) return
    connectChat()
    connectStatus()

    return () => {
      mountedRef.current = false
      if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current)
      chatWsRef.current?.close()
      statusWsRef.current?.close()
    }
  }, [sessionId, connectChat, connectStatus])

  // ---- Send helpers ----
  const sendUserInput = useCallback((content: string) => {
    if (chatWsRef.current?.readyState !== WebSocket.OPEN) {
      console.warn('[useWebSocket] Chat WS not open — message dropped')
      return
    }
    const msg: WSMessage = {
      type: 'control.user_input',
      payload: { content },
      timestamp: new Date().toISOString(),
      session_id: sessionId ?? '',
    }
    chatWsRef.current.send(JSON.stringify(msg))
  }, [sessionId])

  const sendApproval = useCallback((checkpointId: string, approved: boolean) => {
    if (chatWsRef.current?.readyState !== WebSocket.OPEN) return
    const msg: WSMessage = {
      type: approved ? 'control.approve' : 'control.reject',
      payload: { checkpoint_id: checkpointId },
      timestamp: new Date().toISOString(),
      session_id: sessionId ?? '',
    }
    chatWsRef.current.send(JSON.stringify(msg))
  }, [sessionId])

  return { sendUserInput, sendApproval }
}
```

#### `src/hooks/usePipelineState.ts`

Derived state helpers — keeps components lean.

```typescript
import { usePipeline } from '@/context/PipelineContext'
import { AUTONOMOUS_STAGES } from '@/types/pipeline'
import type { PipelineStage } from '@/types/pipeline'

export function usePipelineState() {
  const { state } = usePipeline()

  const activeStage: PipelineStage | undefined = state.stages.find(
    (s) => s.status === 'active'
  )

  const isInAutonomousPhase: boolean =
    activeStage !== undefined && AUTONOMOUS_STAGES.includes(activeStage.id)

  const completedCount: number = state.stages.filter((s) => s.status === 'done').length

  return {
    activeStage,
    isInAutonomousPhase,
    completedCount,
    stages: state.stages,
    hasStarted: state.hasStarted,
    isTyping: state.isTyping,
    chatEntries: state.chatEntries,
    sessionId: state.sessionId,
    isInputDisabled: state.isInputDisabled || isInAutonomousPhase,
    isComplete: state.isComplete,
    userScrolledUp: state.userScrolledUp,
    hasNewMessages: state.hasNewMessages,
  }
}
```

---

### Components

#### `src/components/ChatMessage.tsx`

```typescript
import React from 'react'
import { cn } from '@/utils/formatters'
import type { ChatMessagePayload } from '@/types/messages'

interface ChatMessageProps {
  payload: ChatMessagePayload
  className?: string
}

export function ChatMessage({ payload, className }: ChatMessageProps) {
  const isUser = payload.sender === 'user'

  return (
    <div
      className={cn(
        // Shared
        'animate-fade-up w-full rounded-card px-4 py-3',
        // User variant: transparent bg, 48px left indent
        isUser && 'bg-transparent pl-[48px] text-text-primary',
        // System variant: surface-elevated bg, full-width
        !isUser && 'bg-surface-elevated text-text-primary',
        className
      )}
    >
      <p className="text-chat-body whitespace-pre-wrap break-words leading-relaxed">
        {payload.content}
      </p>
    </div>
  )
}
```

Spacing between messages is controlled by the parent chat thread container using gap or margin, not inside ChatMessage itself. The parent applies 8px gap for same-type consecutive, 16px for type switches (tracked via the `chatEntries` array — compare adjacent `kind` values).

---

#### `src/components/TypingIndicator.tsx`

```typescript
import React from 'react'

export function TypingIndicator() {
  return (
    <div className="flex items-center gap-[5px] px-4 py-3">
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          className="block h-[6px] w-[6px] rounded-full bg-text-secondary animate-opacity-pulse"
          style={{
            animationDelay: `${i * 0.18}s`,
          }}
        />
      ))}
    </div>
  )
}
```

Note: The opacity-pulse keyframe (0.4 → 1 → 0.4) is used per spec. The staggered `animationDelay` creates a subtle sequential feel without using bounce easing. The three dots each pulse on the same cycle with offsets — this is NOT the bouncing-dot pattern the spec prohibits (no translateY involved).

---

#### `src/components/PhaseDivider.tsx`

```typescript
import React from 'react'
import { cn } from '@/utils/formatters'
import { PHASE_LABELS } from '@/types/pipeline'
import type { PipelinePhase } from '@/types/messages'

interface PhaseDividerProps {
  phase: PipelinePhase
  className?: string
}

export function PhaseDivider({ phase, className }: PhaseDividerProps) {
  const label = PHASE_LABELS[phase] ?? phase

  return (
    <div
      className={cn(
        'animate-fade-in my-xl flex items-center gap-3',
        className
      )}
    >
      {/* Left line */}
      <div className="flex-1 h-px bg-border" />

      {/* Centered label */}
      <span
        className="text-caption text-text-tertiary uppercase"
        style={{ letterSpacing: '0.05em' }}
      >
        {label}
      </span>

      {/* Right line */}
      <div className="flex-1 h-px bg-border" />
    </div>
  )
}
```

---

#### `src/components/StageIndicator.tsx`

```typescript
import React from 'react'
import { Check } from 'lucide-react'
import { cn } from '@/utils/formatters'
import type { PipelineStage } from '@/types/pipeline'

interface StageIndicatorProps {
  stage: PipelineStage
  isLast?: boolean
}

export function StageIndicator({ stage, isLast }: StageIndicatorProps) {
  const { status, label, description } = stage

  return (
    <div className="flex items-start gap-3">
      {/* Left column: dot + connecting line */}
      <div className="flex flex-col items-center">
        {/* Status dot / checkmark */}
        <div className="flex-shrink-0 w-5 h-5 flex items-center justify-center">
          {status === 'done' ? (
            <span className="animate-checkmark-pop flex items-center justify-center w-5 h-5 rounded-full bg-success">
              <Check className="w-3 h-3 text-background" strokeWidth={3} />
            </span>
          ) : status === 'active' ? (
            <span className="block w-[10px] h-[10px] rounded-full bg-accent animate-dot-pulse" />
          ) : (
            /* pending / error */
            <span
              className={cn(
                'block w-[10px] h-[10px] rounded-full',
                status === 'error' ? 'bg-critical' : 'bg-text-tertiary'
              )}
            />
          )}
        </div>

        {/* Connecting vertical line — hidden for last item */}
        {!isLast && (
          <div className="w-px flex-1 min-h-[16px] mt-1 bg-border" />
        )}
      </div>

      {/* Right column: text */}
      <div className="pb-4 min-w-0">
        <p
          className={cn(
            'text-[13px] font-medium leading-none',
            status === 'active' ? 'text-text-primary' : 'text-text-secondary'
          )}
        >
          {label}
        </p>
        {status === 'active' && description && (
          <p className="text-caption text-text-tertiary mt-1 leading-snug">
            {description}
          </p>
        )}
      </div>
    </div>
  )
}
```

---

#### `src/components/PipelineSidebar.tsx`

```typescript
import React from 'react'
import { cn } from '@/utils/formatters'
import { StageIndicator } from './StageIndicator'
import type { PipelineStage } from '@/types/pipeline'

interface PipelineSidebarProps {
  stages: PipelineStage[]
  visible: boolean
  className?: string
}

export function PipelineSidebar({ stages, visible, className }: PipelineSidebarProps) {
  if (!visible) return null

  return (
    <aside
      className={cn(
        // Fixed width, full height, left border
        'w-sidebar h-full border-l border-border bg-background overflow-y-auto',
        // Slide in from right on first render
        'animate-slide-in-right',
        className
      )}
      aria-label="Pipeline progress"
    >
      <div className="px-4 pt-5 pb-4">
        {/* Sidebar title */}
        <p
          className="text-caption text-text-tertiary uppercase mb-5"
          style={{ letterSpacing: '0.08em' }}
        >
          Pipeline
        </p>

        {/* Stage list */}
        <div>
          {stages.map((stage, idx) => (
            <StageIndicator
              key={stage.id}
              stage={stage}
              isLast={idx === stages.length - 1}
            />
          ))}
        </div>
      </div>
    </aside>
  )
}
```

---

#### `src/components/PromptInput.tsx`

```typescript
import React, { useRef, useCallback, type KeyboardEvent } from 'react'
import { Send } from 'lucide-react'
import { cn } from '@/utils/formatters'

interface PromptInputProps {
  onSubmit: (value: string) => void
  disabled?: boolean
  placeholder?: string
  className?: string
}

const DEFAULT_PLACEHOLDER = 'Describe the workflow you want to automate...'
const DISABLED_PLACEHOLDER = 'Frankenstein is working...'

export function PromptInput({
  onSubmit,
  disabled = false,
  placeholder,
  className,
}: PromptInputProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const resolvedPlaceholder = disabled
    ? DISABLED_PLACEHOLDER
    : (placeholder ?? DEFAULT_PLACEHOLDER)

  const handleSubmit = useCallback(() => {
    const value = textareaRef.current?.value.trim()
    if (!value || disabled) return
    onSubmit(value)
    if (textareaRef.current) {
      textareaRef.current.value = ''
      // Reset height
      textareaRef.current.style.height = 'auto'
    }
  }, [onSubmit, disabled])

  const handleKeyDown = useCallback((e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
    // Shift+Enter: default behavior (newline) — no preventDefault
  }, [handleSubmit])

  // Auto-resize textarea up to 5 lines
  const handleInput = useCallback(() => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    const lineHeight = 24
    const maxLines = 5
    const maxHeight = lineHeight * maxLines + 32 // 32 = top+bottom padding
    el.style.height = `${Math.min(el.scrollHeight, maxHeight)}px`
  }, [])

  return (
    <div
      className={cn(
        'flex items-end gap-3 bg-surface-elevated border border-border rounded-card p-3',
        disabled && 'opacity-60 cursor-not-allowed',
        className
      )}
    >
      <textarea
        ref={textareaRef}
        rows={1}
        disabled={disabled}
        placeholder={resolvedPlaceholder}
        onKeyDown={handleKeyDown}
        onInput={handleInput}
        className={cn(
          'flex-1 bg-transparent text-chat-body text-text-primary placeholder:text-text-tertiary',
          'resize-none outline-none border-none leading-relaxed',
          'min-h-[44px]',  // 44px min for WCAG touch target
          disabled && 'cursor-not-allowed'
        )}
        aria-label="Describe your workflow"
        aria-disabled={disabled}
      />

      {/* Send button — minimum 44px touch target */}
      <button
        type="button"
        onClick={handleSubmit}
        disabled={disabled}
        className={cn(
          'flex-shrink-0 flex items-center justify-center w-[44px] h-[44px] rounded-input',
          'bg-accent text-background transition-transform',
          'hover:bg-accent-hover active:scale-[0.97]',
          'disabled:opacity-50 disabled:cursor-not-allowed disabled:active:scale-100',
          'focus-visible:outline-2 focus-visible:outline-accent'
        )}
        aria-label="Send message"
      >
        <Send className="w-4 h-4" strokeWidth={2.5} />
      </button>
    </div>
  )
}
```

---

#### `src/components/QuestionGroup.tsx` (stub — story 1.3)

```typescript
import React from 'react'
// Full implementation in Story 1.3
// Placeholder to prevent import errors in story 1.2

interface QuestionGroupProps {
  category: string
  questions: string[]
  round: number
}

export function QuestionGroup(_props: QuestionGroupProps) {
  return (
    <div className="bg-surface-elevated rounded-card p-4 text-text-secondary text-body">
      [QuestionGroup — implemented in Story 1.3]
    </div>
  )
}
```

#### `src/components/RequirementsCard.tsx` (stub — story 1.4)

```typescript
import React from 'react'
// Full implementation in Story 1.4

export function RequirementsCard() {
  return (
    <div className="bg-surface-elevated rounded-card p-4 text-text-secondary text-body">
      [RequirementsCard — implemented in Story 1.4]
    </div>
  )
}
```

---

#### `src/App.tsx`

Root layout. Manages the entry → two-panel transition. Owns session creation.

```typescript
import React, { useEffect, useCallback } from 'react'
import { usePipeline } from '@/context/PipelineContext'
import { usePipelineState } from '@/hooks/usePipelineState'
import { useWebSocket } from '@/hooks/useWebSocket'
import { ChatMessage } from '@/components/ChatMessage'
import { PhaseDivider } from '@/components/PhaseDivider'
import { TypingIndicator } from '@/components/TypingIndicator'
import { PipelineSidebar } from '@/components/PipelineSidebar'
import { PromptInput } from '@/components/PromptInput'
import { cn } from '@/utils/formatters'
import type { ChatMessagePayload, PipelinePhase } from '@/types/messages'

export default function App() {
  const { dispatch } = usePipeline()
  const {
    hasStarted,
    chatEntries,
    stages,
    isTyping,
    isInputDisabled,
    sessionId,
    userScrolledUp,
    hasNewMessages,
  } = usePipelineState()

  const { sendUserInput } = useWebSocket(sessionId)

  const chatEndRef = React.useRef<HTMLDivElement>(null)
  const chatScrollRef = React.useRef<HTMLDivElement>(null)

  // ---- Session creation on mount ----
  useEffect(() => {
    async function initSession() {
      try {
        const res = await fetch('/sessions', { method: 'POST' })
        const data = await res.json() as { session_id: string }
        dispatch({ type: 'SESSION_INIT', sessionId: data.session_id })
      } catch {
        console.error('Failed to create session')
      }
    }
    initSession()
  }, [dispatch])

  // ---- Auto-scroll behavior ----
  useEffect(() => {
    if (!userScrolledUp && chatEndRef.current) {
      chatEndRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [chatEntries, isTyping, userScrolledUp])

  // ---- Scroll tracking ----
  const handleScroll = useCallback(() => {
    const el = chatScrollRef.current
    if (!el) return
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 40
    if (atBottom) {
      dispatch({ type: 'USER_SCROLLED_TO_BOTTOM' })
    } else {
      dispatch({ type: 'USER_SCROLLED_UP' })
    }
  }, [dispatch])

  // ---- Submit handler ----
  const handlePromptSubmit = useCallback((value: string) => {
    dispatch({
      type: 'USER_MESSAGE_SENT',
      content: value,
      timestamp: new Date().toISOString(),
    })
    sendUserInput(value)
  }, [dispatch, sendUserInput])

  // ---- Chat entry gap calculation ----
  // Returns margin-top class based on adjacency to previous entry
  function gapClass(idx: number): string {
    if (idx === 0) return ''
    const prev = chatEntries[idx - 1]
    const curr = chatEntries[idx]
    if (prev.kind === 'phase_divider' || curr.kind === 'phase_divider') return ''
    if (prev.kind === curr.kind) return 'mt-[8px]'
    return 'mt-[16px]'
  }

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-background">

      {/* ---- Entry screen (before first prompt) ---- */}
      {!hasStarted && (
        <div className="flex flex-col items-center justify-center w-full gap-3 px-4">
          {/* Logo */}
          <h1
            className="text-[28px] font-bold text-text-primary tracking-tight"
            style={{ letterSpacing: '-0.02em' }}
          >
            Frankenstein
          </h1>

          {/* Tagline */}
          <p className="text-body text-text-tertiary text-center max-w-[360px]">
            Describe your workflow. Get working AI agents.
          </p>

          {/* Centered prompt input */}
          <div className="w-full max-w-chat mt-4">
            <PromptInput onSubmit={handlePromptSubmit} />
          </div>
        </div>
      )}

      {/* ---- Two-panel layout (after first prompt) ---- */}
      {hasStarted && (
        <div
          className={cn(
            'flex flex-1 overflow-hidden',
            // Desktop: grid with sidebar. Below 1024px: single column
            'lg:grid lg:grid-cols-[1fr_240px]'
          )}
        >
          {/* ---- Chat column ---- */}
          <div className="flex flex-col h-full overflow-hidden">
            {/* Scrollable thread */}
            <div
              ref={chatScrollRef}
              onScroll={handleScroll}
              className="flex-1 overflow-y-auto px-4 py-6"
            >
              <div className="max-w-chat mx-auto flex flex-col">
                {chatEntries.map((entry, idx) => {
                  if (entry.kind === 'phase_divider') {
                    const p = entry.payload as { phase: PipelinePhase; label: string }
                    return (
                      <PhaseDivider key={entry.id} phase={p.phase} />
                    )
                  }

                  if (entry.kind === 'user_message' || entry.kind === 'system_message') {
                    const payload = entry.payload as ChatMessagePayload
                    return (
                      <ChatMessage
                        key={entry.id}
                        payload={payload}
                        className={gapClass(idx)}
                      />
                    )
                  }

                  return null
                })}

                {/* Typing indicator */}
                {isTyping && (
                  <div className="mt-[8px]">
                    <TypingIndicator />
                  </div>
                )}

                {/* Scroll anchor */}
                <div ref={chatEndRef} />
              </div>
            </div>

            {/* "New messages" indicator */}
            {hasNewMessages && (
              <button
                onClick={() => dispatch({ type: 'NEW_MESSAGES_DISMISSED' })}
                className={cn(
                  'mx-auto mb-2 px-4 py-1.5 rounded-full text-caption font-medium',
                  'bg-surface-elevated border border-border text-text-secondary',
                  'hover:text-text-primary transition-colors'
                )}
              >
                New messages ↓
              </button>
            )}

            {/* Prompt input — fixed to bottom of chat column */}
            <div className="px-4 py-3 border-t border-border">
              <div className="max-w-chat mx-auto">
                <PromptInput
                  onSubmit={handlePromptSubmit}
                  disabled={isInputDisabled}
                />
              </div>
            </div>
          </div>

          {/* ---- Pipeline sidebar — hidden below 1024px via CSS ---- */}
          <div className="hidden lg:block">
            <PipelineSidebar stages={stages} visible={true} />
          </div>
        </div>
      )}
    </div>
  )
}
```

---

#### `src/main.tsx`

```typescript
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import { PipelineProvider } from './context/PipelineContext'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <PipelineProvider>
      <App />
    </PipelineProvider>
  </React.StrictMode>
)
```

---

#### `src/utils/formatters.ts`

```typescript
import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

// Tailwind class merge utility (shadcn/ui convention)
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs))
}

// ISO 8601 timestamp → "10:32 AM"
export function formatTimestamp(iso: string): string {
  return new Date(iso).toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
  })
}
```

---

### Key Technical Decisions

**1. Two separate WebSocket connections, not multiplexed.**
The architecture doc specifies `/ws/chat/{session_id}` for conversation and `/ws/status/{session_id}` for pipeline events. These are kept separate intentionally: chat carries the Elicitor Q&A flow (stateful, sequential), while status carries independent broadcast events (stage transitions, progress). Mixing them on one socket would require ordering guarantees the backend does not provide. The `useWebSocket` hook owns both connections from a single call site — callers see one API.

**2. Reducer is pure; all side effects live in the hook.**
`pipelineReducer` contains zero async operations, no WebSocket sends, no fetch calls. The hook dispatches actions; the reducer transforms state. This makes the reducer trivially testable with `import { pipelineReducer, initialState }` and plain function calls — no mocking needed.

**3. Input disabled state is dual-source.**
The `isInputDisabled` flag in state is set by the reducer when a `stage_update` arrives marking an autonomous stage as `active`. The `usePipelineState` hook additionally derives `isInAutonomousPhase` from the current `stages` array, and ORs them. This means the input is disabled both proactively (when the stage goes active) and defensively (if the reducer flag is somehow stale). Neither source alone is sufficient.

**4. CSS Grid for two-panel layout; `hidden lg:block` for sidebar.**
The sidebar collapse below 1024px is handled via Tailwind's `hidden lg:block` on the sidebar container — no JavaScript resize listeners. The chat column always takes `flex-1`, so it naturally fills full width when the sidebar is hidden. No `window.innerWidth` checks in component code.

**5. `gapClass` computes spacing from `chatEntries` array adjacency.**
Rather than storing gap metadata in state, `App.tsx` derives the correct margin-top Tailwind class at render time by comparing each entry's `kind` to its predecessor. This keeps the reducer state minimal and the spacing logic auditable in one place.

**6. Geist font via Google Fonts import (fallback: Inter).**
The `geist` npm package is an alternative, but the CSS import approach works without a build-time font loader. If `@import url(...)` is blocked by CSP, switch to `npm install geist` and `import 'geist/dist/geist.css'` in `index.css`.

**7. Phase dividers are injected as `ChatEntry` items with `kind: 'phase_divider'`.**
Rather than detecting phase boundaries at render time from message payloads, the reducer inserts a `phase_divider` entry into `chatEntries` whenever a `chat.message` arrives with a `phase` field. This makes the phase divider a first-class member of the thread, with its own `id` for React keying and its own `animate-fade-in` lifecycle.

**8. `StageIndicator` uses `lucide-react` for the done checkmark.**
No SVG inline. `lucide-react` is lightweight, tree-shaken, and consistent with shadcn/ui's icon convention. Only the `Check` icon is used in this story.

---

## Dev Notes

### Setup Checklist (run in order)

1. `npm create vite@latest frontend -- --template react-ts` from repo root
2. `cd frontend && npm install`
3. Install Tailwind: `npm install -D tailwindcss postcss autoprefixer tailwindcss-animate && npx tailwindcss init -p`
4. Init shadcn/ui: `npx shadcn-ui@latest init` (select Neutral base, CSS variables: Yes)
5. Add shadcn components: `npx shadcn-ui@latest add button textarea toast`
6. Install utilities: `npm install clsx tailwind-merge lucide-react geist`
7. Replace `tailwind.config.ts` with the full config from this story
8. Replace `src/index.css` with the CSS from this story
9. Update `vite.config.ts` with the proxy config from this story
10. Create all files in the order listed in "Files to Create"
11. Start dev server: `npm run dev` — verify entry screen loads at localhost:5173

### Dependencies Across Stories

- Story 1.3 (QuestionGroup) depends on `PipelineContext`, `useWebSocket`, and the `chat.question_group` dispatch path in the reducer — all scaffolded here
- Story 1.4 (RequirementsCard / Checkpoint 1) depends on the `chat.checkpoint` message handling in `useWebSocket` and the `control.approve` send path
- Story 1.1 (backend) must be running for WebSocket connections to succeed — the Vite proxy will return 502 if backend is down, which is expected behavior in dev

### Backend Contract Dependencies

The following backend behaviors are assumed by this frontend:

| Assumption | Backend file |
|---|---|
| `POST /sessions` returns `{"session_id": "<uuid>"}` | `app/main.py` |
| WS `/ws/chat/{session_id}` accepts connection and sends `chat.message` on first connect | `app/main.py` |
| WS `/ws/status/{session_id}` sends `status.stage_update` on pipeline transitions | `app/main.py` |
| All WS messages are `{type, payload, timestamp, session_id}` JSON | `app/models/messages.py` |
| `chat.message` payload has `{content: string, sender: "system"\|"user", phase?: string}` | `app/models/messages.py` |
| `status.stage_update` payload has `{stage: string, status: "pending"\|"active"\|"done"\|"error", description?: string}` | `app/models/messages.py` |

If story 1.1 is not yet complete, mock the session endpoint with a static JSON server or hardcode `sessionId` in `App.tsx` for local development.

### Testing

Co-locate tests with components. Use `vitest` + `@testing-library/react`.

Key test scenarios for this story:

- `pipelineReducer`: unit test all action types against `initialState` — no mocking needed (pure function)
- `ChatMessage`: snapshot test both user and system variants
- `StageIndicator`: test pending, active, and done render states
- `TypingIndicator`: verify animation class is applied (no behavior to test)
- `PromptInput`: test Enter submits, Shift+Enter does not, disabled prevents submission
- `App` integration: mock `fetch` for session creation, verify entry screen renders, verify two-panel appears after `USER_MESSAGE_SENT` dispatch

Run tests: `npm run test` (vitest watches by default in dev)

### Known Constraints

- CORS: backend must allow `http://localhost:5173`. Configured in story 1.1 (`app/main.py`).
- WebSocket auto-reconnect will loop indefinitely if backend is down — acceptable for hackathon. Add max retry count for production.
- Session state is in-memory only on the backend (NFR16) — page reload loses the session. The frontend will re-create a session on mount. This is expected behavior.
- `prefers-reduced-motion` disables all CSS animations via the `@media` rule in `index.css`. No JS detection needed.
- The sidebar is hidden below 1024px via Tailwind responsive prefix (`hidden lg:block`). There is no partial collapse or drawer behavior — just hidden.

### FR / UX-DR Coverage

| Requirement | Component / File | Notes |
|---|---|---|
| FR59 | `useWebSocket.ts`, `App.tsx` | Real-time WebSocket chat |
| UX-DR1 | `tailwind.config.ts`, `index.css` | Design tokens |
| UX-DR2 | `tailwind.config.ts` | Geist font, type scale |
| UX-DR3 | `tailwind.config.ts` | Amber accent only on interactive |
| UX-DR4 | `tailwind.config.ts` | Semantic colors |
| UX-DR5 | `App.tsx` entry screen | Logo, tagline, single input |
| UX-DR6 | `App.tsx` two-panel | CSS Grid `1fr 240px` |
| UX-DR7 | `ChatMessage.tsx` | System + user variants, fade-up |
| UX-DR13 | `PipelineSidebar.tsx` | Persistent sidebar, fade-in |
| UX-DR14 | `StageIndicator.tsx` | Status dot, connecting lines |
| UX-DR17 | `PhaseDivider.tsx` | Horizontal line, uppercase label |
| UX-DR18 | `TypingIndicator.tsx` | Opacity pulse, not bounce |
| UX-DR19 | `PromptInput.tsx` | Disabled state, Enter to send |
| UX-DR21 | `tailwind.config.ts` keyframes | All animation tokens |
| UX-DR22 | `App.tsx` `gapClass()` | 8px / 16px / 32px gaps |
| UX-DR23 | `App.tsx` scroll logic | Auto-scroll, "New messages ↓" |
| UX-DR24 | `PipelineContext.tsx`, `pipelineReducer.ts` | Context + useReducer |
| UX-DR25 | `useWebSocket.ts` | Single hook, both connections |
| UX-DR26 | `types/messages.ts` | Mirrors backend types |
| UX-DR27 | `App.tsx` `hidden lg:block` | Desktop-only, sidebar collapse |
| UX-DR28 | `index.css`, `PromptInput.tsx` | WCAG AA, 44px targets, focus ring |
| UX-DR30 | `types/pipeline.ts` `PHASE_LABELS` | Phase label strings |
| UX-DR31 | shadcn toast (wired in story 1.3+) | Toast scaffolded via shadcn add |
