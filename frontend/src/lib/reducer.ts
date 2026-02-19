import { AppState, ChatMessage, GitCommit, ToolGroup } from "./types";

export type AppAction =
  | { type: "SET_PROJECT"; project: AppState["project"] }
  | { type: "ADD_USER_MESSAGE"; content: string }
  | { type: "START_ASSISTANT_MESSAGE" }
  | { type: "APPEND_ASSISTANT_TOKEN"; token: string }
  | { type: "END_ASSISTANT_MESSAGE" }
  | { type: "ADD_TOOL_CALL"; tool: string; args: Record<string, unknown> }
  | { type: "ADD_TOOL_RESULT"; tool: string; result: string }
  | { type: "SET_FILES"; files: string[] }
  | { type: "SET_COMMITS"; commits: GitCommit[] }
  | { type: "SET_AGENT_WORKING"; working: boolean }
  | { type: "BUILD_COMPLETE"; swaggerUrl: string; apiUrl: string }
  | { type: "ADD_ERROR"; message: string }
  | { type: "TOGGLE_TOOL_DETAILS" }
  | { type: "AGENT_STOPPED" }
  | { type: "STATE_UPDATE"; state: string; swaggerUrl: string; apiUrl: string }
  | { type: "SELECT_FILE"; path: string | null }
  | { type: "ASK_USER"; question: string; options: string[] }
  | { type: "MARK_ANSWERED"; messageId: string };

let msgCounter = 0;
function nextId() {
  return `msg-${++msgCounter}`;
}

function getToolSummary(tool: string, args: Record<string, unknown>): string {
  const path = args?.path as string | undefined;
  const cmd = args?.command as string | undefined;
  switch (tool) {
    case "write_file":
      return path ? `Writing ${path}` : "Writing file";
    case "edit_file":
      return path ? `Editing ${path}` : "Editing file";
    case "read_file":
      return path ? `Reading ${path}` : "Reading file";
    case "list_directory":
      return path ? `Listing ${path}` : "Listing directory";
    case "run_command":
      return cmd ? `Running: ${cmd.length > 40 ? cmd.slice(0, 40) + "..." : cmd}` : "Running command";
    case "git_commit":
      return "Committing changes";
    case "git_log":
      return "Checking git history";
    case "docker_compose_up":
      return "Building and starting containers";
    case "docker_compose_down":
      return "Stopping containers";
    case "docker_status":
      return "Checking container status";
    case "docker_logs":
      return "Reading container logs";
    case "scaffold_project":
      return "Scaffolding project";
    case "build_complete":
      return "Finalizing build";
    default:
      return tool;
  }
}

export const initialState: AppState = {
  project: null,
  messages: [],
  files: [],
  commits: [],
  isAgentWorking: false,
  swaggerUrl: null,
  apiUrl: null,
  showToolDetails: false,
  selectedFile: null,
};

function getOrCreateActiveToolGroup(messages: ChatMessage[]): { msgs: ChatMessage[]; group: ToolGroup; index: number } {
  const msgs = [...messages];
  // Find the last tool_group message that is still active
  for (let i = msgs.length - 1; i >= 0; i--) {
    if (msgs[i].role === "tool_group" && msgs[i].toolGroup?.isActive) {
      return { msgs, group: { ...msgs[i].toolGroup! }, index: i };
    }
  }
  // Create a new one
  const group: ToolGroup = { id: nextId(), steps: [], isActive: true };
  const msg: ChatMessage = { id: group.id, role: "tool_group", content: "", toolGroup: group };
  msgs.push(msg);
  return { msgs, group, index: msgs.length - 1 };
}

function closeActiveToolGroups(messages: ChatMessage[]): ChatMessage[] {
  return messages.map((m) =>
    m.role === "tool_group" && m.toolGroup?.isActive
      ? { ...m, toolGroup: { ...m.toolGroup, isActive: false } }
      : m
  );
}

