"use client";

import { useCallback, useEffect, useState } from "react";

import { api, ApiError } from "@/lib/api/client";
import type {
  ReviewListResponse,
  ReviewStatusResponse,
  StartReviewRequest,
  StartReviewResponse,
} from "@/lib/api/types";

/**
 * Fetch a paginated list of reviews.
 */
export function useReviews(skip = 0, limit = 20) {
  const [reviews, setReviews] = useState<ReviewListResponse["reviews"]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchReviews = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await api.get<ReviewListResponse>(
        `/reviews?skip=${skip}&limit=${limit}`,
      );
      setReviews(data.reviews);
      setTotal(data.total);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Failed to fetch reviews");
    } finally {
      setIsLoading(false);
    }
  }, [skip, limit]);

  useEffect(() => {
    fetchReviews();
  }, [fetchReviews]);

  return { reviews, total, isLoading, error, refetch: fetchReviews };
}

/**
 * Fetch the status of a single review.
 */
export function useReviewStatus(reviewId: string) {
  const [status, setStatus] = useState<ReviewStatusResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchStatus = useCallback(async () => {
    if (!reviewId?.trim()) {
      setError("Invalid review ID");
      setIsLoading(false);
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      const data = await api.get<ReviewStatusResponse>(`/reviews/${reviewId}`);
      setStatus(data);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Failed to fetch review status");
    } finally {
      setIsLoading(false);
    }
  }, [reviewId]);

  useEffect(() => {
    fetchStatus();
  }, [fetchStatus]);

  return { status, isLoading, error, refetch: fetchStatus };
}

/**
 * Start a new review (mutation hook).
 */
export function useStartReview() {
  const [isSubmitting, setIsSubmitting] = useState(false);

  const startReview = useCallback(async (req: StartReviewRequest) => {
    setIsSubmitting(true);
    try {
      const data = await api.post<StartReviewResponse>("/reviews", req);
      return data;
    } finally {
      setIsSubmitting(false);
    }
  }, []);

  return { startReview, isSubmitting };
}

/**
 * Cancel a review (mutation hook).
 */
export function useCancelReview() {
  const [isCancelling, setIsCancelling] = useState(false);

  const cancelReview = useCallback(async (reviewId: string) => {
    setIsCancelling(true);
    try {
      await api.delete(`/reviews/${reviewId}`);
    } finally {
      setIsCancelling(false);
    }
  }, []);

  return { cancelReview, isCancelling };
}
