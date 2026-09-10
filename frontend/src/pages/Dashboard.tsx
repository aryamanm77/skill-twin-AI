import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Brain, TrendingUp, Activity, CheckCircle, Clock, Target, Users, BarChart2 } from 'lucide-react';
import { procedureApi, sessionApi, statusApi } from '@/services/api';
import { usePipelineStore, useAuthStore } from '@/store';
import { useNavigate } from 'react-router-dom';
import clsx from 'clsx';

function StatCard({ label, value, sub, icon: Icon, color = 'brand' }: any) {
  const colorMap: Record<string, string> = {
    brand: 'text-brand-400 bg-brand-500/10 border-brand-500/20',
    green: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20',
    amber: 'text-amber-400 bg-amber-500/10 border-amber-500/20',
    purple: 'text-purple-400 bg-purple-500/10 border-purple-500/20',
  };
  return (
    <div className="card p-5 flex items-start gap-4">
      <div className={clsx('p-2.5 rounded-xl border', colorMap[color])}>
        <Icon className="w-5 h-5" />
      </div>
      <div>
        <div className="text-2xl font-bold text-white font-mono">{value}</div>
        <div className="text-sm text-slate-300 mt-0.5">{label}</div>
        {sub && <div className="text-xs text-slate-500 mt-1">{sub}</div>}
      </div>
    </div>
  );
}

export function Dashboard() {
  const { user } = useAuthStore();
  const { isRunning, currentScore, isTestMode } = usePipelineStore();
  const navigate = useNavigate();

  const { data: sessions } = useQuery({
    queryKey: ['sessions'],
    queryFn: () => sessionApi.list({ limit: 20 }),
  });
  const { data: procedures } = useQuery({
    queryKey: ['procedures'],
    queryFn: () => procedureApi.list(),
  });
  const { data: domains } = useQuery({
    queryKey: ['domains'],
    queryFn: () => procedureApi.domains(),
  });

  const completedSessions = sessions?.filter(s => s.status === 'completed') ?? [];
  const avgScore = completedSessions.length
    ? (completedSessions.reduce((a, s) => a + (s.final_score ?? 0), 0) / completedSessions.length).toFixed(1)
    : '—';

  return (
    <div className="space-y-6">
      {/* Welcome */}
      <div>
        <h1 className="text-2xl font-bold text-white">
          Welcome back, <span className="text-gradient">{user?.full_name || user?.username}</span>
        </h1>
        <p className="text-slate-400 mt-1 text-sm">
          AI-Powered Skill Training & Assessment Platform
        </p>
      </div>

      {/* Active session banner */}
      {isRunning && (
        <div className="flex items-center gap-3 px-4 py-3 bg-amber-500/10 border border-amber-500/30 rounded-xl">
          <div className="status-dot-warning" />
          <span className="text-sm text-amber-300 font-medium">Session in progress</span>
          <button onClick={() => navigate('/training')} className="ml-auto btn-primary py-1.5 text-xs">
            Go to Training →
          </button>
        </div>
      )}

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Training Sessions" value={sessions?.length ?? 0} icon={Activity} color="brand"
                  sub="All time" />
        <StatCard label="Average Score" value={avgScore} icon={Target} color="green"
                  sub="Completed sessions" />
        <StatCard label="Procedures" value={procedures?.length ?? 0} icon={Brain} color="purple"
                  sub="Available" />
        <StatCard label="Domains" value={domains?.length ?? 0} icon={BarChart2} color="amber"
                  sub="Active" />
      </div>

      {/* Domain quick-select */}
      <div>
        <h2 className="text-sm font-semibold text-slate-300 mb-3 uppercase tracking-wider">Training Domains</h2>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
          {domains?.map((d) => (
            <button
              key={d.id}
              id={`domain-${d.id}`}
              onClick={() => navigate('/training')}
              className="card p-4 flex flex-col items-center gap-2 text-center hover:bg-surface-800 transition-colors group"
            >
              <span className="text-2xl">{d.icon}</span>
              <span className="text-xs font-medium text-slate-300 group-hover:text-white">{d.name}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Recent sessions */}
      <div>
        <h2 className="text-sm font-semibold text-slate-300 mb-3 uppercase tracking-wider">Recent Sessions</h2>
        <div className="card overflow-hidden">
          {completedSessions.length === 0 ? (
            <div className="p-8 text-center text-slate-500 text-sm">
              No completed sessions yet. Start your first training!
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-surface-700/50 text-left">
                  <th className="px-4 py-3 text-xs text-slate-500 font-medium">Session</th>
                  <th className="px-4 py-3 text-xs text-slate-500 font-medium">Mode</th>
                  <th className="px-4 py-3 text-xs text-slate-500 font-medium">Procedure</th>
                  <th className="px-4 py-3 text-xs text-slate-500 font-medium">Score</th>
                  <th className="px-4 py-3 text-xs text-slate-500 font-medium">Duration</th>
                  <th className="px-4 py-3 text-xs text-slate-500 font-medium">Date</th>
                </tr>
              </thead>
              <tbody>
                {completedSessions.slice(0, 10).map((s) => (
                  <tr key={s.id}
                      className="border-b border-surface-700/30 hover:bg-surface-800/50 cursor-pointer"
                      onClick={() => navigate(`/history/${s.id}`)}>
                    <td className="px-4 py-3 font-mono text-xs text-slate-400">{s.id}</td>
                    <td className="px-4 py-3">
                      <span className={clsx(
                        'text-xs px-2 py-0.5 rounded-full border',
                        s.mode === 'expert'
                          ? 'border-brand-500/30 bg-brand-500/10 text-brand-300'
                          : 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300'
                      )}>
                        {s.mode}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-slate-300 text-xs">{s.procedure_id}</td>
                    <td className="px-4 py-3">
                      {s.final_score != null ? (
                        <span className={clsx(
                          'font-mono font-bold',
                          s.final_score >= 85 ? 'text-emerald-400' :
                          s.final_score >= 65 ? 'text-amber-400' : 'text-red-400'
                        )}>
                          {s.final_score.toFixed(0)}
                        </span>
                      ) : <span className="text-slate-600">—</span>}
                    </td>
                    <td className="px-4 py-3 text-slate-400 text-xs font-mono">
                      {s.total_duration_s ? `${s.total_duration_s.toFixed(0)}s` : '—'}
                    </td>
                    <td className="px-4 py-3 text-slate-500 text-xs">
                      {s.started_at ? new Date(s.started_at).toLocaleString() : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
