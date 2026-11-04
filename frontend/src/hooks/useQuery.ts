import { useState } from "react";
import axios from "axios";
import { API } from "../api";
import type { QueryResult } from "../types";

export const useQuery = () => {
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<QueryResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  // `system` selects the full ResearchOS pipeline or one of the baselines / ablations.
  const executeQuery = async (text: string, system: string = "full") => {
    setLoading(true);
    setError(null);
    try {
      const res = await axios.post<QueryResult>(`${API}/query`, { text, system });
      setData(res.data);
    } catch (err: unknown) {
      const detail = axios.isAxiosError(err) ? err.response?.data?.detail : undefined;
      setError(
        typeof detail === "string"
          ? detail
          : err instanceof Error
            ? err.message
            : "An error occurred during query",
      );
    } finally {
      setLoading(false);
    }
  };

  return { executeQuery, data, loading, error };
};
