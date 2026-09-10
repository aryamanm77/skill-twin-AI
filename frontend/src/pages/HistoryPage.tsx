import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { useParams, useNavigate } from 'react-router-dom';
import { sessionApi } from '@/services/api';
import { ArrowLeft, Award, CheckCircle, XCircle, Clock, Target } from 'lucide-react';
import clsx from 'clsx';

function ScoreBar({ label, value, max = 100 }: { label: string; value?: number; max?: number }) {
  const pct = ((value ?? 0) / max) * 100;
  const color = pct >= 85 ? 'bg-emerald-500' : pct >= 65 ? 'bg-amber-500' : 'bg-red-500';
  return (
    <div className="flex items-center gap-3">
      <div className="w-28 text-xs text-slate-400 text-right shrink-0">{label}</div>
      <div className="flex-1 score-bar">
        <div className={clsx('score-bar-fill', color)} style={{ width: `${pct}%` }} />
      </div>
      <div className="w-12 text-xs font-mono text-white text-right shrink-0">
        {value != null ? value.toFixed(1) : '—'}
      </div>
    </div>
  );
}

export function SessionDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { data: session, isLoading } = useQuery({
    queryKey: ['session', id],
    queryFn: () => sessionApi.get(id!),
    enabled: !!id,
  });

  if (isLoading) return <div className="text-slate-500 p-8">Loading session...</div>;
  if (!session) return <div className="text-red-400 p-8">Session not found</div>;

  const score = session.final_score;
  const scoreColor = score != null
    ? score >= 85 ? 'text-emerald-400' : score >= 65 ? 'text-amber-400' : 'text-red-400'
    : 'text-slate-500';

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex items-center gap-4">
        <button onClick={() => navigate(-1)} className="btn-ghost text-slate-400">
          <ArrowLeft className="w-4 h-4" />
          Back
        </button>
        <div>
          <h1 className="text-xl font-bold text-white">Session Report</h1>
          <div className="text-xs font-mono text-slate-500">{session.id}</div>
        </div>
        <div className="ml-auto">
          <span className={clsx(
            'px-3 py-1 rounded-full text-xs font-medium border',
            session.mode === 'expert'
              ? 'border-brand-500/30 bg-brand-500/10 text-brand-300'
              : 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300'
          )}>
            {session.mode}
          </span>
        </div>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="card p-4 text-center">
          <div className={clsx('text-4xl font-bold font-mono', scoreColor)}>
            {score != null ? score.toFixed(0) : '—'}
          </div>
          <div className="text-xs text-slate-400 mt-1">Final Score</div>
        </div>
        <div className="card p-4 text-center">
          <div className="text-2xl font-bold text-white">
            {session.step_results?.filter(s => s.state === 'completed').length ?? '—'}
            <span className="text-slate-500 text-sm">/{session.step_results?.length ?? '—'}</span>
          </div>
          <div className="text-xs text-slate-400 mt-1">Steps Completed</div>
        </div>
        <div className="card p-4 text-center">
          <div className="text-2xl font-bold text-white font-mono">
            {session.total_duration_s ? `${session.total_duration_s.toFixed(0)}s` : '—'}
          </div>
          <div className="text-xs text-slate-400 mt-1">Duration</div>
        </div>
        <div className="card p-4 text-center">
          <div className="text-sm font-medium text-white capitalize">{session.status}</div>
          <div className="text-xs text-slate-400 mt-1">
            {session.ended_at ? new Date(session.ended_at).toLocaleTimeString() : '—'}
          </div>
        </div>
      </div>

      {session.mode === 'trainee' && score != null && (
        <div className="card p-6 space-y-4">
          <div className="panel-title">Score Breakdown</div>
          <ScoreBar label="Sequence" value={session.sequence_score ?? undefined} />
          <ScoreBar label="Object Accuracy" value={session.object_score ?? undefined} />
          <ScoreBar label="Position" value={session.position_score ?? undefined} />
          <ScoreBar label="Timing" value={session.timing_score ?? undefined} />
          <ScoreBar label="Movement" value={session.movement_score ?? undefined} />
        </div>
      )}

      {session.score_explanation && session.score_explanation.length > 0 && (
        <div className="card p-6 space-y-3">
          <div className="panel-title">Explanation</div>
          {session.score_explanation.map((line, i) => (
            <div key={i} className={clsx(
              'text-sm px-3 py-2 rounded-lg',
              line.startsWith('✓') ? 'bg-emerald-500/10 text-emerald-300' :
              line.startsWith('⚠') ? 'bg-amber-500/10 text-amber-300' :
              'bg-surface-800 text-slate-300'
            )}>
              {line}
            </div>
          ))}
        </div>
      )}

      {session.step_results && (
        <div className="card p-6">
          <div className="panel-title mb-4">Step-by-Step Results</div>
          <div className="space-y-2">
            {session.step_results.map((step, i) => (
              <div key={i} className={clsx(
                'flex items-center gap-3 px-4 py-3 rounded-lg',
                step.state === 'completed' ? 'bg-emerald-500/10 border border-emerald-500/20' :
                step.state === 'failed' ? 'bg-red-500/10 border border-red-500/20' :
                'bg-surface-800'
              )}>
                {step.state === 'completed'
                  ? <CheckCircle className="w-4 h-4 text-emerald-400 shrink-0" />
                  : <XCircle className="w-4 h-4 text-red-400 shrink-0" />
                }
                <div className="flex-1">
                  <div className="text-sm font-medium text-white">{step.step_name}</div>
                  {step.detected_object !== step.expected_object && step.detected_object && (
                    <div className="text-xs text-red-400 mt-0.5">
                      Expected: {step.expected_object} · Detected: {step.detected_object}
                    </div>
                  )}
                </div>
                {step.duration_s != null && (
                  <div className="text-xs font-mono text-slate-400">{step.duration_s.toFixed(1)}s</div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export function HistoryPage() {
  const navigate = useNavigate();
  const { data: sessions, isLoading } = useQuery({
    queryKey: ['sessions-history'],
    queryFn: () => sessionApi.list({ limit: 50 }),
  });

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-bold text-white">Session History</h1>
      {isLoading ? (
        <div className="text-slate-500">Loading sessions...</div>
      ) : sessions?.length === 0 ? (
        <div className="card p-8 text-center text-slate-500">No sessions recorded yet.</div>
      ) : (
        <div className="card overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-surface-700/50">
                <th className="px-4 py-3 text-left text-xs text-slate-500 font-medium">Session ID</th>
                <th className="px-4 py-3 text-left text-xs text-slate-500 font-medium">Mode</th>
                <th className="px-4 py-3 text-left text-xs text-slate-500 font-medium">Procedure</th>
                <th className="px-4 py-3 text-left text-xs text-slate-500 font-medium">Status</th>
                <th className="px-4 py-3 text-left text-xs text-slate-500 font-medium">Score</th>
                <th className="px-4 py-3 text-left text-xs text-slate-500 font-medium">Date</th>
              </tr>
            </thead>
            <tbody>
              {sessions?.map((s) => (
                <tr key={s.id}
                    className="border-b border-surface-700/30 hover:bg-surface-800/50 cursor-pointer"
                    onClick={() => navigate(`/history/${s.id}`)}>
                  <td className="px-4 py-3 font-mono text-xs text-slate-400">{s.id}</td>
                  <td className="px-4 py-3">
                    <span className={clsx(
                      'text-xs px-2 py-0.5 rounded-full border',
                      s.mode === 'expert' ? 'border-brand-500/30 bg-brand-500/10 text-brand-300'
                        : 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300'
                    )}>
                      {s.mode}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-slate-300 text-xs">{s.procedure_id}</td>
                  <td className="px-4 py-3 text-xs capitalize text-slate-400">{s.status}</td>
                  <td className="px-4 py-3">
                    {s.final_score != null ? (
                      <span className={clsx('font-mono font-bold',
                        s.final_score >= 85 ? 'text-emerald-400' :
                        s.final_score >= 65 ? 'text-amber-400' : 'text-red-400')}>
                        {s.final_score.toFixed(0)}
                      </span>
                    ) : <span className="text-slate-600">—</span>}
                  </td>
                  <td className="px-4 py-3 text-slate-500 text-xs">
                    {new Date(s.started_at).toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