export function appReducer(state: AppState, action: AppAction): AppState {
  switch (action.type) {
    case "SET_PROJECT":
      return { ...state, project: action.project };

    case "ADD_USER_MESSAGE":
      return {
        ...state,
        messages: [
          ...state.messages,
          { id: nextId(), role: "user", content: action.content },
        ],
        isAgentWorking: true,
      };

    case "START_ASSISTANT_MESSAGE": {
      const msgs = closeActiveToolGroups(state.messages);
      return {
        ...state,
        messages: [
          ...msgs,
          { id: nextId(), role: "assistant", content: "", isStreaming: true },
        ],
      };
    }

    case "APPEND_ASSISTANT_TOKEN": {
      const msgs = [...state.messages];
      const last = msgs[msgs.length - 1];
      if (last && last.role === "assistant" && last.isStreaming) {
        msgs[msgs.length - 1] = { ...last, content: last.content + action.token };
      }
      return { ...state, messages: msgs };
    }

    case "END_ASSISTANT_MESSAGE": {
      const msgs = [...state.messages];
      const last = msgs[msgs.length - 1];
      if (last && last.role === "assistant") {
        msgs[msgs.length - 1] = { ...last, isStreaming: false };
      }
      return { ...state, messages: msgs };
    }

    case "ADD_TOOL_CALL": {
      const { msgs, group, index } = getOrCreateActiveToolGroup(state.messages);
      const updatedGroup = {
        ...group,
        steps: [...group.steps, { tool: action.tool, status: "running" as const, args: action.args }],
      };
      const summary = getToolSummary(action.tool, action.args);
      msgs[index] = { ...msgs[index], toolGroup: updatedGroup, content: summary };
      return { ...state, messages: msgs };
    }

    case "ADD_TOOL_RESULT": {
      const msgs = [...state.messages];
      let autoSelectFile: string | null = null;
      // Find the active tool group and update the matching step
      for (let i = msgs.length - 1; i >= 0; i--) {
        if (msgs[i].role === "tool_group" && msgs[i].toolGroup?.isActive) {
          const group = { ...msgs[i].toolGroup! };
          const steps = [...group.steps];
          for (let j = steps.length - 1; j >= 0; j--) {
            if (steps[j].tool === action.tool && steps[j].status === "running") {
              steps[j] = { ...steps[j], status: "done", result: action.result };
              // Auto-select file on write/edit
              if ((action.tool === "write_file" || action.tool === "edit_file") && steps[j].args?.path) {
                autoSelectFile = steps[j].args!.path as string;
              }
              break;
            }
          }
          // Show the current running step or done count
          const runningStep = steps.find((s) => s.status === "running");
          const summary = runningStep
            ? getToolSummary(runningStep.tool, runningStep.args || {})
            : `${steps.filter((s) => s.status === "done").length} tools executed`;
          msgs[i] = { ...msgs[i], toolGroup: { ...group, steps }, content: summary };
          break;
        }
      }
      return {
        ...state,
        messages: msgs,
        selectedFile: autoSelectFile ?? state.selectedFile,
      };
    }

    case "SET_FILES":
      return { ...state, files: action.files };

    case "SET_COMMITS":
      return { ...state, commits: action.commits };

    case "SET_AGENT_WORKING":
      return { ...state, isAgentWorking: action.working };

    case "BUILD_COMPLETE": {
      const msgs = closeActiveToolGroups(state.messages);
      msgs.push({
        id: nextId(),
        role: "build_summary",
        content: "",
        swaggerUrl: action.swaggerUrl,
        apiUrl: action.apiUrl,
      });
      return {
        ...state,
        messages: msgs,
        swaggerUrl: action.swaggerUrl,
        apiUrl: action.apiUrl,
        isAgentWorking: false,
      };
    }

    case "ADD_ERROR":
      return {
        ...state,
        messages: [
          ...state.messages,
          { id: nextId(), role: "assistant", content: `Error: ${action.message}` },
        ],
        isAgentWorking: false,
      };

    case "TOGGLE_TOOL_DETAILS":
      return { ...state, showToolDetails: !state.showToolDetails };

    case "AGENT_STOPPED": {
      const msgs = closeActiveToolGroups(state.messages);
      return { ...state, messages: msgs, isAgentWorking: false };
    }

    case "STATE_UPDATE": {
      const project = state.project
        ? { ...state.project, state: action.state, swagger_url: action.swaggerUrl, api_url: action.apiUrl }
        : state.project;
      return {
        ...state,
        project,
        swaggerUrl: action.swaggerUrl || state.swaggerUrl,
        apiUrl: action.apiUrl || state.apiUrl,
      };
    }

    case "SELECT_FILE":
      return { ...state, selectedFile: action.path };

    case "ASK_USER": {
      const msgs = closeActiveToolGroups(state.messages);
      msgs.push({
        id: nextId(),
        role: "ask_user",
        content: action.question,
        options: action.options,
        answered: false,
      });
      return { ...state, messages: msgs, isAgentWorking: false };
    }

    case "MARK_ANSWERED": {
      const msgs = state.messages.map((m) =>
        m.id === action.messageId ? { ...m, answered: true } : m
      );
      return { ...state, messages: msgs };
    }

    default:
      return state;
  }
}
