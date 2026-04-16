import { Button } from "@/components/ui/button";
import { useThreads, ThreadHistoryItem, ThreadMode } from "@/providers/Thread";
import { useEffect } from "react";

import { getContentString } from "../utils";
import { useQueryState, parseAsBoolean } from "nuqs";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Skeleton } from "@/components/ui/skeleton";
import {
  BookOpen,
  MessageSquarePlus,
  PanelRightOpen,
  PanelRightClose,
} from "lucide-react";
import { useMediaQuery } from "@/hooks/useMediaQuery";

function getModeLabel(mode?: ThreadMode) {
  switch (mode) {
    case "create":
      return "Create";
    case "edit":
      return "Edit";
    case "qa":
      return "QA";
    default:
      return "Idle";
  }
}

function getModeClasses(mode?: ThreadMode) {
  switch (mode) {
    case "create":
      return "bg-emerald-50 text-emerald-700 border-emerald-200";
    case "edit":
      return "bg-amber-50 text-amber-700 border-amber-200";
    case "qa":
      return "bg-sky-50 text-sky-700 border-sky-200";
    default:
      return "bg-slate-50 text-slate-600 border-slate-200";
  }
}

function SidebarActions({ onClose }: { onClose?: () => void }) {
  const [, setThreadId] = useQueryState("threadId");
  const [, setWorkspaceView] = useQueryState("workspaceView", {
    defaultValue: "chat",
  });

  return (
    <div className="flex w-full flex-col gap-2 px-4 pt-2">
      <Button
        className="w-full justify-start rounded-xl"
        onClick={() => {
          setThreadId(null);
          setWorkspaceView("chat");
          onClose?.();
        }}
      >
        <MessageSquarePlus className="mr-2 size-4" />
        新聊天
      </Button>
      <Button
        variant="outline"
        className="w-full justify-start rounded-xl"
        onClick={() => {
          setWorkspaceView("notes");
          onClose?.();
        }}
      >
        <BookOpen className="mr-2 size-4" />
        查看笔记
      </Button>
    </div>
  );
}

function ThreadList({
  threads,
  onThreadClick,
}: {
  threads: ThreadHistoryItem[];
  onThreadClick?: () => void;
}) {
  const [threadId, setThreadId] = useQueryState("threadId");
  const [, setWorkspaceView] = useQueryState("workspaceView", {
    defaultValue: "chat",
  });

  return (
    <div className="flex h-full w-full flex-col items-start justify-start gap-2 overflow-y-scroll px-3 [&::-webkit-scrollbar]:w-1.5 [&::-webkit-scrollbar-thumb]:rounded-full [&::-webkit-scrollbar-thumb]:bg-gray-300 [&::-webkit-scrollbar-track]:bg-transparent">
      {threads.map((t) => {
        let itemText = t.preview || t.thread_id;
        if (
          !t.preview &&
          t.values?.messages &&
          Array.isArray(t.values.messages) &&
          t.values.messages.length > 0
        ) {
          itemText = getContentString(t.values.messages[0].content as any);
        }
        return (
          <div
            key={t.thread_id}
            className="w-full"
          >
            <Button
              variant="ghost"
              className="flex h-auto w-full flex-col items-start justify-start gap-2 rounded-xl px-3 py-3 text-left font-normal"
              onClick={(e) => {
                e.preventDefault();
                setWorkspaceView("chat");
                onThreadClick?.();
                if (t.thread_id !== threadId) {
                  setThreadId(t.thread_id);
                }
              }}
            >
              <div className="flex w-full items-center justify-between gap-2">
                <span className="truncate text-sm">{itemText}</span>
                <span
                  className={`shrink-0 rounded-full border px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide ${getModeClasses(t.mode)}`}
                >
                  {getModeLabel(t.mode)}
                </span>
              </div>
              {t.active_note_title ? (
                <p className="text-muted-foreground line-clamp-1 text-xs">
                  {t.active_note_title}
                </p>
              ) : null}
            </Button>
          </div>
        );
      })}
    </div>
  );
}

function ThreadHistoryLoading() {
  return (
    <div className="flex h-full w-full flex-col items-start justify-start gap-2 overflow-y-scroll px-3 [&::-webkit-scrollbar]:w-1.5 [&::-webkit-scrollbar-thumb]:rounded-full [&::-webkit-scrollbar-thumb]:bg-gray-300 [&::-webkit-scrollbar-track]:bg-transparent">
      {Array.from({ length: 18 }).map((_, i) => (
        <Skeleton
          key={`skeleton-${i}`}
          className="h-14 w-full rounded-xl"
        />
      ))}
    </div>
  );
}

export default function ThreadHistory() {
  const isLargeScreen = useMediaQuery("(min-width: 1024px)");
  const [chatHistoryOpen, setChatHistoryOpen] = useQueryState(
    "chatHistoryOpen",
    parseAsBoolean.withDefault(false),
  );

  const { getThreads, threads, setThreads, threadsLoading, setThreadsLoading } =
    useThreads();

  useEffect(() => {
    if (typeof window === "undefined") return;
    setThreadsLoading(true);
    getThreads()
      .then(setThreads)
      .catch(console.error)
      .finally(() => setThreadsLoading(false));
  }, []);

  const content = (
    <>
      <SidebarActions onClose={() => setChatHistoryOpen(false)} />
      <div className="px-4 pt-4">
        <p className="text-xs font-medium uppercase tracking-[0.16em] text-slate-400">
          历史记录
        </p>
      </div>
      <div className="min-h-0 flex-1 overflow-hidden pb-3">
        {threadsLoading ? (
          <ThreadHistoryLoading />
        ) : (
          <ThreadList
            threads={threads}
            onThreadClick={() => setChatHistoryOpen(false)}
          />
        )}
      </div>
    </>
  );

  return (
    <>
      <div className="shadow-inner-right hidden h-screen w-[300px] shrink-0 flex-col border-r border-slate-300 bg-white lg:flex">
        <div className="flex w-full items-center justify-between px-4 pt-2">
          <Button
            className="hover:bg-gray-100"
            variant="ghost"
            onClick={() => setChatHistoryOpen((p) => !p)}
          >
            {chatHistoryOpen ? (
              <PanelRightOpen className="size-5" />
            ) : (
              <PanelRightClose className="size-5" />
            )}
          </Button>
          <h1 className="text-xl font-semibold tracking-tight">Note Agent</h1>
        </div>
        {content}
      </div>
      <div className="lg:hidden">
        <Sheet
          open={!!chatHistoryOpen && !isLargeScreen}
          onOpenChange={(open) => {
            if (isLargeScreen) return;
            setChatHistoryOpen(open);
          }}
        >
          <SheetContent
            side="left"
            className="flex flex-col p-0 lg:hidden"
          >
            <SheetHeader className="border-b px-4 py-3">
              <SheetTitle>Note Agent</SheetTitle>
            </SheetHeader>
            {content}
          </SheetContent>
        </Sheet>
      </div>
    </>
  );
}
