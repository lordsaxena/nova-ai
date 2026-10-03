import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { FilesetResolver, GestureRecognizer } from "@mediapipe/tasks-vision";
import {
  OrbitControls,
  Stars,
  Text,
} from "@react-three/drei";
import {
  useEffect,
  useRef,
  useState,
} from "react";
import * as THREE from "three";

import {
  novaSystems,
  type NovaSystem,
} from "./data/novaSystems";

import type {
  NovaEvent,
} from "./data/novaEvents";

import {
  subscribeToEvents,
  connectToBackend,
  sendCameraFrame,
} from "./events/eventBus";

import "./App.css";


/* =========================================================
   EVENT POSITIONS
========================================================= */

const eventPositions: Record<
  string,
  [number, number, number]
> = {
  MOTION_DETECTED: [-4, 1, 0],

  PERSON_DETECTED: [-4, 1, 0],

  OBJECT_DETECTED: [-4, 1, 0],

  CAMERA_CONNECTED: [-4, 1, 0],

  CAMERA_ERROR: [-4, 1, 0],

  MEMORY_UPDATED: [4, 1, -1],

  MEMORY_READY: [4, 1, -1],

  AGENT_ACTIVE: [3, -2, 0],

  THREAT_SCAN: [0, 3, -2],

  TRACE_ONLINE: [0, 3, -2],

  KNOWLEDGE_UPDATE: [0, -4, -2],
};


/* =========================================================
   CORE
========================================================= */

function Core() {

  const ref =
    useRef<THREE.Mesh>(null);

  useFrame(({ clock }) => {

    if (!ref.current)
      return;

    const pulse =
      1 +
      Math.sin(
        clock.getElapsedTime() * 2
      ) * 0.04;

    ref.current.scale.setScalar(
      pulse
    );

  });

  return (
    <mesh ref={ref}>

      <sphereGeometry
        args={[0.7, 32, 32]}
      />

      <meshBasicMaterial
        color="#ffffff"
        transparent
        opacity={0.9}
      />

    </mesh>
  );
}


/* =========================================================
   VISION ACTIVITY RING
========================================================= */

function VisionActivityRing({
  active,
  confidence,
}: {
  active: boolean;
  confidence: number;
}) {

  const ref =
    useRef<THREE.Mesh>(null);

  useFrame(({ clock }) => {

    if (!ref.current)
      return;

    const time =
      clock.getElapsedTime();

    ref.current.rotation.z =
      time *
      (active ? 1.8 : 0.25);

    const target =
      active
        ? 1 + confidence * 0.35
        : 0.85;

    const next =
      THREE.MathUtils.lerp(
        ref.current.scale.x,
        target,
        0.08
      );

    ref.current.scale.setScalar(
      next
    );

    const material =
      ref.current.material as
        THREE.MeshBasicMaterial;

    material.opacity =
      active
        ? 0.25 +
          confidence * 0.55
        : 0.08;

  });

  return (
    <mesh ref={ref}>

      <torusGeometry
        args={[
          0.72,
          0.012,
          8,
          64,
        ]}
      />

      <meshBasicMaterial
        color="#7dd3fc"
        transparent
        opacity={0.08}
      />

    </mesh>
  );
}


/* =========================================================
   PERSON POSITION SIGNAL
========================================================= */

function PersonPositionSignal({
  position,
  active,
}: {
  position: {
    x: number;
    y: number;
  } | null;

  active: boolean;
}) {

  if (!position)
    return null;

  const x =
    (position.x - 0.5) * 2.2;

  const y =
    -(position.y - 0.5) * 1.5;

  return (
    <group
      position={[
        x,
        y,
        0.3,
      ]}
    >

      <mesh>

        <sphereGeometry
          args={[
            active ? 0.12 : 0.07,
            16,
            16,
          ]}
        />

        <meshBasicMaterial
          color="#ffffff"
          transparent
          opacity={
            active
              ? 0.95
              : 0.35
          }
        />

      </mesh>

      <mesh
        rotation={[
          Math.PI / 2,
          0,
          0,
        ]}
      >

        <ringGeometry
          args={[
            0.16,
            0.19,
            32,
          ]}
        />

        <meshBasicMaterial
          color="#7dd3fc"
          transparent
          opacity={
            active
              ? 0.8
              : 0.2
          }
          side={
            THREE.DoubleSide
          }
        />

      </mesh>

    </group>
  );
}


/* =========================================================
   PLANET
========================================================= */

