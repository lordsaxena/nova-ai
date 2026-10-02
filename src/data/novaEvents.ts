export type NovaObservation = {
  motion?: boolean;
  confidence?: number;
  motion_area?: number;

  person?: boolean;
  person_count?: number;

  position?: {
    x: number;
    y: number;
  };

  frame?: {
    width: number;
    height: number;
  };

  region?: {
    x: number;
    y: number;
    width: number;
    height: number;
  };

  camera?: boolean;
  vision?: boolean;
};

export type NovaEvent = {
  id: number;
  type: string;
  source: string;
  message: string;
  timestamp: string;
  color: string;
  observation?: NovaObservation;
};

export const initialEvents: NovaEvent[] = [
  {
    id: 1,
    type: "SYSTEM_ONLINE",
    source: "NOVA CORE",
    message: "NOVA systems initialized",
    timestamp: new Date().toLocaleTimeString(),
    color: "#7dd3fc",
  },
  {
    id: 2,
    type: "CAMERA_CONNECTED",
    source: "VISION",
    message: "Visual input connected",
    timestamp: new Date().toLocaleTimeString(),
    color: "#67e8f9",
  },
  {
    id: 3,
    type: "MEMORY_READY",
    source: "MEMORY",
    message: "Memory system ready",
    timestamp: new Date().toLocaleTimeString(),
    color: "#c084fc",
  },
];