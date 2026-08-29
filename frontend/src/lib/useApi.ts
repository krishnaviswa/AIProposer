"use client";

import { useCallback, useEffect, useState } from "react";

/** Minimal data hook — loads once, exposes a refetch. */
export function useResource<T>(loader: () => Promise<T>, deps: unknown[] = []) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [loading, setLoading] = useState(true);

  const run = useCallback(() => {
    setLoading(true);
    loader()
      .then((d) => {
        setData(d);
        setError(null);
      })
      .catch((e: Error) => setError(e))
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  useEffect(run, [run]);

  return { data, error, loading, refetch: run, setData };
}