function Planet({
  system,
  selected,
  onClick,
  activity = 0,
  active = false,
  personPosition = null,
}: {
  system: NovaSystem;

  selected: boolean;

  onClick: () => void;

  activity?: number;

  active?: boolean;

  personPosition?: {
    x: number;
    y: number;
  } | null;
}) {

  const ref =
    useRef<THREE.Mesh>(null);

  useFrame(({ clock }) => {

    if (!ref.current)
      return;

    const time =
      clock.getElapsedTime();

    const basePulse =
      1 +
      Math.sin(
        time * 1.4 +
        system.position[0]
      ) * 0.025;

    const visionPulse =
      system.name === "VISION" &&
      active
        ? 1 +
          Math.sin(time * 8) *
            (0.045 +
              activity * 0.06)
        : 1;

    const targetScale =
      basePulse *
      visionPulse *
      (selected ? 1.18 : 1);

    const next =
      THREE.MathUtils.lerp(
        ref.current.scale.x,
        targetScale,
        0.12
      );

    ref.current.scale.setScalar(
      next
    );

    const material =
      ref.current.material as
        THREE.MeshStandardMaterial;

    if (
      system.name ===
      "VISION"
    ) {

      material.emissiveIntensity =
        selected
          ? 2.5 +
            activity * 3
          : 1.2 +
            activity * 4;

      material.opacity =
        active
          ? 0.9
          : 0.72;

    } else {

      material.emissiveIntensity =
        selected
          ? 2.2
          : 1.2;

    }

  });

  const isVision =
    system.name ===
    "VISION";

  return (
    <group
      position={
        system.position
      }
    >

      <mesh
        ref={ref}
        onClick={onClick}
      >

        <sphereGeometry
          args={[
            selected
              ? 0.58
              : 0.5,
            32,
            32,
          ]}
        />

        <meshStandardMaterial
          color={system.color}
          emissive={system.color}
          emissiveIntensity={
            selected
              ? 2.5
              : 1.2
          }
          transparent
          opacity={0.72}
        />

      </mesh>


      {isVision && (
        <VisionActivityRing
          active={active}
          confidence={
            activity
          }
        />
      )}


      {isVision && (
        <PersonPositionSignal
          position={
            personPosition
          }
          active={active}
        />
      )}


      <pointLight
        color={system.color}
        intensity={
          selected
            ? 2.5
            : isVision && active
            ? 1.8 +
              activity * 2
            : 0.7
        }
        distance={4}
      />


      <Text
        position={[
          0,
          -0.85,
          0,
        ]}
        fontSize={0.16}
        color="white"
        anchorX="center"
        anchorY="middle"
      >
        {system.name}
      </Text>

    </group>
  );
}


/* =========================================================
   MODULE
========================================================= */

function Module({
  module,
  index,
  total,
  onClick,
}: {
  module: {
    name: string;
    description: string;
    components: {
      name: string;
      description: string;
    }[];
  };

  index: number;

  total: number;

  onClick: () => void;
}) {

  const angle =
    (index / total) *
    Math.PI *
    2;

  const radius = 1.8;

  return (
    <group
      position={[
        Math.cos(angle) *
          radius,

        Math.sin(angle) *
          radius,

        0,
      ]}
    >

      <mesh
        onClick={onClick}
      >

        <sphereGeometry
          args={[
            0.3,
            24,
            24,
          ]}
        />

        <meshStandardMaterial
          color="#7dd3fc"
          emissive="#7dd3fc"
          emissiveIntensity={1.4}
        />

      </mesh>

      <Text
        position={[
          0,
          -0.48,
          0,
        ]}
        fontSize={0.12}
        color="white"
        anchorX="center"
        anchorY="middle"
      >
        {module.name}
      </Text>

    </group>
  );
}


/* =========================================================
   COMPONENT NODE
========================================================= */

function ComponentNode({
  component,
  index,
  total,
}: {
  component: {
    name: string;
    description: string;
  };

  index: number;

  total: number;
}) {

  const angle =
    (index / total) *
    Math.PI *
    2;

  const radius = 1.5;

  return (
    <group
      position={[
        Math.cos(angle) *
          radius,

        Math.sin(angle) *
          radius,

        0,
      ]}
    >

      <mesh>

        <sphereGeometry
          args={[
            0.12,
            16,
            16,
          ]}
        />

        <meshBasicMaterial
          color="#ffffff"
        />

      </mesh>

      <Text
        position={[
          0,
          -0.25,
          0,
        ]}
        fontSize={0.07}
        color="white"
        anchorX="center"
      >
        {component.name}
      </Text>

    </group>
  );
}


/* =========================================================
   COMPONENT UNIVERSE
========================================================= */

function ComponentUniverse({
  module,
}: {
  module: {
    name: string;
    description: string;
    components: {
      name: string;
      description: string;
    }[];
  };
}) {

  return (
    <group>

      <Core />

      {module.components.map(
        (
          component,
          index
        ) => (

          <ComponentNode
            key={
              component.name
            }
            component={
              component
            }
            index={
              index
            }
            total={
              module
                .components
                .length
            }
          />

        )
      )}

    </group>
  );
}


/* =========================================================
   FLOATING MODULES
========================================================= */

function FloatingModules({
  system,
  onModuleClick,
}: {
  system: NovaSystem;

  onModuleClick: (
    module:
      NovaSystem["modules"][number]
  ) => void;
}) {

  return (
    <group>

      <Core />

      {system.modules.map(
        (
          module,
          index
        ) => (

          <Module
            key={
              module.name
            }
            module={
              module
            }
            index={
              index
            }
            total={
              system
                .modules
                .length
            }
            onClick={() =>
              onModuleClick(
                module
              )
            }
          />

        )
      )}

    </group>
  );
}


/* =========================================================
   EVENT PARTICLE
========================================================= */

