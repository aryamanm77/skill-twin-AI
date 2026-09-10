import React from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import {
  LayoutDashboard, Brain, Video, BarChart3, Wrench,
  History, Settings, LogOut, ChevronLeft, ChevronRight,
  Shield, Wifi, WifiOff, Activity,
} from 'lucide-react';
import { useAuthStore, usePipelineStore, useUIStore } from '@/store';
import clsx from 'clsx';

const NAV_ITEMS = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/training', label: 'Training', icon: Brain },
  { to: '/expert', label: 'Expert Mode', icon: Video },
  { to: '/trainee', label: 'Trainee Mode', icon: Activity },
  { to: '/twin', label: 'Digital Twin', icon: Wrench },
  { to: '/analytics', label: 'Analytics', icon: BarChart3 },
  { to: '/builder', label: 'Procedure Builder', icon: Settings },
  { to: '/history', label: 'Session History', icon: History },
  { to: '/settings', label: 'Settings', icon: Settings },
];

export function Sidebar() {
  const { user, logout } = useAuthStore();
  const { wsConnected, isTestMode, isRunning, mode } = usePipelineStore();
  const { sidebarOpen, setSidebar } = useUIStore();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <aside className={clsx(
      'flex flex-col h-full bg-surface-900 border-r border-surface-700/50 transition-all duration-300',
      sidebarOpen ? 'w-56' : 'w-14'
    )}>
      {/* Logo */}
      <div className="flex items-center gap-3 px-4 py-4 border-b border-surface-700/50">
        <div className="w-7 h-7 rounded-lg bg-brand-600 flex items-center justify-center flex-shrink-0">
          <Brain className="w-4 h-4 text-white" />
        </div>
        {sidebarOpen && (
          <div className="overflow-hidden">
            <div className="font-bold text-sm text-white leading-none">SkillTwin</div>
            <div className="text-xs text-brand-400 font-medium mt-0.5">AI Platform</div>
          </div>
        )}
        <button
          id="sidebar-toggle"
          onClick={() => setSidebar(!sidebarOpen)}
          className="ml-auto text-slate-500 hover:text-slate-300 transition-colors flex-shrink-0"
        >
          {sidebarOpen ? <ChevronLeft className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
        </button>
      </div>

      {/* Status indicators */}
      {sidebarOpen && (
        <div className="px-4 py-2 flex items-center gap-3 text-xs border-b border-surface-700/30">
          <div className="flex items-center gap-1.5">
            {wsConnected
              ? <Wifi className="w-3 h-3 text-accent-green" />
              : <WifiOff className="w-3 h-3 text-accent-red" />
            }
            <span className={wsConnected ? 'text-accent-green' : 'text-accent-red'}>
              {wsConnected ? 'Live' : 'Offline'}
            </span>
          </div>
          {isTestMode && (
            <span className="test-mode-badge text-[10px]">TEST</span>
          )}
          {isRunning && (
            <div className="flex items-center gap-1 text-amber-400">
              <div className="status-dot-warning" />
              <span className="uppercase text-[10px]">{mode}</span>
            </div>
          )}
        </div>
      )}

      {/* Navigation */}
      <nav className="flex-1 px-2 py-3 space-y-0.5 overflow-y-auto scrollbar-thin">
        {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              clsx(
                'flex items-center gap-3 px-2.5 py-2 rounded-lg text-sm font-medium transition-all duration-150',
                isActive
                  ? 'text-white bg-brand-600/20 border border-brand-500/30'
                  : 'text-slate-400 hover:text-white hover:bg-surface-800'
              )
            }
            title={!sidebarOpen ? label : undefined}
          >
            <Icon className="w-4 h-4 flex-shrink-0" />
            {sidebarOpen && <span>{label}</span>}
          </NavLink>
        ))}
      </nav>

      {/* Privacy indicator */}
      {sidebarOpen && (
        <div className="px-4 py-2 border-t border-surface-700/30">
          <div className="flex items-center gap-2 text-xs text-slate-500">
            <Shield className="w-3 h-3 text-accent-green" />
            <span>Local Processing</span>
          </div>
          <div className="text-[10px] text-slate-600 mt-0.5">Raw video not stored</div>
        </div>
      )}

      {/* User section */}
      <div className="px-2 py-2 border-t border-surface-700/50">
        {sidebarOpen ? (
          <div className="flex items-center gap-2 px-2 py-2">
            <div className="w-7 h-7 rounded-full bg-brand-600/30 border border-brand-500/30
                           flex items-center justify-center text-xs font-bold text-brand-300">
              {user?.username?.charAt(0).toUpperCase()}
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-xs font-medium text-white truncate">{user?.username}</div>
              <div className="text-[10px] text-slate-500 capitalize">{user?.role}</div>
            </div>
            <button
              id="logout-btn"
              onClick={handleLogout}
              className="text-slate-500 hover:text-red-400 transition-colors"
              title="Logout"
            >
              <LogOut className="w-3.5 h-3.5" />
            </button>
          </div>
        ) : (
          <button
            onClick={handleLogout}
            className="w-full flex items-center justify-center py-2 text-slate-500 hover:text-red-400 transition-colors"
            title="Logout"
          >
            <LogOut className="w-4 h-4" />
          </button>
        )}
      </div>
    </aside>
  );
}
