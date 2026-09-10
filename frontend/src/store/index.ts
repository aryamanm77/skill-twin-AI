import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type {
  User, PipelineUpdate, FSMState, SkillScore,
  TrackedObject, FSMEvent, Procedure, AppStatus,
} from '@/types';

// ── Auth Store ────────────────────────────────────────────────────────────────
interface AuthStore {
  user: User | null;
  token: string | null;
  setAuth: (user: User, token: string) => void;
  logout: () => void;
  isAuthenticated: boolean;
}

export const useAuthStore = create<AuthStore>()(
  persist(
    (set, get) => ({
      user: { id: 'local-dev', username: 'developer', full_name: 'Local Developer', role: 'admin' },
      token: 'mock-token',
      isAuthenticated: true,
      setAuth: (user, token) => {
        localStorage.setItem('st_token', token);
        set({ user, token, isAuthenticated: true });
      },
      logout: () => {
        localStorage.removeItem('st_token');
        set({ user: null, token: null, isAuthenticated: false });
      },
    }),
    { name: 'skilltwin-auth', partialize: (s) => ({ user: s.user, token: s.token, isAuthenticated: s.isAuthenticated }) }
  )
);

// ── Pipeline Store ─────────────────────────────────────────────────────────────
interface PipelineStore {
  isRunning: boolean;
  mode: 'idle' | 'expert' | 'trainee' | 'test';
  sessionId: string | null;
  cameraFrame: string | null;        // base64 JPEG
  trackedObjects: TrackedObject[];
  fsmState: FSMState | null;
  currentScore: SkillScore | null;
  recentEvents: FSMEvent[];          // last 10 FSM events
  modelStatus: string;
  inferenceMs: number;
  isTestMode: boolean;
  wsConnected: boolean;
  lastUpdateTs: number;
  // Actions
  updateFromPipeline: (data: PipelineUpdate) => void;
  setSessionActive: (sessionId: string, mode: string) => void;
  stopSession: () => void;
  setWsConnected: (v: boolean) => void;
  addEvent: (event: FSMEvent) => void;
}

export const usePipelineStore = create<PipelineStore>()((set, get) => ({
  isRunning: false,
  mode: 'idle',
  sessionId: null,
  cameraFrame: null,
  trackedObjects: [],
  fsmState: null,
  currentScore: null,
  recentEvents: [],
  modelStatus: 'not_loaded',
  inferenceMs: 0,
  isTestMode: false,
  wsConnected: false,
  lastUpdateTs: 0,

  updateFromPipeline: (data) => {
    set((s) => ({
      cameraFrame: data.frame ?? s.cameraFrame,
      trackedObjects: data.tracked,
      fsmState: data.fsm ?? s.fsmState,
      currentScore: data.score ?? s.currentScore,
      modelStatus: data.model_status,
      inferenceMs: data.inference_ms,
      isTestMode: data.test_mode,
      lastUpdateTs: Date.now(),
      recentEvents: data.fsm_events?.length
        ? [...data.fsm_events, ...s.recentEvents].slice(0, 20)
        : s.recentEvents,
    }));
  },

  setSessionActive: (sessionId, mode) =>
    set({ isRunning: true, sessionId, mode: mode as PipelineStore['mode'] }),

  stopSession: () =>
    set({ isRunning: false, sessionId: null, mode: 'idle', cameraFrame: null,
          trackedObjects: [], fsmState: null }),

  setWsConnected: (v) => set({ wsConnected: v }),

  addEvent: (event) =>
    set((s) => ({ recentEvents: [event, ...s.recentEvents].slice(0, 20) })),
}));

// ── UI Store ──────────────────────────────────────────────────────────────────
interface UIStore {
  selectedDomain: string | null;
  selectedProcedure: Procedure | null;
  sidebarOpen: boolean;
  setDomain: (id: string | null) => void;
  setProcedure: (p: Procedure | null) => void;
  setSidebar: (v: boolean) => void;
}

export const useUIStore = create<UIStore>()((set) => ({
  selectedDomain: null,
  selectedProcedure: null,
  sidebarOpen: true,
  setDomain: (id) => set({ selectedDomain: id }),
  setProcedure: (p) => set({ selectedProcedure: p }),
  setSidebar: (v) => set({ sidebarOpen: v }),
}));
