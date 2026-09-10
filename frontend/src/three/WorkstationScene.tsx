import React, { useRef, useMemo, Suspense } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, Grid, Text, Line, Sphere } from '@react-three/drei';
import * as THREE from 'three';
import { usePipelineStore } from '@/store';
import type { Procedure, TrackedObject } from '@/types';

// ── Workstation table ──────────────────────────────────────────────────────────
function Workstation() {
  return (
    <group>
      {/* Table surface */}
      <mesh receiveShadow position={[0, 0, 0]}>
        <boxGeometry args={[3.2, 0.04, 2.0]} />
        <meshStandardMaterial color="#1e293b" roughness={0.8} metalness={0.1} />
      </mesh>
      {/* Table legs */}
      {[[-1.5, -0.3, -0.9], [1.5, -0.3, -0.9], [-1.5, -0.3, 0.9], [1.5, -0.3, 0.9]].map(([x, y, z], i) => (
        <mesh key={i} position={[x, y, z]}>
          <cylinderGeometry args={[0.03, 0.03, 0.6, 8]} />
          <meshStandardMaterial color="#0f172a" roughness={0.9} />
        </mesh>
      ))}
    </group>
  );
}

// ── Zone markers ───────────────────────────────────────────────────────────────
function ZoneMarker({ zone }: { zone: { id: string; name: string; color: string; normalized: { x: number; y: number; w: number; h: number } } }) {
  const { x, y, w, h } = zone.normalized;
  // Convert normalized [0,1] to 3D workstation space [-1.5,1.5] x [-0.9,0.9]
  const wx = (x + w / 2) * 3.0 - 1.5;
  const wz = (y + h / 2) * 1.8 - 0.9;
  const ww = w * 3.0;
  const wd = h * 1.8;
  const color = new THREE.Color(zone.color);

  return (
    <group position={[wx, 0.025, wz]}>
      <mesh>
        <boxGeometry args={[ww, 0.002, wd]} />
        <meshStandardMaterial color={zone.color} transparent opacity={0.15} />
      </mesh>
      {/* Border */}
      <lineSegments>
        <edgesGeometry args={[new THREE.BoxGeometry(ww, 0.002, wd)]} />
        <lineBasicMaterial color={zone.color} transparent opacity={0.6} />
      </lineSegments>
      <Text
        position={[0, 0.05, 0]}
        fontSize={0.07}
        color={zone.color}
        anchorX="center"
        anchorY="middle"
        rotation={[-Math.PI / 2, 0, 0]}
      >
        {zone.name}
      </Text>
    </group>
  );
}

// ── Tracked object sphere ─────────────────────────────────────────────────────
function ObjectMarker({ obj, color }: { obj: TrackedObject; color: string }) {
  const meshRef = useRef<THREE.Mesh>(null!);
  const [nx, ny] = obj.center;
  const wx = nx * 3.0 - 1.5;
  const wz = ny * 1.8 - 0.9;

  useFrame((_, delta) => {
    if (meshRef.current) {
      meshRef.current.rotation.y += delta * 0.8;
    }
  });

  return (
    <group position={[wx, 0.15, wz]}>
      <mesh ref={meshRef} castShadow>
        <sphereGeometry args={[0.06, 16, 16]} />
        <meshStandardMaterial color={color} emissive={color} emissiveIntensity={0.3} />
      </mesh>
      <Text position={[0, 0.12, 0]} fontSize={0.05} color="white" anchorX="center">
        [{obj.track_id}] {obj.class_name}
      </Text>
    </group>
  );
}

// ── Trajectory line ────────────────────────────────────────────────────────────
function TrajectoryLine({ points, color, opacity = 1 }: {
  points: Array<{ cx: number; cy: number }>;
  color: string;
  opacity?: number;
}) {
  const linePoints = useMemo(() => {
    return points.map((p) => new THREE.Vector3(
      p.cx * 3.0 - 1.5, 0.1, p.cy * 1.8 - 0.9
    ));
  }, [points]);

  if (linePoints.length < 2) return null;

  return (
    <Line
      points={linePoints}
      color={color}
      lineWidth={2}
      transparent
      opacity={opacity}
    />
  );
}

