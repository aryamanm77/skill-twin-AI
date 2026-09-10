import React, { useState, useEffect } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { Play, Square, RefreshCw, Camera, AlertTriangle, CheckCircle, Info } from 'lucide-react';
import { sessionApi, procedureApi, statusApi } from '@/services/api';
import { usePipelineStore, useUIStore } from '@/store';
import { LiveFeed } from '@/components/camera/LiveFeed';
import { SkillScorePanel, StepTimeline, ExplanationPanel } from '@/components/score/ScorePanel';
import { DigitalTwin } from '@/three/WorkstationScene';
import type { Procedure, CameraMode } from '@/types';
import clsx from 'clsx';

// ── Live Feedback Banner ───────────────────────────────────────────────────────
function FeedbackBanner({ events }: { events: any[] }) {
  if (!events.length) return null;
  const latest = events[0];
  const severity = latest.severity;
  return (
    <div className={clsx(
      'feedback-banner',
      severity === 'error' ? 'feedback-error' :
      severity === 'warning' ? 'feedback-warning' :
      'feedback-success'
    )}>
      <span className="text-base">
        {severity === 'error' ? '⚠' : severity === 'warning' ? '⏱' : '✓'}
      </span>
      <span>{latest.message}</span>
      {latest.event_type === 'wrong_object' && (
        <span className="ml-auto text-xs opacity-75">
          Expected: {latest.expected_object} | Detected: {latest.detected_object}
        </span>
      )}
    </div>
  );
}

// ── Session Controls ───────────────────────────────────────────────────────────
interface SessionControlsProps {
  mode: 'expert' | 'trainee';
  procedureId: string;
  cameraMode: CameraMode;
  onSessionChange: (id: string | null) => void;
}

function SessionControls({ mode, procedureId, cameraMode, onSessionChange }: SessionControlsProps) {
  const { isRunning, sessionId, setSessionActive, stopSession } = usePipelineStore();

  const startMutation = useMutation({
    mutationFn: () => sessionApi.start({ procedure_id: procedureId, mode, camera_mode: cameraMode }),
    onSuccess: (data) => {
      setSessionActive(data.session_id, mode);
      onSessionChange(data.session_id);
    },
  });

  const stopMutation = useMutation({
    mutationFn: () => sessionApi.stop(sessionId!),
    onSuccess: () => {
      stopSession();
      onSessionChange(null);
    },
  });

  if (isRunning && sessionId) {
    return (
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2 text-sm text-accent-green">
          <div className="status-dot-active" />
          <span className="font-mono text-xs">{sessionId}</span>
        </div>
        <button
          id="stop-session-btn"
          className="btn-danger"
          onClick={() => stopMutation.mutate()}
          disabled={stopMutation.isPending}
        >
          <Square className="w-4 h-4" />
          {stopMutation.isPending ? 'Stopping...' : 'Stop Session'}
        </button>
      </div>
    );
  }

  return (
    <button
      id="start-session-btn"
      className={mode === 'expert' ? 'btn-primary' : 'btn-success'}
      onClick={() => startMutation.mutate()}
      disabled={startMutation.isPending}
    >
      <Play className="w-4 h-4" />
      {startMutation.isPending ? 'Starting...' : `Start ${mode === 'expert' ? 'Expert' : 'Trainee'} Session`}
    </button>
  );
}

