export type NovaComponent = {
  name: string;
  description: string;
};

export type NovaModule = {
  name: string;
  description: string;
  components: NovaComponent[];
};

export type NovaSystem = {
  name: string;
  color: string;
  position: [number, number, number];
  description: string;
  modules: NovaModule[];
};

export const novaSystems: NovaSystem[] = [
  {
    name: "VISION",
    color: "#7dd3fc",
    position: [-4, 1, 0],
    description: "NOVA's visual perception system.",

    modules: [
      {
        name: "CAMERA",
        description: "Camera input and visual stream.",

        components: [
          {
            name: "CAMERA INPUT",
            description: "Receives visual frames.",
          },
          {
            name: "FRAME PROCESSOR",
            description: "Processes incoming frames.",
          },
          {
            name: "VIDEO STREAM",
            description: "Maintains the live video stream.",
          },
        ],
      },

      {
        name: "MOTION DETECTION",
        description: "Detects movement in the environment.",

        components: [
          {
            name: "MOTION SENSOR",
            description: "Detects changes between frames.",
          },
          {
            name: "MOVEMENT TRACKER",
            description: "Tracks moving objects.",
          },
          {
            name: "ACTIVITY ANALYZER",
            description: "Analyzes movement patterns.",
          },
        ],
      },

      {
        name: "OBJECT DETECTION",
        description: "Identifies objects in visual input.",

        components: [
          {
            name: "PERSON DETECTOR",
            description: "Detects people.",
          },
          {
            name: "OBJECT DETECTOR",
            description: "Identifies visible objects.",
          },
          {
            name: "PHONE DETECTOR",
            description: "Detects mobile devices.",
          },
          {
            name: "TRACKING ENGINE",
            description: "Tracks detected objects.",
          },
        ],
      },

      {
        name: "PERSON DETECTION",
        description: "Detects people in the environment.",

        components: [
          {
            name: "PERSON MODEL",
            description: "Detects human figures.",
          },
          {
            name: "POSE ENGINE",
            description: "Analyzes body position.",
          },
          {
            name: "ACTIVITY ENGINE",
            description: "Analyzes visible activity.",
          },
        ],
      },

      {
        name: "GESTURE DETECTION",
        description: "Understands visual gestures.",

        components: [
          {
            name: "HAND TRACKER",
            description: "Tracks hand movement.",
          },
          {
            name: "GESTURE MODEL",
            description: "Recognizes gestures.",
          },
          {
            name: "GESTURE PARSER",
            description: "Converts gestures into commands.",
          },
        ],
      },
    ],
  },

  {
    name: "MEMORY",
    color: "#c084fc",
    position: [4, 1, -1],
    description: "NOVA's memory and context system.",

    modules: [
      {
        name: "SHORT TERM MEMORY",
        description: "Stores current conversation context.",
        components: [
          {
            name: "CONTEXT BUFFER",
            description: "Stores active context.",
          },
          {
            name: "SESSION MEMORY",
            description: "Stores the current session.",
          },
        ],
      },

      {
        name: "LONG TERM MEMORY",
        description: "Stores persistent useful information.",
        components: [
          {
            name: "MEMORY STORE",
            description: "Stores persistent information.",
          },
          {
            name: "MEMORY RETRIEVER",
            description: "Retrieves relevant memories.",
          },
        ],
      },

      {
        name: "KNOWLEDGE GRAPH",
        description: "Connects information and relationships.",
        components: [
          {
            name: "ENTITY GRAPH",
            description: "Stores entities.",
          },
          {
            name: "RELATION ENGINE",
            description: "Connects related entities.",
          },
        ],
      },
    ],
  },

  {
    name: "VOICE",
    color: "#67e8f9",
    position: [-3, -2, -1],
    description: "NOVA's speech interaction system.",

    modules: [
      {
        name: "SPEECH RECOGNITION",
        description: "Converts speech into text.",
        components: [
          {
            name: "AUDIO INPUT",
            description: "Receives microphone audio.",
          },
          {
            name: "SPEECH ENGINE",
            description: "Converts speech to text.",
          },
        ],
      },

      {
        name: "COMMAND PARSER",
        description: "Understands user commands.",
        components: [
          {
            name: "INTENT ENGINE",
            description: "Identifies user intent.",
          },
          {
            name: "COMMAND ROUTER",
            description: "Routes commands to agents.",
          },
        ],
      },

      {
        name: "TEXT TO SPEECH",
        description: "Produces spoken responses.",
        components: [
          {
            name: "VOICE ENGINE",
            description: "Generates speech.",
          },
          {
            name: "AUDIO OUTPUT",
            description: "Plays generated speech.",
          },
        ],
      },
    ],
  },

  {
    name: "TRACE",
    color: "#f87171",
    position: [0, 3, -2],
    description: "Security and event intelligence.",

    modules: [
      {
        name: "EVENT GRAPH",
        description: "Maps system events and relationships.",
        components: [
          {
            name: "EVENT NODE",
            description: "Represents system events.",
          },
          {
            name: "RELATION ENGINE",
            description: "Connects related events.",
          },
        ],
      },

      {
        name: "ANOMALY DETECTION",
        description: "Identifies unusual system activity.",
        components: [
          {
            name: "BEHAVIOR ANALYZER",
            description: "Analyzes system behavior.",
          },
          {
            name: "ANOMALY ENGINE",
            description: "Detects unusual patterns.",
          },
        ],
      },

      {
        name: "SECURITY ENGINE",
        description: "Analyzes security-related events.",
        components: [
          {
            name: "EVENT MONITOR",
            description: "Monitors system events.",
          },
          {
            name: "THREAT ANALYZER",
            description: "Analyzes suspicious activity.",
          },
        ],
      },
    ],
  },

  {
    name: "AGENTS",
    color: "#facc15",
    position: [3, -2, 0],
    description: "NOVA's specialized AI agents.",

    modules: [
      {
        name: "RESEARCH AGENT",
        description: "Researches information.",
        components: [
          {
            name: "SEARCH ENGINE",
            description: "Finds relevant information.",
          },
          {
            name: "SOURCE ANALYZER",
            description: "Analyzes sources.",
          },
        ],
      },

      {
        name: "CODING AGENT",
        description: "Assists with software development.",
        components: [
          {
            name: "CODE ANALYZER",
            description: "Analyzes source code.",
          },
          {
            name: "CODE GENERATOR",
            description: "Generates code.",
          },
        ],
      },

      {
        name: "ANALYSIS AGENT",
        description: "Analyzes information and data.",
        components: [
          {
            name: "DATA ANALYZER",
            description: "Analyzes datasets.",
          },
          {
            name: "REASONING ENGINE",
            description: "Performs structured reasoning.",
          },
        ],
      },
    ],
  },

  {
    name: "KNOWLEDGE",
    color: "#86efac",
    position: [0, -4, -2],
    description: "NOVA's knowledge universe.",

    modules: [
      {
        name: "DOCUMENTS",
        description: "Understands connected documents.",
        components: [
          {
            name: "DOCUMENT PARSER",
            description: "Reads document content.",
          },
          {
            name: "DOCUMENT INDEX",
            description: "Indexes document information.",
          },
        ],
      },

      {
        name: "WEB KNOWLEDGE",
        description: "Organizes researched information.",
        components: [
          {
            name: "WEB RESEARCH",
            description: "Collects web information.",
          },
          {
            name: "SOURCE INDEX",
            description: "Organizes research sources.",
          },
        ],
      },

      {
        name: "KNOWLEDGE GRAPH",
        description: "Connects concepts and entities.",
        components: [
          {
            name: "ENTITY STORE",
            description: "Stores entities.",
          },
          {
            name: "RELATION GRAPH",
            description: "Connects related concepts.",
          },
        ],
      },
    ],
  },
];