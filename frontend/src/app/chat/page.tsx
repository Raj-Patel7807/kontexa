"use client";

import * as React from "react";
import { useEffect, useState, useRef, useTransition } from "react";
import { useRouter } from "next/navigation";
import { getCurrentUserApi, getCsrfTokenApi, UserProfile } from "../lib/auth";
import { listWorkspacesApi, createWorkspaceApi, WorkspaceItem } from "../lib/workspaces";
import {
  listConversationsApi,
  createConversationApi,
  renameConversationApi,
  deleteConversationApi,
  listMessagesApi,
  sendMessageApi,
  ConversationItem,
  MessageItem,
} from "../lib/conversations";
import { AppShell } from "@/components/app-shell";
import {
  Button,
  Input,
  Modal,
  Badge,
  EmptyState,
  ErrorBoundary,
  Skeleton,
} from "@/components/ui";

export default function ChatPage() {
  const router = useRouter();
  const [user, setUser] = useState<UserProfile | null>(null);
  const [csrfToken, setCsrfToken] = useState<string>("");
  const [workspaces, setWorkspaces] = useState<WorkspaceItem[]>([]);
  const [selectedWorkspace, setSelectedWorkspace] = useState<WorkspaceItem | null>(null);

  // Chat conversation state
  const [conversations, setConversations] = useState<ConversationItem[]>([]);
  const [selectedConversation, setSelectedConversation] = useState<ConversationItem | null>(null);
  const [messages, setMessages] = useState<MessageItem[]>([]);
  const [inputContent, setInputContent] = useState("");

  // Modals & Renaming
  const [isCreatingWorkspace, setIsCreatingWorkspace] = useState(false);
  const [newWsName, setNewWsName] = useState("");
  const [isRenamingConv, setIsRenamingConv] = useState(false);
  const [renameTitle, setRenameTitle] = useState("");

  const [loading, setLoading] = useState(true);
  const [messagesLoading, setMessagesLoading] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll messages
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Initial user & workspaces load
  useEffect(() => {
    let mounted = true;
    async function loadData() {
      try {
        const userData = await getCurrentUserApi();
        if (!mounted) return;
        setUser(userData);

        const csrfData = await getCsrfTokenApi().catch(() => ({ csrf_token: "" }));
        if (mounted) setCsrfToken(csrfData.csrf_token);

        const wsList = await listWorkspacesApi();
        if (!mounted) return;
        setWorkspaces(wsList);

        if (wsList.length > 0) {
          setSelectedWorkspace(wsList[0]);
        }
      } catch {
        router.push("/login");
      } finally {
        if (mounted) setLoading(false);
      }
    }
    loadData();
    return () => {
      mounted = false;
    };
  }, [router]);

  // Load conversations when workspace changes
  useEffect(() => {
    if (!selectedWorkspace) return;

    let mounted = true;
    async function loadConversations(wsId: string) {
      try {
        const convList = await listConversationsApi(wsId);
        if (!mounted) return;
        setConversations(convList);
        if (convList.length > 0) {
          setSelectedConversation(convList[0]);
        } else {
          setSelectedConversation(null);
          setMessages([]);
        }
      } catch (err: unknown) {
        if (!mounted) return;
        setError(err instanceof Error ? err.message : "Failed to load conversations");
      }
    }
    loadConversations(selectedWorkspace.id);
    return () => {
      mounted = false;
    };
  }, [selectedWorkspace]);

  // Load messages when conversation selection changes
  useEffect(() => {
    if (!selectedWorkspace || !selectedConversation) return;

    let mounted = true;
    async function loadMessages(wsId: string, convId: string) {
      setMessagesLoading(true);
      try {
        const msgList = await listMessagesApi(wsId, convId);
        if (!mounted) return;
        setMessages(msgList);
      } catch (err: unknown) {
        if (!mounted) return;
        setError(err instanceof Error ? err.message : "Failed to load messages");
      } finally {
        if (mounted) setMessagesLoading(false);
      }
    }
    loadMessages(selectedWorkspace.id, selectedConversation.id);
    return () => {
      mounted = false;
    };
  }, [selectedWorkspace, selectedConversation]);

  const handleCreateNewConversation = async () => {
    if (!selectedWorkspace) return;
    setError(null);

    startTransition(async () => {
      try {
        const created = await createConversationApi(
          selectedWorkspace.id,
          undefined,
          "New Conversation",
          csrfToken
        );
        setConversations((prev) => [created, ...prev]);
        setSelectedConversation(created);
        setMessages([]);
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Failed to create conversation");
      }
    });
  };

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedWorkspace || !selectedConversation || !inputContent.trim() || isSending) return;

    const content = inputContent.trim();
    setInputContent("");
    setIsSending(true);
    setError(null);

    // Generate client-side idempotency key to prevent double submits
    const idempotencyKey = `msg_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;

    try {
      const newMessages = await sendMessageApi(
        selectedWorkspace.id,
        selectedConversation.id,
        content,
        idempotencyKey,
        csrfToken
      );

      setMessages((prev) => [...prev, ...newMessages]);

      // Update conversation title in list if changed
      setConversations((prev) =>
        prev.map((c) =>
          c.id === selectedConversation.id
            ? { ...c, title: c.title === "New Conversation" ? content.slice(0, 45) : c.title }
            : c
        )
      );
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to send message");
      // Restore input content on error
      setInputContent(content);
    } finally {
      setIsSending(false);
    }
  };

  const handleRenameConversation = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedWorkspace || !selectedConversation || !renameTitle.trim()) return;

    startTransition(async () => {
      try {
        const updated = await renameConversationApi(
          selectedWorkspace.id,
          selectedConversation.id,
          renameTitle.trim(),
          csrfToken
        );
        setConversations((prev) =>
          prev.map((c) => (c.id === updated.id ? updated : c))
        );
        setSelectedConversation(updated);
        setIsRenamingConv(false);
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Failed to rename conversation");
      }
    });
  };

  const handleDeleteConversation = async (convId: string) => {
    if (!selectedWorkspace) return;
    if (!window.confirm("Are you sure you want to delete this conversation?")) return;

    startTransition(async () => {
      try {
        await deleteConversationApi(selectedWorkspace.id, convId, csrfToken);
        const filtered = conversations.filter((c) => c.id !== convId);
        setConversations(filtered);
        if (selectedConversation?.id === convId) {
          setSelectedConversation(filtered.length > 0 ? filtered[0] : null);
          setMessages([]);
        }
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Failed to delete conversation");
      }
    });
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center text-slate-400">
        Loading chat workspace...
      </div>
    );
  }

  if (!user) return null;

  return (
    <ErrorBoundary>
      <AppShell
        user={user}
        workspaces={workspaces}
        currentWorkspace={selectedWorkspace}
        onSelectWorkspace={(ws) => setSelectedWorkspace(ws)}
        onOpenCreateWorkspace={() => setIsCreatingWorkspace(true)}
        csrfToken={csrfToken}
      >
        <div className="flex-1 flex h-[calc(100vh-57px)] overflow-hidden">
          {/* Thread History Sidebar */}
          <section className="w-72 bg-slate-900/60 border-r border-slate-800/80 flex flex-col shrink-0">
            <div className="p-3 border-b border-slate-800 flex items-center justify-between">
              <span className="text-xs font-bold text-slate-300 uppercase tracking-wider">
                Conversations
              </span>
              <Button
                size="sm"
                variant="outline"
                onClick={handleCreateNewConversation}
                disabled={isPending}
                className="text-xs text-indigo-400 hover:text-indigo-300 px-2 py-1"
              >
                + New Chat
              </Button>
            </div>

            <div className="flex-1 overflow-y-auto p-2 space-y-1">
              {conversations.length === 0 ? (
                <div className="text-center py-8 text-xs text-slate-500">
                  No conversations yet. Start a new chat!
                </div>
              ) : (
                conversations.map((c) => {
                  const isSelected = selectedConversation?.id === c.id;
                  return (
                    <div
                      key={c.id}
                      className={`group flex items-center justify-between px-3 py-2 rounded-lg text-xs cursor-pointer transition-colors ${
                        isSelected
                          ? "bg-indigo-600/20 text-indigo-300 border border-indigo-500/30"
                          : "text-slate-400 hover:bg-slate-800 hover:text-slate-200"
                      }`}
                      onClick={() => setSelectedConversation(c)}
                    >
                      <span className="truncate flex-1 font-medium mr-2">
                        {c.title || "Untitled Conversation"}
                      </span>
                      <div className="hidden group-hover:flex items-center gap-1">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setRenameTitle(c.title || "");
                            setIsRenamingConv(true);
                          }}
                          className="p-1 hover:text-white"
                          title="Rename"
                        >
                          ✎
                        </button>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleDeleteConversation(c.id);
                          }}
                          className="p-1 hover:text-rose-400"
                          title="Delete"
                        >
                          ✕
                        </button>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </section>

          {/* Active Conversation & Message Composer */}
          <section className="flex-1 flex flex-col bg-slate-950 min-w-0">
            {/* Conversation Header */}
            <div className="px-6 py-3 border-b border-slate-800 flex items-center justify-between bg-slate-900/40">
              <div className="flex items-center gap-2">
                <h2 className="text-sm font-semibold text-slate-100 truncate">
                  {selectedConversation?.title || "No Conversation Selected"}
                </h2>
                {selectedConversation && (
                  <Badge variant="outline">
                    {messages.length} messages
                  </Badge>
                )}
              </div>
            </div>

            {error && (
              <div className="m-4 p-3 bg-rose-950/60 border border-rose-800/60 rounded-lg text-xs text-rose-300 flex justify-between items-center">
                <span>{error}</span>
                <button onClick={() => setError(null)} className="text-rose-400 hover:text-rose-200">
                  Dismiss
                </button>
              </div>
            )}

            {/* Message Stream */}
            <div className="flex-1 overflow-y-auto p-6 space-y-4">
              {!selectedConversation ? (
                <EmptyState
                  title="No conversation selected"
                  description="Choose an existing thread from the sidebar or click 'New Chat' to get started."
                  actionLabel="Start New Conversation"
                  onAction={handleCreateNewConversation}
                />
              ) : messagesLoading ? (
                <div className="space-y-4">
                  <Skeleton className="h-16 w-3/4 rounded-xl" />
                  <Skeleton className="h-20 w-1/2 ml-auto rounded-xl" />
                  <Skeleton className="h-16 w-2/3 rounded-xl" />
                </div>
              ) : messages.length === 0 ? (
                <EmptyState
                  title="Thread is empty"
                  description="Ask engineering questions, inspect code, or plan tasks with your workspace context."
                />
              ) : (
                messages.map((m) => {
                  const isUser = m.role === "user";
                  return (
                    <div
                      key={m.id}
                      className={`flex flex-col ${isUser ? "items-end" : "items-start"}`}
                    >
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-[10px] font-mono uppercase text-slate-500">
                          {isUser ? user.name || "Developer" : "Assistant (Dev Adapter)"}
                        </span>
                        <span className="text-[10px] text-slate-600 font-mono">
                          {new Date(m.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                        </span>
                      </div>
                      <div
                        className={`max-w-2xl px-4 py-3 rounded-2xl text-xs leading-relaxed whitespace-pre-wrap ${
                          isUser
                            ? "bg-indigo-600 text-white rounded-br-sm"
                            : "bg-slate-900 border border-slate-800 text-slate-200 rounded-bl-sm font-sans"
                        }`}
                      >
                        {m.content}
                      </div>
                    </div>
                  );
                })
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Message Input Composer */}
            {selectedConversation && (
              <form
                onSubmit={handleSendMessage}
                className="p-4 border-t border-slate-800 bg-slate-900/60"
              >
                <div className="flex items-center gap-2">
                  <input
                    type="text"
                    disabled={isSending}
                    placeholder="Ask Kontexa or describe a task..."
                    value={inputContent}
                    onChange={(e) => setInputContent(e.target.value)}
                    className="flex-1 bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-xs text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-colors"
                  />
                  <Button
                    type="submit"
                    size="sm"
                    disabled={!inputContent.trim() || isSending}
                    isLoading={isSending}
                  >
                    Send
                  </Button>
                </div>
              </form>
            )}
          </section>
        </div>

        {/* Modal: Rename Conversation */}
        <Modal
          isOpen={isRenamingConv}
          onClose={() => setIsRenamingConv(false)}
          title="Rename Conversation"
        >
          <form onSubmit={handleRenameConversation} className="space-y-4">
            <Input
              label="Conversation Title"
              required
              value={renameTitle}
              onChange={(e) => setRenameTitle(e.target.value)}
            />
            <div className="flex justify-end gap-2 pt-2">
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => setIsRenamingConv(false)}
              >
                Cancel
              </Button>
              <Button type="submit" size="sm" isLoading={isPending}>
                Save Title
              </Button>
            </div>
          </form>
        </Modal>

        {/* Modal: Create Workspace fallback */}
        <Modal
          isOpen={isCreatingWorkspace}
          onClose={() => setIsCreatingWorkspace(false)}
          title="Create Organization"
        >
          <form
            onSubmit={async (e) => {
              e.preventDefault();
              if (!newWsName.trim()) return;
              try {
                const ws = await createWorkspaceApi(newWsName.trim(), undefined, csrfToken);
                setWorkspaces((prev) => [ws, ...prev]);
                setSelectedWorkspace(ws);
                setNewWsName("");
                setIsCreatingWorkspace(false);
              } catch (err: unknown) {
                setError(err instanceof Error ? err.message : "Failed to create workspace");
              }
            }}
            className="space-y-4"
          >
            <Input
              label="Organization Name"
              required
              placeholder="e.g. Acme Engineering"
              value={newWsName}
              onChange={(e) => setNewWsName(e.target.value)}
            />
            <div className="flex justify-end gap-2 pt-2">
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => setIsCreatingWorkspace(false)}
              >
                Cancel
              </Button>
              <Button type="submit" size="sm">
                Create Organization
              </Button>
            </div>
          </form>
        </Modal>
      </AppShell>
    </ErrorBoundary>
  );
}
