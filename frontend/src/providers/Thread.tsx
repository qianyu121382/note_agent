import { validate } from "uuid";
import { getApiKey } from "@/lib/api-key";
import { Thread } from "@langchain/langgraph-sdk";
import { useQueryState } from "nuqs";
import {
  createContext,
  useContext,
  ReactNode,
  useCallback,
  useState,
  Dispatch,
  SetStateAction,
} from "react";
import { createClient } from "./client";

export interface ThreadHistoryItem {
  thread_id: string;
  updated_at?: string | null;
  preview?: string;
  values?: {
    messages?: Array<{
      id?: string;
      type: string;
      content: unknown;
    }>;
  };
}

interface ThreadContextType {
  getThreads: () => Promise<ThreadHistoryItem[]>;
  threads: ThreadHistoryItem[];
  setThreads: Dispatch<SetStateAction<ThreadHistoryItem[]>>;
  threadsLoading: boolean;
  setThreadsLoading: Dispatch<SetStateAction<boolean>>;
}

const ThreadContext = createContext<ThreadContextType | undefined>(undefined);

function getThreadSearchMetadata(
  assistantId: string,
): { graph_id: string } | { assistant_id: string } {
  if (validate(assistantId)) {
    return { assistant_id: assistantId };
  } else {
    return { graph_id: assistantId };
  }
}

function mergeThreads(
  localThreads: ThreadHistoryItem[],
  remoteThreads: Thread[],
): ThreadHistoryItem[] {
  const merged = new Map<string, ThreadHistoryItem>();

  for (const thread of localThreads) {
    merged.set(thread.thread_id, thread);
  }

  for (const thread of remoteThreads) {
    const existing = merged.get(thread.thread_id);
    merged.set(thread.thread_id, {
      thread_id: thread.thread_id,
      updated_at: existing?.updated_at ?? null,
      preview: existing?.preview,
      values: {
        messages:
          existing?.values?.messages ??
          (((thread.values as { messages?: Array<{ id?: string; type: string; content: unknown }> } | undefined)?.messages) ?? []),
      },
    });
  }

  return Array.from(merged.values()).sort((a, b) =>
    (b.updated_at ?? "").localeCompare(a.updated_at ?? ""),
  );
}

export function ThreadProvider({ children }: { children: ReactNode }) {
  const envApiUrl: string | undefined = process.env.NEXT_PUBLIC_API_URL;
  const envAssistantId: string | undefined =
    process.env.NEXT_PUBLIC_ASSISTANT_ID;
  const envAuthScheme: string | undefined = process.env.NEXT_PUBLIC_AUTH_SCHEME;

  const [apiUrl] = useQueryState("apiUrl", {
    defaultValue: envApiUrl || "",
  });
  const [assistantId] = useQueryState("assistantId");
  const [authScheme] = useQueryState("authScheme", {
    defaultValue: envAuthScheme || "",
  });
  const [threads, setThreads] = useState<ThreadHistoryItem[]>([]);
  const [threadsLoading, setThreadsLoading] = useState(false);

  const getThreads = useCallback(async (): Promise<ThreadHistoryItem[]> => {
    const resolvedAssistantId = assistantId || envAssistantId;

    const localResponse = await fetch("/api/session-history", {
      cache: "no-store",
    });
    const localData = localResponse.ok
      ? ((await localResponse.json()) as { threads?: ThreadHistoryItem[] })
      : { threads: [] };
    const localThreads = localData.threads ?? [];

    if (!apiUrl || !resolvedAssistantId) return localThreads;

    try {
      const client = createClient(
        apiUrl,
        getApiKey() ?? undefined,
        authScheme || undefined,
      );

      const remoteThreads = await client.threads.search({
        metadata: {
          ...getThreadSearchMetadata(resolvedAssistantId),
        },
        limit: 100,
      });

      return mergeThreads(localThreads, remoteThreads);
    } catch {
      return localThreads;
    }
  }, [apiUrl, assistantId, authScheme, envAssistantId]);

  const value = {
    getThreads,
    threads,
    setThreads,
    threadsLoading,
    setThreadsLoading,
  };

  return (
    <ThreadContext.Provider value={value}>{children}</ThreadContext.Provider>
  );
}

export function useThreads() {
  const context = useContext(ThreadContext);
  if (context === undefined) {
    throw new Error("useThreads must be used within a ThreadProvider");
  }
  return context;
}

