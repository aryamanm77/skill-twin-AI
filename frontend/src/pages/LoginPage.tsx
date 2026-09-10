import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMutation } from '@tanstack/react-query';
import { Brain, Eye, EyeOff, AlertCircle } from 'lucide-react';
import { authApi } from '@/services/api';
import { useAuthStore } from '@/store';
import clsx from 'clsx';

export function LoginPage() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPw, setShowPw] = useState(false);
  const [error, setError] = useState('');
  const { setAuth } = useAuthStore();
  const navigate = useNavigate();

  const loginMutation = useMutation({
    mutationFn: () => authApi.login(username, password),
    onSuccess: (data) => {
      setAuth(data.user, data.access_token);
      navigate('/');
    },
    onError: (err: any) => {
      setError(err?.response?.data?.detail || 'Login failed. Check credentials.');
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    loginMutation.mutate();
  };

  const demoLogin = (user: string, pass: string) => {
    setUsername(user);
    setPassword(pass);
    setTimeout(() => loginMutation.mutate(), 100);
  };

  return (
    <div className="min-h-screen bg-surface-950 bg-grid flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-brand-600 mb-4 shadow-glow-blue">
            <Brain className="w-7 h-7 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-white">SkillTwin AI</h1>
          <p className="text-slate-400 mt-1 text-sm">AI-Powered Practical Skill Training</p>
        </div>

        {/* Login card */}
        <div className="card p-6 shadow-glow-blue">
          <h2 className="text-lg font-semibold text-white mb-6">Sign in to your account</h2>

          <form id="login-form" onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="label block mb-1.5">Username</label>
              <input
                id="username-input"
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="w-full bg-surface-800 border border-surface-700 rounded-lg px-3 py-2.5 text-white text-sm
                           focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent"
                placeholder="admin, expert, or trainee"
                autoComplete="username"
              />
            </div>
            <div>
              <label className="label block mb-1.5">Password</label>
              <div className="relative">
                <input
                  id="password-input"
                  type={showPw ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full bg-surface-800 border border-surface-700 rounded-lg px-3 py-2.5 pr-10 text-white text-sm
                             focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent"
                  placeholder="••••••••"
                  autoComplete="current-password"
                />
                <button
                  type="button"
                  onClick={() => setShowPw(!showPw)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
                >
                  {showPw ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            {error && (
              <div className="flex items-center gap-2 text-sm text-red-400 bg-red-500/10 border border-red-500/30 rounded-lg px-3 py-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                {error}
              </div>
            )}

            <button
              id="login-btn"
              type="submit"
              disabled={loginMutation.isPending || !username || !password}
              className="w-full btn-primary justify-center py-2.5 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loginMutation.isPending ? 'Signing in...' : 'Sign In'}
            </button>
          </form>

          {/* Demo accounts */}
          <div className="mt-6 pt-6 border-t border-surface-700/50">
            <div className="text-xs text-slate-500 mb-3 text-center">Quick demo access</div>
            <div className="grid grid-cols-3 gap-2">
              {[
                { role: 'Admin', user: 'admin', pass: 'admin123', color: 'text-purple-400' },
                { role: 'Expert', user: 'expert', pass: 'expert123', color: 'text-brand-400' },
                { role: 'Trainee', user: 'trainee', pass: 'trainee123', color: 'text-emerald-400' },
              ].map(({ role, user, pass, color }) => (
                <button
                  key={role}
                  id={`demo-${role.toLowerCase()}-btn`}
                  onClick={() => demoLogin(user, pass)}
                  className="text-xs px-3 py-2 bg-surface-800 hover:bg-surface-700 border border-surface-700 
                             rounded-lg transition-colors"
                >
                  <div className={clsx('font-medium', color)}>{role}</div>
                  <div className="text-slate-500 mt-0.5">{user}</div>
                </button>
              ))}
            </div>
          </div>
        </div>

        <p className="text-center text-xs text-slate-600 mt-6">
          SkillTwin AI — Local Processing · Privacy First
        </p>
      </div>
    </div>
  );
}