function EventParticle({
  event,
}: {
  event: NovaEvent;
}) {

  const ref =
    useRef<THREE.Mesh>(null);

  const start =
    eventPositions[
      event.type
    ] ?? [0, 0, 0];

  const destination:
    [number, number, number] =
    event.source ===
    "VISION"
      ? [0, 0, 0]

      : event.source ===
        "MEMORY"
      ? [4, 1, -1]

      : event.source ===
        "TRACE"
      ? [0, 3, -2]

      : event.source ===
        "AGENTS"
      ? [3, -2, 0]

      : event.source ===
        "KNOWLEDGE"
      ? [0, -4, -2]

      : [0, 0, 0];


  useFrame(
    ({
      clock,
    }) => {

      if (!ref.current)
        return;

      const time =
        (
          clock.getElapsedTime() *
            0.35 +
          event.id *
            0.0001
        ) % 1;

      const eased =
        time < 0.5
          ? 2 * time * time
          : 1 -
            Math.pow(
              -2 * time + 2,
              2
            ) /
              2;

      ref.current.position.lerpVectors(

        new THREE.Vector3(
          ...start
        ),

        new THREE.Vector3(
          ...destination
        ),

        eased
      );

      const pulse =
        1 +
        Math.sin(
          clock.getElapsedTime() *
            10
        ) *
          0.35;

      ref.current.scale.setScalar(
        pulse
      );

    }
  );


  return (
    <mesh ref={ref}>

      <sphereGeometry
        args={[
          0.055,
          12,
          12,
        ]}
      />

      <meshBasicMaterial
        color={
          event.color
        }
        transparent
        opacity={0.95}
      />

    </mesh>
  );
}


/* =========================================================
   LIVE EVENT PARTICLES
========================================================= */

function LiveEventParticles({
  events,
}: {
  events: NovaEvent[];
}) {

  return (
    <group>

      {events
        .slice(0, 20)
        .map(
          (event) => (

            <EventParticle
              key={
                event.id
              }
              event={
                event
              }
            />

          )
        )}

    </group>
  );
}


/* =========================================================
   3D CAMERA CONTROLLER
========================================================= */

function CameraController({
  selectedSystem,
  selectedModule,
  personPosition,
  gestureControl,
  visionControlEnabled,
}: {
  selectedSystem:
    | NovaSystem
    | null;

  selectedModule:
    | NovaSystem["modules"][number]
    | null;

  personPosition: {
    x: number;
    y: number;
  } | null;

  gestureControl: {
    x: number;
    y: number;
    zoom: number;
    gesture: string;
  } | null;

  visionControlEnabled: boolean;
}) {

  const {
    camera,
  } = useThree();


  const targetPosition =
    useRef(
      new THREE.Vector3(
        0,
        0,
        8
      )
    );


  const targetLookAt =
    useRef(
      new THREE.Vector3(
        0,
        0,
        0
      )
    );


  /* =====================================================
     AUTOMATIC CAMERA FOLLOW
  ===================================================== */

  useFrame(() => {

    /* =====================================================
       HAND CONTROL HAS PRIORITY
       When a valid gesture is detected, the hand controls
       the camera even if a system/module is selected.
    ===================================================== */

    if (
      visionControlEnabled &&
      gestureControl
    ) {

      const normalizedX =
        gestureControl.x - 0.5;

      const normalizedY =
        gestureControl.y - 0.5;

      const cameraX =
        THREE.MathUtils.clamp(
          normalizedX * 4.0,
          -2.0,
          2.0
        );

      const cameraY =
        THREE.MathUtils.clamp(
          -normalizedY * 2.6,
          -1.3,
          1.3
        );

      const cameraZ =
        THREE.MathUtils.clamp(
          8 - gestureControl.zoom * 3.0,
          4.8,
          10.5
        );

      targetPosition.current.set(
        cameraX,
        cameraY,
        cameraZ
      );

      targetLookAt.current.set(
        cameraX * 0.22,
        cameraY * 0.22,
        0
      );

    }

    else if (
      selectedModule
    ) {

      targetPosition.current.set(
        0,
        0,
        4.2
      );

      targetLookAt.current.set(
        0,
        0,
        0
      );

    }

    else if (
      selectedSystem
    ) {

      targetPosition.current.set(
        selectedSystem.position[0] *
          0.35,

        selectedSystem.position[1] *
          0.35,

        5.5
      );

      targetLookAt.current.set(
        selectedSystem.position[0],
        selectedSystem.position[1],
        selectedSystem.position[2]
      );

    }

    else if (
      visionControlEnabled &&
      personPosition
    ) {

      const normalizedX =
        personPosition.x - 0.5;

      const normalizedY =
        personPosition.y - 0.5;

      const cameraX =
        THREE.MathUtils.clamp(
          normalizedX * 2.4,
          -1.2,
          1.2
        );

      const cameraY =
        THREE.MathUtils.clamp(
          -normalizedY * 1.5,
          -0.75,
          0.75
        );

      targetPosition.current.set(
        cameraX,
        cameraY,
        8
      );

      targetLookAt.current.set(
        cameraX * 0.25,
        cameraY * 0.25,
        0
      );

    }

    else {

      targetPosition.current.set(
        0,
        0,
        8
      );

      targetLookAt.current.set(
        0,
        0,
        0
      );

    }


    /* =================================================
       SMOOTH CAMERA
    ================================================= */

    camera.position.lerp(
      targetPosition.current,
      0.035
    );


    const currentLook =
      new THREE.Vector3();

    currentLook.copy(
      targetLookAt.current
    );


    const currentDirection =
      new THREE.Vector3();

    currentDirection
      .subVectors(
        currentLook,
        camera.position
      )
      .normalize();


    const targetQuaternion =
      new THREE.Quaternion();

    targetQuaternion.setFromUnitVectors(
      new THREE.Vector3(
        0,
        0,
        -1
      ),
      currentDirection
    );


    camera.quaternion.slerp(
      targetQuaternion,
      0.04
    );

  });


  return null;
}


