import { useEffect, useRef, useCallback } from 'react';
import { usePipelineStore } from '@/store';
import type { WSMessage, PipelineUpdate } from '@/types';

const WS_URL = `ws://${window.location.hostname}:8000/ws/stream`;
const RECONNECT_DELAY = 3000;

export function useWebSocket() {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout>>();
  const { updateFromPipeline, setWsConnected, addEvent } = usePipelineStore();

  const connect = useCallback(() => {
    try {
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onopen = () => {
        setWsConnected(true);
        // Keepalive ping every 20s
        const ping = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) ws.send('ping');
        }, 20_000);
        (ws as any)._pingInterval = ping;
      };

      ws.onmessage = (event) => {
        try {
          const msg: WSMessage = JSON.parse(event.data);
          handleMessage(msg);
        } catch { /* ignore parse errors */ }
      };

      ws.onclose = () => {
        clearInterval((ws as any)._pingInterval);
        setWsConnected(false);
        reconnectTimer.current = setTimeout(connect, RECONNECT_DELAY);
      };

      ws.onerror = () => {
        ws.close();
      };
    } catch {
      reconnectTimer.current = setTimeout(connect, RECONNECT_DELAY);
    }
  }, []);

  const handleMessage = useCallback((msg: WSMessage) => {
    switch (msg.type) {
      case 'pipeline_update':
        if (msg.data) {
          updateFromPipeline(msg.data as unknown as PipelineUpdate);
          // Extract FSM events
          const events = (msg.data as any).fsm_events;
          if (events?.length) {
            events.forEach((e: any) => addEvent(e));
          }
        }
        break;
      case 'feedback':
        // Could show a toast here
        break;
      case 'error':
        console.warn('[WS] Server error:', msg.data);
        break;
      default:
        break;
    }
  }, [updateFromPipeline, addEvent]);

  useEffect(() => {
    connect();
    return () => {
      clearTimeout(reconnectTimer.current);
      wsRef.current?.close();
    };
  }, [connect]);

  return {
    send: (msg: string) => wsRef.current?.send(msg),
    isConnected: usePipelineStore((s) => s.wsConnected),
  };
}
