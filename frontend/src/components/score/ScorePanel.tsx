import React from 'react';
import { usePipelineStore } from '@/store';
import { CheckCircle, AlertTriangle, Clock, Target, TrendingUp, Award } from 'lucide-react';
import clsx from 'clsx';

function ScoreBar({ value, color, label }: { value: number; color: string; label: string }) {
  return (
    <div className="space-y-1">
      <div className="flex justify-between items-center">
        <span className="text-xs text-slate-400">{label}</span>
        <span className="text-xs font-mono font-semibold text-white">{value.toFixed(0)}</span>
      </div>
      <div className="score-bar">
        <div
          className={clsx('score-bar-fill', color)}
          style={{ width: `${Math.min(100, value)}%` }}
        />
      </div>
    </div>
  );
}

function ScoreRing({ score }: { score: number }) {
  const r = 52;
  const circ = 2 * Math.PI * r;
  const fill = (score / 100) * circ;
  const color = score >= 85 ? '#10b981' : score >= 65 ? '#f59e0b' : '#ef4444';

  return (
    <div className="relative w-32 h-32 flex items-center justify-center">
      <svg className="w-full h-full -rotate-90" viewBox="0 0 120 120">
        <circle cx="60" cy="60" r={r} fill="none" stroke="#1e293b" strokeWidth="8" />
        <circle
          cx="60" cy="60" r={r} fill="none"
          stroke={color} strokeWidth="8"
          strokeLinecap="round"
          strokeDasharray={`${fill} ${circ}`}
          style={{ transition: 'stroke-dasharray 0.7s ease-out, stroke 0.3s' }}
        />
      </svg>
      <div className="absolute text-center">
        <div className="text-3xl font-bold text-white font-mono">{score.toFixed(0)}</div>
        <div className="text-xs text-slate-400">/ 100</div>
      </div>
    </div>
  );
}

export function SkillScorePanel() {
  const { currentScore, fsmState, isRunning } = usePipelineStore();

  if (!currentScore && !isRunning) {
    return (
      <div className="card p-4 flex flex-col items-center justify-center gap-3 min-h-[200px] text-slate-600">
        <Award className="w-10 h-10" />
        <div className="text-sm text-center">Start a training session to see your skill score</div>
      </div>
    );
  }

  const score = currentScore;
  const completedSteps = fsmState?.completed_steps?.length ?? 0;
  const totalSteps = fsmState?.total_steps ?? 0;

  return (
    <div className="card p-4 space-y-4 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <span className="panel-title">Skill Score</span>
        {fsmState?.is_complete && (
          <span className="text-xs text-accent-green flex items-center gap-1">
            <CheckCircle className="w-3.5 h-3.5" />
            Complete
          </span>
        )}
      </div>

      {/* Main score ring */}
      <div className="flex items-center justify-center py-2">
        <ScoreRing score={score?.final_score ?? 0} />
      </div>

      {/* Step progress */}
      <div className="flex items-center justify-between text-xs text-slate-400 px-1">
        <span>{completedSteps} / {totalSteps} steps</span>
        <div className="flex items-center gap-1">
          <Clock className="w-3 h-3" />
          <span>{fsmState ? `${fsmState.elapsed_s.toFixed(0)}s` : '—'}</span>
        </div>
      </div>

      {/* Breakdown bars */}
      {score && (
        <div className="space-y-2.5 pt-1 border-t border-surface-700/50">
          <ScoreBar value={score.sequence} color="bg-brand-500" label={`Sequence (${Math.round(score.weights.sequence * 100)}%)`} />
          <ScoreBar value={score.object_accuracy} color="bg-purple-500" label={`Object Accuracy (${Math.round(score.weights.object_accuracy * 100)}%)`} />
          <ScoreBar value={score.position} color="bg-cyan-500" label={`Position (${Math.round(score.weights.position * 100)}%)`} />
          <ScoreBar value={score.timing} color="bg-amber-500" label={`Timing (${Math.round(score.weights.timing * 100)}%)`} />
          <ScoreBar value={score.movement} color="bg-emerald-500" label={`Movement (${Math.round(score.weights.movement * 100)}%)`} />
        </div>
      )}
    </div>
  );
}

// ── Step Timeline ──────────────────────────────────────────────────────────────
export function StepTimeline() {
  const { fsmState } = usePipelineStore();
  if (!fsmState) return null;
  const { step_records, current_step, completed_steps, total_steps } = fsmState;

  return (
    <div className="card p-4 space-y-2">
      <div className="panel-title pb-2">Step Timeline</div>
      {step_records.map((rec, i) => {
        const isActive = current_step?.id === rec.step_id;
        const isDone = rec.state === 'completed';
        const isFailed = rec.state === 'failed';
        return (
          <div
            key={rec.step_id}
            className={clsx(
              'step-timeline-item',
              isDone ? 'bg-emerald-500/10 text-emerald-300' :
              isFailed ? 'bg-red-500/10 text-red-300' :
              isActive ? 'bg-brand-500/10 text-brand-300 border border-brand-500/30' :
              'text-slate-500'
            )}
          >
            <span className="text-base w-5 text-center">
              {isDone ? '✓' : isFailed ? '✗' : isActive ? '▶' : '○'}
            </span>
            <div className="flex-1 min-w-0">
              <div className="text-sm font-medium truncate">{rec.step_name}</div>
              {rec.duration_s != null && (
                <div className="text-xs opacity-70">{rec.duration_s.toFixed(1)}s</div>
              )}
            </div>
            {rec.detected_object && rec.detected_object !== rec.expected_object && (
              <span className="text-xs text-red-400 shrink-0 flex items-center gap-1">
                <AlertTriangle className="w-3 h-3" />
                Wrong obj
              </span>
            )}
          </div>
        );
      })}
    </div>
  );
}

// ── Explanation Panel ──────────────────────────────────────────────────────────
export function ExplanationPanel() {
  const { currentScore } = usePipelineStore();
  if (!currentScore?.explanation?.length) return null;

  return (
    <div className="card p-4 space-y-3">
      <div className="panel-title">Score Explanation</div>
      <div className="space-y-2">
        {currentScore.explanation.map((line, i) => (
          <div
            key={i}
            className={clsx(
              'text-xs px-3 py-2 rounded-lg',
              line.startsWith('✓') ? 'bg-emerald-500/10 text-emerald-300' :
              line.startsWith('⚠') ? 'bg-amber-500/10 text-amber-300' :
              'bg-surface-800 text-slate-300'
            )}
          >
            {line}
          </div>
        ))}
      </div>
    </div>
  );
}