/* =========================================================
   GESTURE TARGET SELECTION
========================================================= */

function GestureSelectionLayer({
  systems,
  gestureControl,
  onTarget,
  onSelect,
}: {
  systems: NovaSystem[];
  gestureControl: {
    x: number;
    y: number;
    zoom: number;
    gesture: string;
  } | null;
  onTarget: (system: NovaSystem | null) => void;
  onSelect: (system: NovaSystem) => void;
}) {

  const { camera } = useThree();

  const meshRefs = useRef<THREE.Mesh[]>([]);
  const raycaster = useRef(new THREE.Raycaster());
  const targetRef = useRef<NovaSystem | null>(null);
  const targetSinceRef = useRef(0);
  const selectedTargetRef = useRef<string | null>(null);

  useFrame(() => {

    if (
      !gestureControl ||
      !gestureControl.gesture.startsWith("POINT")
    ) {
      if (targetRef.current !== null) {
        targetRef.current = null;
        targetSinceRef.current = 0;
        selectedTargetRef.current = null;
        onTarget(null);
      }
      return;
    }

    /* The webcam preview is mirrored, so mirror X too. */
    const ndc = new THREE.Vector2(
      (1 - gestureControl.x) * 2 - 1,
      -(gestureControl.y * 2 - 1)
    );

    raycaster.current.setFromCamera(ndc, camera);

    const intersections =
      raycaster.current.intersectObjects(
        meshRefs.current,
        false
      );

    let nextTarget: NovaSystem | null = null;

    if (intersections.length > 0) {
      const systemName =
        intersections[0].object.userData.systemName as string | undefined;

      if (systemName) {
        nextTarget =
          systems.find(
            (system) => system.name === systemName
          ) ?? null;
      }
    }

    if (nextTarget?.name !== targetRef.current?.name) {
      targetRef.current = nextTarget;
      targetSinceRef.current = performance.now();
      selectedTargetRef.current = null;
      onTarget(nextTarget);
      return;
    }

    /* Hold the point for 700 ms to select. */
    if (
      nextTarget &&
      performance.now() - targetSinceRef.current > 700 &&
      selectedTargetRef.current !== nextTarget.name
    ) {
      selectedTargetRef.current = nextTarget.name;
      onSelect(nextTarget);
    }
  });

  return (
    <group>
      {systems.map((system, index) => {
        const refCallback = (mesh: THREE.Mesh | null) => {
          if (mesh) meshRefs.current[index] = mesh;
        };

        return (
          <mesh
            key={`gesture-target-${system.name}`}
            ref={refCallback}
            position={system.position}
            userData={{ systemName: system.name }}
          >
            <sphereGeometry args={[0.82, 16, 16]} />
            <meshBasicMaterial
              transparent
              opacity={0}
              depthWrite={false}
            />
          </mesh>
        );
      })}
    </group>
  );
}


/* =========================================================
   GALAXY
========================================================= */

