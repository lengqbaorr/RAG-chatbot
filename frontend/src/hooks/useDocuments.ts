import { useMutation, useQuery } from "@tanstack/react-query";

import {
  deleteDocument,
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
    refetchInterval: 10_000,
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
