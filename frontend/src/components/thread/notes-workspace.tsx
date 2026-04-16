"use client";

import { ArrowLeft, BookOpen } from "lucide-react";
import { useQueryState } from "nuqs";

import { Button } from "@/components/ui/button";

export function NotesWorkspace() {
  const [, setWorkspaceView] = useQueryState("workspaceView", {
    defaultValue: "chat",
  });

  return (
    <div className="flex h-full flex-col overflow-hidden bg-slate-50">
      <div className="border-b bg-white px-4 py-3">
        <Button
          variant="ghost"
          className="gap-2"
          onClick={() => setWorkspaceView("chat")}
        >
          <ArrowLeft className="size-4" />
          返回聊天
        </Button>
      </div>

      <div className="flex flex-1 items-center justify-center p-6">
        <div className="w-full max-w-2xl rounded-2xl border bg-white p-8 shadow-sm">
          <div className="mb-4 flex items-center gap-3">
            <div className="rounded-xl bg-slate-100 p-3">
              <BookOpen className="size-5 text-slate-700" />
            </div>
            <div>
              <h2 className="text-xl font-semibold text-slate-900">笔记工作区</h2>
              <p className="text-sm text-slate-500">
                当前组件已恢复为最小可用版本，用于保证前端正常编译与切换视图。
              </p>
            </div>
          </div>

          <div className="rounded-xl border border-dashed bg-slate-50 p-4 text-sm leading-6 text-slate-600">
            <p>这个页面之前依赖的笔记列表与详情能力当前不在源码树中。</p>
            <p>现在先保留占位工作区，避免首页因为缺失组件而直接报错。</p>
            <p>后续如果你要恢复完整笔记浏览，再单独补对应 API 和数据层即可。</p>
          </div>
        </div>
      </div>
    </div>
  );
}