function Galaxy({
  selectedSystem,
  setSelectedSystem,
  selectedModule,
  setSelectedModule,
  visionActive,
  visionConfidence,
  personPosition,
  gestureControl,
  gestureTarget,
  onGestureTarget,
  events,
}: {
  selectedSystem:
    | NovaSystem
    | null;

  setSelectedSystem: (
    system:
      | NovaSystem
      | null
  ) => void;

  selectedModule:
    | NovaSystem["modules"][number]
    | null;

  setSelectedModule: (
    module:
      | NovaSystem["modules"][number]
      | null
  ) => void;

  visionActive: boolean;

  visionConfidence: number;

  personPosition: {
    x: number;
    y: number;
  } | null;

  gestureControl: {
    x: number;
    y: number;
    zoom: number;
    gesture: string;
  } | null;

  gestureTarget: NovaSystem | null;

  onGestureTarget: (system: NovaSystem | null) => void;

  events: NovaEvent[];
}) {

  /*
    Vision camera control is enabled
    only when the camera actually
    knows where a person is.
  */

  const visionControlEnabled =
    gestureControl !== null ||
    personPosition !== null;


  return (
    <>

      <ambientLight
        intensity={0.12}
      />


      <Stars
        radius={80}
        depth={50}
        count={5000}
        factor={4}
        saturation={0}
        fade
        speed={0.5}
      />


      <CameraController
        selectedSystem={
          selectedSystem
        }

        selectedModule={
          selectedModule
        }

        personPosition={
          personPosition
        }

        gestureControl={
          gestureControl
        }

        visionControlEnabled={
          visionControlEnabled
        }
      />


      {!selectedSystem && !selectedModule && (
        <GestureSelectionLayer
          systems={novaSystems}
          gestureControl={gestureControl}
          onTarget={onGestureTarget}
          onSelect={(system) => {
            setSelectedSystem(system);
            setSelectedModule(null);
          }}
        />
      )}


      {!selectedSystem && (

        <>

          <Core />

          {novaSystems.map(
            (system) => (

              <Planet
                key={
                  system.name
                }

                system={
                  system
                }

                selected={
                  gestureTarget?.name === system.name
                }

                onClick={() => {

                  setSelectedSystem(
                    system
                  );

                  setSelectedModule(
                    null
                  );

                }}

                active={
                  system.name ===
                  "VISION"
                    ? visionActive
                    : false
                }

                activity={
                  system.name ===
                  "VISION"
                    ? visionConfidence
                    : 0
                }

                personPosition={
                  system.name ===
                  "VISION"
                    ? personPosition
                    : null
                }

              />

            )
          )}

        </>

      )}


      {selectedSystem &&
        !selectedModule && (

          <FloatingModules
            system={
              selectedSystem
            }

            onModuleClick={(
              module
            ) =>
              setSelectedModule(
                module
              )
            }
          />

        )}


      {selectedSystem &&
        selectedModule && (

          <ComponentUniverse
            module={
              selectedModule
            }
          />

        )}


      <LiveEventParticles
        events={
          events
        }
      />


      <OrbitControls
        enablePan={false}
        enableDamping
        dampingFactor={0.08}
        minDistance={3}
        maxDistance={18}
        enabled={
          !visionControlEnabled
        }
      />

    </>
  );
}


/* =========================================================
   APP
========================================================= */

