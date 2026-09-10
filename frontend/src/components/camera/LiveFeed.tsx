import React, { useRef, useEffect } from 'react';
import { usePipelineStore } from '@/store';
import { AlertTriangle, Camera, Cpu } from 'lucide-react';
import clsx from 'clsx';

interface LiveFeedProps {
  className?: string;
}

export function LiveFeed({ className }: LiveFeedProps) {
  const { cameraFrame, trackedObjects, isTestMode, modelStatus, inferenceMs, wsConnected } = usePipelineStore();
  const imgRef = useRef<HTMLImageElement>(null);

  useEffect(() => {
    if (imgRef.current && cameraFrame) {
      imgRef.current.src = `data:image/jpeg;base64,${cameraFrame}`;
    }
  }, [cameraFrame]);

  return (
    <div className={clsx('relative bg-black rounded-xl overflow-hidden', className)}>
      {/* Video feed */}
      {cameraFrame ? (
        <img
          ref={imgRef}
          alt="Live camera feed with YOLO detection overlay"
          className="w-full h-full object-contain"
          id="live-feed-img"
        />
      ) : (
        <div className="flex flex-col items-center justify-center h-full gap-3 text-slate-600">
          <Camera className="w-12 h-12" />
          <div className="text-sm font-medium">
            {wsConnected ? 'Starting camera...' : 'Connecting to server...'}
          </div>
          {!wsConnected && (
            <div className="text-xs text-slate-700">WebSocket disconnected — retrying...</div>
          )}
        </div>
      )}

      {/* TEST MODE banner */}
      {isTestMode && (
        <div className="absolute top-2 left-2 right-2 flex items-center gap-2 
                        bg-cyan-500/20 border border-cyan-500/50 rounded-lg px-3 py-1.5 backdrop-blur-sm">
          <AlertTriangle className="w-3.5 h-3.5 text-cyan-400 flex-shrink-0" />
          <span className="text-xs font-medium text-cyan-300">SIMULATION / TEST MODE — Not real camera output</span>
        </div>
      )}

      {/* Stats overlay */}
      <div className="absolute bottom-2 left-2 flex items-center gap-2 text-xs">
        <div className="bg-black/60 backdrop-blur-sm rounded px-2 py-1 flex items-center gap-1.5">
          <Cpu className="w-3 h-3 text-slate-400" />
          <span className="text-slate-300 font-mono">
            {inferenceMs > 0 ? `${inferenceMs.toFixed(0)}ms` : 'No inference'}
          </span>
        </div>
        <div className="bg-black/60 backdrop-blur-sm rounded px-2 py-1 flex items-center gap-1.5">
          <div className={clsx(
            'w-2 h-2 rounded-full',
            modelStatus === 'ok' ? 'bg-accent-green' :
            modelStatus === 'test_mode' ? 'bg-cyan-400' :
            modelStatus?.startsWith('error') ? 'bg-accent-red' : 'bg-amber-400'
          )} />
          <span className="text-slate-300">
            {modelStatus === 'ok' ? `${trackedObjects.length} detected` :
             modelStatus === 'test_mode' ? 'Test data' :
             modelStatus?.startsWith('error') ? 'Model error' : modelStatus}
          </span>
        </div>
      </div>

      {/* Detection count badges */}
      {trackedObjects.length > 0 && (
        <div className="absolute top-2 right-2 flex flex-col gap-1">
          {trackedObjects.map((obj) => (
            <div key={obj.track_id}
                 className="bg-black/70 backdrop-blur-sm rounded px-2 py-0.5 text-xs font-mono text-green-400">
              [{obj.track_id}] {obj.class_name} {(obj.confidence * 100).toFixed(0)}%
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
