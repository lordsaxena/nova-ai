import { emitEvent } from "./eventBus";

const eventTypes = [
  {
    type: "MOTION_DETECTED",
    source: "VISION",
    message: "Movement detected",
    color: "#7dd3fc",
  },

  {
    type: "OBJECT_DETECTED",
    source: "OBJECT DETECTION",
    message:
      "Object detected in visual input",
    color: "#67e8f9",
  },

  {
    type: "MEMORY_UPDATED",
    source: "MEMORY",
    message:
      "Memory context updated",
    color: "#c084fc",
  },

  {
    type: "AGENT_ACTIVE",
    source: "AGENTS",
    message:
      "AI agent processing task",
    color: "#facc15",
  },

  {
    type: "THREAT_SCAN",
    source: "TRACE",
    message:
      "Security event analyzed",
    color: "#f87171",
  },

  {
    type: "KNOWLEDGE_UPDATE",
    source: "KNOWLEDGE",
    message:
      "Knowledge graph updated",
    color: "#86efac",
  },
];

export function startEventSimulator() {
  const interval = setInterval(() => {
    const event =
      eventTypes[
        Math.floor(
          Math.random() *
            eventTypes.length
        )
      ];

    emitEvent(event);
  }, 3000);

  return () => {
    clearInterval(interval);
  };
}