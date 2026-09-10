import axios from 'axios';
import type {
  AuthToken, User, Domain, ProcedureSummary, Procedure,
  ExpertProfile, TrainingSession, SessionDetail, AppStatus,
  CameraMode,
} from '@/types';

const api = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
});

// Attach token to every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('st_token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// ── Auth ──────────────────────────────────────────────────────────────────────
export const authApi = {
  login: async (username: string, password: string): Promise<AuthToken> => {
    const form = new FormData();
    form.append('username', username);
    form.append('password', password);
    const res = await axios.post('/api/auth/token', form);
    return res.data;
  },
  register: async (data: {
    username: string; email: string; full_name?: string;
    password: string; role?: string;
  }): Promise<User> => {
    const res = await api.post('/auth/register', data);
    return res.data;
  },
  me: async (): Promise<User> => {
    const res = await api.get('/auth/me');
    return res.data;
  },
  users: async (): Promise<User[]> => {
    const res = await api.get('/auth/users');
    return res.data;
  },
};

// ── Domains & Procedures ──────────────────────────────────────────────────────
export const procedureApi = {
  domains: async (): Promise<Domain[]> => {
    const res = await api.get('/procedures/domains');
    return res.data;
  },
  list: async (domainId?: string): Promise<ProcedureSummary[]> => {
    const res = await api.get('/procedures', { params: domainId ? { domain_id: domainId } : {} });
    return res.data;
  },
  get: async (id: string): Promise<Procedure> => {
    const res = await api.get(`/procedures/${id}`);
    return res.data;
  },
  create: async (config: Record<string, unknown>): Promise<{ status: string; id: string }> => {
    const res = await api.post('/procedures', { config });
    return res.data;
  },
  getExpertProfile: async (procedureId: string): Promise<ExpertProfile> => {
    const res = await api.get(`/procedures/${procedureId}/expert-profile`);
    return res.data;
  },
};

// ── Sessions ──────────────────────────────────────────────────────────────────
export const sessionApi = {
  start: async (params: {
    procedure_id: string; mode: string;
    camera_mode: CameraMode; camera_source?: string;
  }) => {
    const res = await api.post('/sessions/start', params);
    return res.data;
  },
  stop: async (sessionId: string) => {
    const res = await api.post(`/sessions/${sessionId}/stop`);
    return res.data;
  },
  active: async (): Promise<AppStatus['pipeline']> => {
    const res = await api.get('/sessions/active');
    return res.data;
  },
  list: async (params?: { procedure_id?: string; mode?: string; limit?: number }): Promise<TrainingSession[]> => {
    const res = await api.get('/sessions', { params });
    return res.data;
  },
  get: async (id: string): Promise<SessionDetail> => {
    const res = await api.get(`/sessions/${id}`);
    return res.data;
  },
};

// ── Calibration ────────────────────────────────────────────────────────────────
export const calibrationApi = {
  save: async (procedureId: string, points: [number, number][],
               frameWidth: number, frameHeight: number) => {
    const res = await api.post('/calibration', {
      procedure_id: procedureId, points, frame_width: frameWidth, frame_height: frameHeight,
    });
    return res.data;
  },
  get: async (procedureId: string) => {
    const res = await api.get(`/calibration/${procedureId}`);
    return res.data;
  },
};

// ── Status ────────────────────────────────────────────────────────────────────
export const statusApi = {
  health: async () => {
    const res = await api.get('/health');
    return res.data;
  },
  status: async (): Promise<AppStatus> => {
    const res = await api.get('/status');
    return res.data;
  },
  cameraModes: async () => {
    const res = await api.get('/camera/modes');
    return res.data;
  },
};

export default api;