// ── Main Training Page ─────────────────────────────────────────────────────────
export function TrainingPage() {
  const [mode, setMode] = useState<'expert' | 'trainee'>('trainee');
  const [cameraMode, setCameraMode] = useState<CameraMode>('test');
  const [selectedProcedureId, setSelectedProcedureId] = useState('basic_assembly');
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const { recentEvents, fsmState, isTestMode } = usePipelineStore();

  const { data: procedures } = useQuery({
    queryKey: ['procedures'],
    queryFn: () => procedureApi.list(),
  });

  const { data: procedure } = useQuery<Procedure>({
    queryKey: ['procedure', selectedProcedureId],
    queryFn: () => procedureApi.get(selectedProcedureId),
    enabled: !!selectedProcedureId,
  });

  const { data: expertProfile } = useQuery({
    queryKey: ['expert-profile', selectedProcedureId],
    queryFn: () => procedureApi.getExpertProfile(selectedProcedureId),
    enabled: !!selectedProcedureId,
  });

  return (
    <div className="flex flex-col h-full gap-4">
      {/* Top bar */}
      <div className="flex items-center gap-4 flex-wrap">
        {/* Procedure selector */}
        <select
          id="procedure-select"
          value={selectedProcedureId}
          onChange={(e) => setSelectedProcedureId(e.target.value)}
          className="bg-surface-800 border border-surface-700 rounded-lg px-3 py-2 text-sm text-white"
        >
          {procedures?.map((p) => (
            <option key={p.id} value={p.id}>{p.name}</option>
          ))}
        </select>

        {/* Mode toggle */}
        <div className="flex bg-surface-800 rounded-lg p-1 gap-1">
          {(['expert', 'trainee'] as const).map((m) => (
            <button
              key={m}
              id={`mode-${m}-btn`}
              onClick={() => setMode(m)}
              className={clsx(
                'px-3 py-1.5 rounded-md text-sm font-medium transition-all',
                mode === m ? 'bg-brand-600 text-white' : 'text-slate-400 hover:text-white'
              )}
            >
              {m === 'expert' ? '👁 Expert' : '🎯 Trainee'}
            </button>
          ))}
        </div>

        {/* Camera mode */}
        <div className="flex bg-surface-800 rounded-lg p-1 gap-1">
          {(['test', 'real'] as const).map((m) => (
            <button
              key={m}
              id={`camera-${m}-btn`}
              onClick={() => setCameraMode(m)}
              className={clsx(
                'px-3 py-1.5 rounded-md text-xs font-medium transition-all flex items-center gap-1.5',
                cameraMode === m ? 'bg-surface-700 text-white' : 'text-slate-500 hover:text-slate-300'
              )}
            >
              <Camera className="w-3 h-3" />
              {m === 'test' ? 'Test Mode' : 'Real Camera'}
            </button>
          ))}
        </div>

        {/* Expert profile status */}
        {mode === 'trainee' && (
          <div className={clsx(
            'flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full border',
            expertProfile?.has_profile
              ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300'
              : 'border-amber-500/30 bg-amber-500/10 text-amber-300'
          )}>
            {expertProfile?.has_profile
              ? <><CheckCircle className="w-3 h-3" />Expert profile loaded</>
              : <><AlertTriangle className="w-3 h-3" />No expert profile — record expert first</>
            }
          </div>
        )}

        <div className="ml-auto">
          <SessionControls
            mode={mode}
            procedureId={selectedProcedureId}
            cameraMode={cameraMode}
            onSessionChange={setActiveSessionId}
          />
        </div>
      </div>

      {/* TEST MODE banner */}
      {isTestMode && (
        <div className="flex items-center gap-2 px-4 py-2 bg-cyan-500/10 border border-cyan-500/30 rounded-lg text-xs text-cyan-300">
          <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0" />
          <strong>SIMULATION / TEST MODE</strong> — Synthetic data generated. Not connected to real camera or YOLO model.
        </div>
      )}

      {/* Live feedback */}
      {recentEvents.length > 0 && (
        <FeedbackBanner events={recentEvents} />
      )}

      {/* Main 3-column layout */}
      <div className="flex-1 grid grid-cols-[1fr_1.4fr_1fr] gap-4 min-h-0">
        {/* Left: Camera */}
        <div className="flex flex-col gap-3 min-h-0">
          <div className="card flex-1 p-0 overflow-hidden">
            <div className="panel-header">
              <span className="panel-title">Live Camera</span>
              {isTestMode && <span className="test-mode-badge">TEST</span>}
            </div>
            <LiveFeed className="flex-1 min-h-0" style={{ height: 'calc(100% - 40px)' }} />
          </div>
          <SkillScorePanel />
        </div>

        {/* Center: 3D Digital Twin */}
        <div className="card relative overflow-hidden">
          <div className="panel-header absolute top-0 left-0 right-0 z-10 bg-surface-900/80 backdrop-blur-sm">
            <span className="panel-title">3D Digital Twin</span>
            <span className="text-xs text-slate-500">Interactive · Rotate / Zoom</span>
          </div>
          <DigitalTwin
            procedure={procedure}
            className="w-full h-full pt-10"
          />
        </div>

        {/* Right: Analytics */}
        <div className="flex flex-col gap-3 min-h-0 overflow-y-auto scrollbar-thin">
          {/* Current Step */}
          <div className="card p-4">
            <div className="panel-title mb-3">Current Step</div>
            {fsmState?.current_step ? (
              <div className="space-y-2">
                <div className="text-lg font-semibold text-white">{fsmState.current_step.name}</div>
                <div className="flex items-center gap-2 text-sm text-slate-400">
                  <span>Step {fsmState.current_step.order} / {fsmState.total_steps}</span>
                </div>
                {fsmState.current_step.expected_object && (
                  <div className="text-xs px-3 py-2 bg-brand-500/10 border border-brand-500/30 rounded-lg text-brand-300">
                    Expected: {fsmState.current_step.expected_object}
                  </div>
                )}
              </div>
            ) : (
              <div className="text-sm text-slate-500">Start session to begin</div>
            )}
          </div>

          {/* Step Timeline */}
          <StepTimeline />

          {/* Explanation */}
          <ExplanationPanel />
        </div>
      </div>
    </div>
  );
}
