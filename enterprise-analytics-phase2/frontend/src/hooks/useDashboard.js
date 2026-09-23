/**
 * useDashboard.js — Custom hook for dashboard data fetching.
 * Handles loading, error, caching and refetch.
 *
 * Copy to: frontend/src/hooks/useDashboard.js
 *
 * Usage:
 *   const { dashboard, loading, error, refetch } = useDashboard("ceo");
 */
import { useState, useEffect, useCallback, useRef } from "react";

const API_BASE = "/api/v1";

// Simple in-memory cache: {cacheKey: {data, ts}}
const _cache = {};
const CACHE_TTL = 1800_000; // 30 minutes in ms

export function useDashboard(personaId, period = "latest") {
  const [dashboard, setDashboard] = useState(null);
  const [loading,   setLoading]   = useState(false);
  const [error,     setError]     = useState(null);
  const abortRef = useRef(null);

  const fetchDashboard = useCallback(async (forceRefresh = false) => {
    if (!personaId) return;

    const cacheKey = `${personaId}:${period}`;

    // Check local cache first (unless forced refresh)
    if (!forceRefresh && _cache[cacheKey]) {
      const { data, ts } = _cache[cacheKey];
      if (Date.now() - ts < CACHE_TTL) {
        setDashboard(data);
        setError(null);
        return;
      }
    }

    // Cancel any pending fetch
    if (abortRef.current) {
      abortRef.current.abort();
    }
    abortRef.current = new AbortController();

    setLoading(true);
    setError(null);

    try {
      const params = new URLSearchParams({
        period,
        dataset_id: "ireland",
        refresh: forceRefresh ? "true" : "false",
      });
      const res = await fetch(
        `${API_BASE}/dashboard/${personaId}?${params}`,
        {
          signal: abortRef.current.signal,
          headers: { "Content-Type": "application/json" },
        }
      );

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.error || `Server error (${res.status})`);
      }

      const data = await res.json();

      // Update local cache
      _cache[cacheKey] = { data, ts: Date.now() };

      setDashboard(data);
    } catch (e) {
      if (e.name === "AbortError") return;   // request cancelled — ignore
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [personaId, period]);

  // Fetch when persona or period changes
  useEffect(() => {
    fetchDashboard(false);
    return () => {
      if (abortRef.current) abortRef.current.abort();
    };
  }, [fetchDashboard]);

  return {
    dashboard,
    loading,
    error,
    refetch: () => fetchDashboard(true),
  };
}
