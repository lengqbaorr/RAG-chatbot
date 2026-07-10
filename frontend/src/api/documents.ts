import { apiRequest } from "@/api/client";
import type {
  DocumentDeleteResponse,
  DocumentListResponse,
  DocumentUploadResponse,
  DocumentUrlUploadRequest,
} from "@/types/api";

export function listDocuments(): Promise<DocumentListResponse> {
  return apiRequest<DocumentListResponse>("/documents");
}

export function uploadDocument(file: File): Promise<DocumentUploadResponse> {
  const form = new FormData();
  form.append("file", file);
  return apiRequest<DocumentUploadResponse>("/documents/upload", {
    method: "POST",
    body: form,
  });
}

export function uploadDocumentUrl(payload: DocumentUrlUploadRequest): Promise<DocumentUploadResponse> {
  return apiRequest<DocumentUploadResponse>("/documents/url", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function deleteDocument(sourceId: string): Promise<DocumentDeleteResponse> {
  return apiRequest<DocumentDeleteResponse>(`/documents/${sourceId}`, {
    method: "DELETE",
  });
}

export function reindexDocument(sourceId: string): Promise<DocumentUploadResponse> {
  return apiRequest<DocumentUploadResponse>(`/documents/reindex/${sourceId}`, {
    method: "POST",
  });
}
