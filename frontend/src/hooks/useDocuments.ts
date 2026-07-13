import { useMutation, useQuery } from "@tanstack/react-query";

import {
  deleteDocument,
  getDocumentChunkPreview,
  getDocumentPreview,
  listDocuments,
  reindexDocument,
  uploadDocument,
  uploadDocumentUrl,
} from "@/api/documents";
import { queryClient } from "@/services/queryClient";

export function useDocuments() {
  return useQuery({
    queryKey: ["documents"],
    queryFn: listDocuments,
    refetchInterval: 30_000,
  });
}

export function useUploadDocument() {
  return useMutation({
    mutationFn: uploadDocument,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["documents"] });
      void queryClient.invalidateQueries({ queryKey: ["jobs"] });
    },
  });
}

export function useUploadDocumentUrl() {
  return useMutation({
    mutationFn: uploadDocumentUrl,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["documents"] });
      void queryClient.invalidateQueries({ queryKey: ["jobs"] });
    },
  });
}

export function useDeleteDocument() {
  return useMutation({
    mutationFn: deleteDocument,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["documents"] });
      void queryClient.invalidateQueries({ queryKey: ["health"] });
    },
  });
}

export function useReindexDocument() {
  return useMutation({
    mutationFn: reindexDocument,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["jobs"] });
    },
  });
}

export function useDocumentPreview(sourceId: string | null) {
  return useQuery({
    queryKey: ["document-preview", sourceId],
    queryFn: () => getDocumentPreview(sourceId as string),
    enabled: Boolean(sourceId),
    staleTime: 5 * 60_000,
  });
}

export function useDocumentChunkPreview(sourceId: string | null, chunkId: string | null) {
  return useQuery({
    queryKey: ["document-chunk-preview", sourceId, chunkId],
    queryFn: () => getDocumentChunkPreview(sourceId as string, chunkId as string),
    enabled: Boolean(sourceId && chunkId),
    staleTime: 5 * 60_000,
  });
}
