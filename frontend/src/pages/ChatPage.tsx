import { ChatWindow } from "@/components/chat/ChatWindow";
import { CitationPanel } from "@/components/citation/CitationPanel";
import { DocumentPreviewDialog } from "@/components/document/DocumentPreviewDialog";

export function ChatPage() {
  return (
    <>
      <section className="flex h-[calc(100vh-4rem)]">
        <div className="min-w-0 flex-1">
          <ChatWindow />
        </div>
        <CitationPanel />
      </section>
      <DocumentPreviewDialog />
    </>
  );
}