// ── Current step indicator ─────────────────────────────────────────────────────
function StepIndicator({ step }: { step: { name: string; expected_object?: string } }) {
  return (
    <group position={[0, 0.8, 0]}>
      <Text fontSize={0.1} color="#60a5fa" anchorX="center" anchorY="middle">
        {`▶ ${step.name}`}
      </Text>
    </group>
  );
}

// ── Scene ─────────────────────────────────────────────────────────────────────
interface WorkstationSceneProps {
  procedure?: Procedure;
  expertTrajectories?: Record<number, Array<{ cx: number; cy: number }>>;
  traineeTrajectories?: Record<number, Array<{ cx: number; cy: number }>>;
}

function Scene({ procedure, expertTrajectories, traineeTrajectories }: WorkstationSceneProps) {
  const { trackedObjects, fsmState } = usePipelineStore();

  // Build object → color map from procedure
  const objectColors = useMemo(() => {
    const map: Record<string, string> = {};
    procedure?.objects?.forEach((o) => { map[o.id] = o.color; });
    return map;
  }, [procedure]);

  // YOLO class → procedure color
  const classToColor = useMemo(() => {
    const map: Record<string, string> = {};
    procedure?.objects?.forEach((o) => {
      o.yolo_classes.forEach((cls) => { map[cls] = o.color; });
    });
    return map;
  }, [procedure]);

  return (
    <>
      {/* Lighting */}
      <ambientLight intensity={0.4} />
      <directionalLight position={[3, 4, 2]} intensity={1.2} castShadow />
      <pointLight position={[-2, 2, -1]} intensity={0.4} color="#4d82ff" />

      {/* Workstation */}
      <Workstation />

      {/* Grid */}
      <Grid position={[0, -0.02, 0]} args={[3.2, 2.0]} cellColor="#1e293b" sectionColor="#334155" />

      {/* Zones */}
      {procedure?.workspace_zones?.map((zone) => (
        <ZoneMarker key={zone.id} zone={zone} />
      ))}

      {/* Tracked objects */}
      {trackedObjects.map((obj) => (
        <ObjectMarker
          key={obj.track_id}
          obj={obj}
          color={classToColor[obj.class_name] ?? '#60a5fa'}
        />
      ))}

      {/* Expert trajectory (ghost) */}
      {expertTrajectories && Object.entries(expertTrajectories).map(([id, traj]) => (
        <TrajectoryLine key={`expert-${id}`} points={traj} color="#60a5fa" opacity={0.4} />
      ))}

      {/* Trainee trajectory */}
      {trackedObjects.map((obj) => (
        <TrajectoryLine
          key={`trainee-${obj.track_id}`}
          points={obj.track_id ? (obj as any).history ?? [] : []}
          color={classToColor[obj.class_name] ?? '#10b981'}
          opacity={0.8}
        />
      ))}

      {/* Current step indicator */}
      {fsmState?.current_step && <StepIndicator step={fsmState.current_step} />}
    </>
  );
}

// ── Public component ───────────────────────────────────────────────────────────
interface DigitalTwinProps {
  procedure?: Procedure;
  expertTrajectories?: Record<number, Array<{ cx: number; cy: number }>>;
  className?: string;
}

export function DigitalTwin({ procedure, expertTrajectories, className }: DigitalTwinProps) {
  return (
    <div className={className}>
      {/* Label */}
      <div className="absolute top-2 left-2 z-10 text-xs text-slate-500 
                      bg-black/40 backdrop-blur-sm rounded px-2 py-1">
        ⚠ Approximate spatial representation — not true 3D reconstruction
      </div>

      <Canvas
        camera={{ position: [0, 2.5, 3.0], fov: 50 }}
        shadows
        gl={{ antialias: true, alpha: false }}
        style={{ background: '#080e1d' }}
      >
        <Suspense fallback={null}>
          <Scene procedure={procedure} expertTrajectories={expertTrajectories} />
          <OrbitControls
            enableDamping
            dampingFactor={0.05}
            minDistance={1.5}
            maxDistance={6}
            target={[0, 0.2, 0]}
          />
        </Suspense>
      </Canvas>
    </div>
  );
}
