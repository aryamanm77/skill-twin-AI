// All TypeScript types for SkillTwin AI

export interface User {
  id: number;
  username: string;
  email: string;
  full_name?: string;
  role: 'admin' | 'expert' | 'trainee';
  is_active: boolean;
}

export interface AuthToken {
  access_token: string;
  token_type: string;
  user: User;
}

export interface Domain {
  id: string;
  name: string;
  icon: string;
  description: string;
}

export interface ProcedureStep {
  id: string;
  order: number;
  name: string;
  description: string;
  action: 'pick' | 'move' | 'place' | 'tool_use' | 'complete';
  expected_object?: string;
  source_zone?: string;
  target_zone?: string;
  expected_duration_s: number;
  max_duration_s: number;
  min_duration_s: number;
}

export interface ProcedureObject {
  id: string;
  name: string;
  display_name: string;
  yolo_classes: string[];
  color: string;
  source_zone?: string;
}

export interface WorkspaceZone {
  id: string;
  name: string;
  color: string;
  normalized: { x: number; y: number; w: number; h: number };
}

export interface Procedure {
  id: string;
  name: string;
  domain: string;
  description: string;
  version: string;
  steps: ProcedureStep[];
  objects: ProcedureObject[];
  workspace_zones: WorkspaceZone[];
  scoring_weights: {
    sequence: number;
    object_accuracy: number;
    position: number;
    timing: number;
    movement: number;
  };
  tolerances: {
    position_px: number;
    timing_factor: number;
    trajectory_dtw: number;
  };
}

export interface ProcedureSummary {
  id: string;
  name: string;
  description: string;
  domain_id: string;
  version: string;
  steps_count: number;
}

export interface TrackedObject {
  track_id: number;
  class_name: string;
  confidence: number;
  center: [number, number];
  center_px: [number, number];
  workspace_pos?: [number, number];
  current_zones: string[];
  is_active: boolean;
  frames_seen: number;
  path_length: number;
}

export interface StepRecord {
  step_id: string;
  step_name: string;
  state: 'pending' | 'in_progress' | 'completed' | 'skipped' | 'failed';
  expected_object?: string;
  detected_object?: string;
  started_at?: number;
  completed_at?: number;
  duration_s?: number;
  position_at_completion?: [number, number];
  sequence_order: number;
  notes: string;
}

export interface FSMState {
  current_step_idx: number;
  current_step?: {
    id: string;
    name: string;
    action: string;
    expected_object?: string;
    order: number;
  };
  completed_steps: string[];
  total_steps: number;
  is_complete: boolean;
  step_records: StepRecord[];
  elapsed_s: number;
}

export interface FSMEvent {
  event_type: 'step_started' | 'step_completed' | 'step_failed' | 'wrong_object' | 'sequence_deviation';
  timestamp: number;
  step_id?: string;
  step_name?: string;
  detected_object?: string;
  expected_object?: string;
  message: string;
  severity: 'info' | 'warning' | 'error';
  data: Record<string, unknown>;
}

export interface SkillScore {
  final_score: number;
  sequence: number;
  object_accuracy: number;
  position: number;
  timing: number;
  movement: number;
  weights: Record<string, number>;
  steps_completed: number;
  total_steps: number;
  explanation: string[];
  step_scores: Array<{
    step_id: string;
    step_name: string;
    completed: boolean;
    score: number;
    sequence: number;
    object: number;
    position: number;
    timing: number;
    movement: number;
    deviations: string[];
  }>;
}

export interface PipelineUpdate {
  frame?: string;  // base64 JPEG
  tracked: TrackedObject[];
  fsm?: FSMState;
  score?: SkillScore;
  fsm_events: FSMEvent[];
  model_status: string;
  inference_ms: number;
  test_mode: boolean;
}

export interface WSMessage {
  type: 'pipeline_update' | 'session_status' | 'feedback' | 'error' | 'connected' | 'keepalive' | 'pong';
  timestamp: number;
  data?: Record<string, unknown>;
  client_id?: string;
  message?: string;
}

export interface TrainingSession {
  id: string;
  user_id: number;
  procedure_id: string;
  mode: 'expert' | 'trainee';
  status: 'active' | 'completed' | 'aborted';
  started_at: string;
  ended_at?: string;
  final_score?: number;
  total_duration_s?: number;
}

export interface SessionDetail extends TrainingSession {
  sequence_score?: number;
  object_score?: number;
  position_score?: number;
  timing_score?: number;
  movement_score?: number;
  step_results?: StepRecord[];
  trajectory_data?: Record<string, unknown[]>;
  events?: FSMEvent[];
  score_explanation?: string[];
}

export interface ExpertProfile {
  has_profile: boolean;
  session_id?: string;
  recorded_at?: string;
  total_duration_s?: number;
  step_count?: number;
  step_data?: StepRecord[];
  trajectory_data?: Record<string, unknown[]>;
}

export type CameraMode = 'test' | 'real' | 'video';

export interface AppStatus {
  pipeline: {
    running: boolean;
    mode: string;
    session_id?: string;
    frame_count: number;
    camera: { running: boolean; error?: string };
    model_status: string;
    fsm_state?: FSMState;
    current_score?: SkillScore;
  };
  model_status: string;
  ws_clients: number;
  privacy: {
    raw_video_stored: boolean;
    face_recognition: boolean;
    processing: string;
  };
}