export default function App() {

  const [
    selectedSystem,
    setSelectedSystem,
  ] = useState<
    NovaSystem | null
  >(null);


  const [
    selectedModule,
    setSelectedModule,
  ] = useState<
    NovaSystem["modules"][number] | null
  >(null);


  const [
    events,
    setEvents,
  ] = useState<
    NovaEvent[]
  >([]);


  const [
    visionActive,
    setVisionActive,
  ] = useState(false);


  const [
    visionConfidence,
    setVisionConfidence,
  ] = useState(0);


  const [
    personPosition,
    setPersonPosition,
  ] = useState<{
    x: number;
    y: number;
  } | null>(null);


  const [
    latestObservation,
    setLatestObservation,
  ] = useState<
    NovaEvent["observation"] | null
  >(null);


  const [
    visionStatus,
    setVisionStatus,
  ] = useState(
    "INITIALIZING"
  );


  /* =====================================================
     LIVE CAMERA PREVIEW + VISION STREAM
  ===================================================== */

  const cameraVideoRef =
    useRef<HTMLVideoElement | null>(null);

  const [cameraActive, setCameraActive] =
    useState(false);

  const [cameraError, setCameraError] =
    useState("");

  const [gestureControl, setGestureControl] =
    useState<{
      x: number;
      y: number;
      zoom: number;
      gesture: string;
    } | null>(null);

  const [gestureTarget, setGestureTarget] =
    useState<NovaSystem | null>(null);

  const gestureRecognizerRef =
    useRef<GestureRecognizer | null>(null);

  const lastGestureFrameRef =
    useRef(0);

  const lastGestureRef =
    useRef("");

  useEffect(() => {

    let stream: MediaStream | null = null;
    let cancelled = false;
    let frameTimer: number | null = null;

    async function startCamera() {

      try {

        const visionFileset =
          await FilesetResolver.forVisionTasks(
            "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.22/wasm"
          );

        gestureRecognizerRef.current =
          await GestureRecognizer.createFromOptions(
            visionFileset,
            {
              baseOptions: {
                modelAssetPath:
                  "https://storage.googleapis.com/mediapipe-models/gesture_recognizer/gesture_recognizer/float16/1/gesture_recognizer.task",
                delegate: "GPU",
              },
              runningMode: "VIDEO",
              numHands: 2,
              minHandDetectionConfidence: 0.55,
              minHandPresenceConfidence: 0.55,
              minTrackingConfidence: 0.55,
            }
          );

      } catch (gestureError) {

        console.error(
          "NOVA gesture engine failed:",
          gestureError
        );

        gestureRecognizerRef.current = null;
      }

      try {

        if (!navigator.mediaDevices?.getUserMedia) {
          throw new Error(
            "Camera access is not supported by this browser."
          );
        }

        stream = await navigator.mediaDevices.getUserMedia({
          video: {
            facingMode: "user",
            width: { ideal: 640 },
            height: { ideal: 360 },
            frameRate: { ideal: 10 },
          },
          audio: false,
        });

        if (cancelled) {
          stream.getTracks().forEach((track) => track.stop());
          return;
        }

        if (cameraVideoRef.current) {
          cameraVideoRef.current.srcObject = stream;
          await cameraVideoRef.current.play().catch(() => {});
        }

        setCameraActive(true);
        setCameraError("");

        const canvas = document.createElement("canvas");
        const context = canvas.getContext("2d");

        frameTimer = window.setInterval(() => {

          const video = cameraVideoRef.current;

          if (
            !video ||
            !context ||
            video.readyState < 2 ||
            video.videoWidth === 0
          ) {
            return;
          }

          const sourceWidth = video.videoWidth;
          const sourceHeight = video.videoHeight;
          const maxWidth = 640;
          const scale = Math.min(1, maxWidth / sourceWidth);

          canvas.width = Math.max(1, Math.round(sourceWidth * scale));
          canvas.height = Math.max(1, Math.round(sourceHeight * scale));

          context.drawImage(
            video,
            0,
            0,
            canvas.width,
            canvas.height
          );

          /* =========================================
             HAND GESTURE CONTROL
          ========================================= */

          const recognizer =
            gestureRecognizerRef.current;

          if (
            recognizer &&
            performance.now() - lastGestureFrameRef.current > 90
          ) {

            lastGestureFrameRef.current =
              performance.now();

            try {

              const result =
                recognizer.recognizeForVideo(
                  video,
                  performance.now()
                );

              const landmarks =
                result.landmarks?.[0];

              if (landmarks?.[8]) {

                const indexFinger = landmarks[8];
                const thumb = landmarks[4];

                const pinchDistance = Math.hypot(
                  indexFinger.x - thumb.x,
                  indexFinger.y - thumb.y
                );

                const detectedGesture =
                  result.gestures?.[0]?.[0]?.categoryName ||
                  "";

                const pinch =
                  pinchDistance < 0.075;

                const zoom = THREE.MathUtils.clamp(
                  (0.16 - pinchDistance) * 5.0,
                  0,
                  1
                );

                if (
                  pinch ||
                  detectedGesture === "Open_Palm" ||
                  detectedGesture === "Pointing_Up" ||
                  detectedGesture === "Victory"
                ) {

                  const gestureName = pinch
                    ? "PINCH / ZOOM"
                    : detectedGesture === "Open_Palm"
                      ? "OPEN PALM / MOVE"
                      : detectedGesture === "Pointing_Up"
                        ? "POINT / MOVE"
                        : "VICTORY";

                  setGestureControl({
                    x: indexFinger.x,
                    y: indexFinger.y,
                    zoom,
                    gesture: gestureName,
                  });

                  lastGestureRef.current = gestureName;

                } else if (
                  detectedGesture === "Closed_Fist"
                ) {

                  setGestureControl(null);
                  lastGestureRef.current = "FIST / STOP";

                }

              } else {

                setGestureControl(null);

              }

            } catch (gestureError) {

              console.error(
                "NOVA gesture frame error:",
                gestureError
              );

            }
          }

          const frame = canvas.toDataURL(
            "image/jpeg",
            0.55
          );

          sendCameraFrame(frame);

        }, 200);

      } catch (error) {

        console.error(
          "NOVA camera preview error:",
          error
        );

        setCameraActive(false);

        setCameraError(
          "Camera permission denied or camera unavailable"
        );
      }
    }

    startCamera();

    return () => {

      cancelled = true;

      if (frameTimer !== null) {
        window.clearInterval(frameTimer);
        frameTimer = null;
      }

      if (stream) {
        stream.getTracks().forEach((track) => track.stop());
        stream = null;
      }

      if (cameraVideoRef.current) {
        cameraVideoRef.current.srcObject = null;
      }

      if (gestureRecognizerRef.current) {
        gestureRecognizerRef.current.close();
        gestureRecognizerRef.current = null;
      }

      setGestureControl(null);
    };

  }, []);


  /* =====================================================
     EVENT BUS
  ===================================================== */

  useEffect(() => {

    connectToBackend();


    const unsubscribe =
      subscribeToEvents(
        (event) => {

          setEvents(
            (previous) => [
              event,
              ...previous,
            ].slice(
              0,
              8
            )
          );


          /* =============================================
             VISION
          ============================================= */

          if (
            event.source ===
            "VISION"
          ) {


            if (
              event.type ===
              "CAMERA_CONNECTED"
            ) {

              setVisionStatus(
                "CAMERA ACTIVE"
              );

            }


            /* =========================================
               PERSON DETECTED
            ========================================= */

            if (
              event.type ===
              "PERSON_DETECTED"
            ) {

              const observation =
                event.observation;


              const confidence =
                observation
                  ?.confidence ??
                0;


              const position =
                observation
                  ?.position ??
                null;


              setVisionActive(
                true
              );


              setVisionConfidence(
                confidence
              );


              setPersonPosition(
                position
              );


              setLatestObservation(
                observation ??
                  null
              );


              setVisionStatus(
                "PERSON TRACKING"
              );


              window.setTimeout(
                () => {

                  setVisionActive(
                    false
                  );

                  setVisionStatus(
                    "CAMERA ACTIVE"
                  );

                },
                1200
              );

            }


            /* =========================================
               MOTION
            ========================================= */

            if (
              event.type ===
              "MOTION_DETECTED"
            ) {

              const observation =
                event.observation;


              const confidence =
                observation
                  ?.confidence ??
                0;


              setVisionActive(
                true
              );


              setVisionConfidence(
                confidence
              );


              setLatestObservation(
                observation ??
                  null
              );


              setVisionStatus(
                "MOTION DETECTED"
              );


              window.setTimeout(
                () => {

                  setVisionActive(
                    false
                  );

                  setVisionStatus(
                    "CAMERA ACTIVE"
                  );

                },
                1800
              );

            }


            /* =========================================
               CAMERA ERROR
            ========================================= */

            if (
              event.type ===
              "CAMERA_ERROR"
            ) {

              setVisionActive(
                false
              );

              setVisionConfidence(
                0
              );

              setPersonPosition(
                null
              );

              setVisionStatus(
                "CAMERA ERROR"
              );

            }

          }

        }
      );


    return unsubscribe;

  }, []);


  /* =====================================================
     BACK
  ===================================================== */

  const goBack =
    () => {

      if (
        selectedModule
      ) {

        setSelectedModule(
          null
        );

        return;
      }


      if (
        selectedSystem
      ) {

        setSelectedSystem(
          null
        );

        return;
      }

    };


  return (

    <div className="nova">


      {/* =================================================
          TOP BAR
      ================================================= */}

      <div className="topbar">

        <div className="logo">
          NOVA
        </div>


        <div className="status">

          <span
            className="status-dot"
          />

          SYSTEM ONLINE

        </div>

      </div>


      {/* =================================================
          EVENT PANEL
      ================================================= */}

      <div className="event-panel">

        <div
          className="event-header"
        >

          <span>
            LIVE EVENTS
          </span>

          <span className="live">
            ● LIVE
          </span>

        </div>


        <div className="event-list">

          {events.length ===
          0 ? (

            <div className="event-empty">
              WAITING FOR EVENTS...
            </div>

          ) : (

            events.map(
              (event) => (

                <div
                  className="event-item"
                  key={
                    event.id
                  }
                >

                  <div
                    className="event-dot"
                    style={{
                      background:
                        event.color,

                      boxShadow:
                        `0 0 8px ${event.color}`,
                    }}
                  />


                  <div
                    className="event-content"
                  >

                    <div
                      className="event-type"
                    >
                      {
                        event.type
                      }
                    </div>


                    <div
                      className="event-message"
                    >
                      {
                        event.message
                      }
                    </div>


                    <div
                      className="event-meta"
                    >
                      {
                        event.source
                      }

                      {" · "}

                      {
                        event.timestamp
                      }
                    </div>

                  </div>

                </div>

              )
            )

          )}

        </div>

      </div>


      {/* =================================================
          SYSTEM INFO
      ================================================= */}

      {selectedSystem && (

        <div className="system-info">

          <div className="system-title">
            {
              selectedSystem.name
            }
          </div>


          <div className="system-description">
            {
              selectedSystem.description
            }
          </div>


          <div className="module-count">
            {
              selectedSystem
                .modules
                .length
            }

            {" MODULES"}
          </div>

        </div>

      )}


      {/* =================================================
          MODULE INFO
      ================================================= */}

      {selectedModule && (

        <div className="module-info">

          <div className="module-title">
            {
              selectedModule.name
            }
          </div>


          <div className="module-description">
            {
              selectedModule.description
            }
          </div>


          <div className="component-count">
            {
              selectedModule
                .components
                .length
            }

            {" COMPONENTS"}
          </div>

        </div>

      )}


      {/* =================================================
          VISION STATUS
      ================================================= */}

      {!selectedSystem && (

        <div
          className="system-info"
          style={{
            top: "80px",
            right: "28px",
          }}
        >

          <div
            className="system-title"
            style={{
              color:
                visionActive
                  ? "#7dd3fc"
                  : "white",
            }}
          >
            VISION
          </div>


          <div className="system-description">
            {
              visionStatus
            }
          </div>


          {latestObservation && (

            <>

              <div className="module-count">

                CONFIDENCE{" "}

                {
                  Math.round(
                    visionConfidence *
                      100
                  )
                }

                %

              </div>


              {latestObservation
                .person && (

                <div
                  className="module-count"
                  style={{
                    marginTop:
                      "7px",
                  }}
                >

                  PERSONS{" "}

                  {
                    latestObservation
                      .person_count ??
                    1
                  }

                </div>

              )}


              {personPosition && (

                <div
                  className="module-count"
                  style={{
                    marginTop:
                      "7px",
                  }}
                >

                  TRACK X{" "}

                  {
                    Math.round(
                      personPosition.x *
                        100
                    )
                  }

                  %

                  {" · "}

                  TRACK Y{" "}

                  {
                    Math.round(
                      personPosition.y *
                        100
                    )
                  }

                  %

                </div>

              )}


              {latestObservation
                .motion_area !==
                undefined && (

                <div
                  className="module-count"
                  style={{
                    marginTop:
                      "7px",
                  }}
                >

                  MOTION AREA{" "}

                  {
                    latestObservation
                      .motion_area
                  }

                </div>

              )}

            </>

          )}

        </div>

      )}


      {/* =================================================
          GESTURE TARGET INDICATOR
      ================================================= */}

      {gestureTarget && (

        <div
          style={{
            position: "absolute",
            left: "50%",
            top: "118px",
            transform: "translateX(-50%)",
            padding: "7px 13px",
            borderRadius: "10px",
            border: `1px solid ${gestureTarget.color}55`,
            background: "rgba(5,10,20,0.66)",
            backdropFilter: "blur(14px)",
            color: gestureTarget.color,
            fontSize: "9px",
            letterSpacing: "1.4px",
            pointerEvents: "none",
            zIndex: 20,
          }}
        >
          TARGET · {gestureTarget.name}
        </div>

      )}

      {/* =================================================
          GESTURE CONTROL INDICATOR
      ================================================= */}

      {gestureControl && (

        <div
          style={{
            position: "absolute",
            left: "50%",
            top: "82px",
            transform: "translateX(-50%)",
            padding: "8px 14px",
            borderRadius: "10px",
            border: "1px solid rgba(125,211,252,0.28)",
            background: "rgba(5,10,20,0.62)",
            backdropFilter: "blur(14px)",
            color: "#7dd3fc",
            fontSize: "9px",
            letterSpacing: "1.4px",
            pointerEvents: "none",
            zIndex: 20,
          }}
        >
          HAND CONTROL · {gestureControl.gesture}
        </div>

      )}

      {/* =================================================
          CAMERA CONTROL INDICATOR
      ================================================= */}

      {personPosition &&
        !selectedSystem && (

        <div
          style={{
            position:
              "absolute",

            left: "50%",

            top: "82px",

            transform:
              "translateX(-50%)",

            padding:
              "7px 12px",

            borderRadius:
              "10px",

            border:
              "1px solid rgba(125,211,252,0.22)",

            background:
              "rgba(5,10,20,0.5)",

            backdropFilter:
              "blur(14px)",

            color:
              "#7dd3fc",

            fontSize:
              "8px",

            letterSpacing:
              "1.5px",

            pointerEvents:
              "none",
          }}
        >
          VISION CAMERA CONTROL ACTIVE
        </div>

      )}


      {/* =================================================
          BACK
      ================================================= */}

      {(selectedSystem ||
        selectedModule) && (

        <button
          className="back-button"
          onClick={
            goBack
          }
        >
          ← BACK
        </button>

      )}


      {/* =================================================
          LIVE CAMERA
      ================================================= */}

      <div className="vision-camera-panel">

        <div className="vision-camera-header">

          <div className="vision-camera-title">
            <span className="vision-camera-icon">◉</span>
            VISION
          </div>

          <div
            className={
              cameraActive
                ? "vision-camera-live"
                : "vision-camera-offline"
            }
          >
            <span className="vision-camera-dot" />
            {cameraActive ? "LIVE" : "OFFLINE"}
          </div>

        </div>

        <div className="vision-camera-frame">

          <video
            ref={cameraVideoRef}
            className="vision-camera-video"
            autoPlay
            muted
            playsInline
          />

          {!cameraActive && (
            <div className="vision-camera-placeholder">

              <div className="vision-camera-placeholder-icon">
                ◉
              </div>

              <div className="vision-camera-placeholder-title">
                CAMERA UNAVAILABLE
              </div>

              <div className="vision-camera-placeholder-text">
                {
                  cameraError ||
                  "Waiting for camera permission..."
                }
              </div>

            </div>
          )}

          {cameraActive && (
            <>
              <div className="vision-scan-line" />

              <div className="vision-camera-corner top-left" />
              <div className="vision-camera-corner top-right" />
              <div className="vision-camera-corner bottom-left" />
              <div className="vision-camera-corner bottom-right" />

              {personPosition && (
                <div
                  className="vision-person-marker"
                  style={{
                    left: `${personPosition.x * 100}%`,
                    top: `${personPosition.y * 100}%`,
                  }}
                >
                  <span />
                </div>
              )}
            </>
          )}

        </div>

        <div className="vision-camera-footer">

          <span>
            {visionStatus}
          </span>

          <span>
            {gestureControl
              ? gestureControl.gesture
              : latestObservation?.person
                ? `${latestObservation.person_count ?? 1} PERSON`
                : "VISION READY"}
          </span>

        </div>

      </div>


      {/* =================================================
          3D GALAXY
      ================================================= */}

      <Canvas
        camera={{
          position: [
            0,
            0,
            8,
          ],
          fov: 55,
        }}
      >

        <Galaxy

          selectedSystem={
            selectedSystem
          }

          setSelectedSystem={
            setSelectedSystem
          }

          selectedModule={
            selectedModule
          }

          setSelectedModule={
            setSelectedModule
          }

          visionActive={
            visionActive
          }

          visionConfidence={
            visionConfidence
          }

          personPosition={
            personPosition
          }

          gestureControl={
            gestureControl
          }

          gestureTarget={
            gestureTarget
          }

          onGestureTarget={
            setGestureTarget
          }

          events={
            events
          }

        />

      </Canvas>


      {/* =================================================
          COMMAND
      ================================================= */}

      <div className="command">

        <span>
          ⌘
        </span>

        <input
          placeholder="Ask NOVA anything..."
        />

        <span>
          ↵
        </span>

      </div>

    </div>
  );
}