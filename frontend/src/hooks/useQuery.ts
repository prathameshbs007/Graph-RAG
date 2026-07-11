import { useState } from 'react';
import { api } from '../lib/api';
import type { QueryCompareResponse, QueryResponse } from '../types';

export const useQuery = () => {
    const [loading, setLoading] = useState(false);
    const [data, setData] = useState<QueryResponse | null>(null);
    const [compareData, setCompareData] = useState<QueryCompareResponse | null>(null);
    const [error, setError] = useState<string | null>(null);

    const executeQuery = async (text: string, compare = false) => {
        setLoading(true);
        setError(null);
        setData(null);
        setCompareData(null);
        try {
            if (compare) {
                const res = await api.post<QueryCompareResponse>('/query/compare', {
                    text,
                    top_k: 10,
                    rerank_top_n: 5,
                });
                setCompareData(res.data);
            } else {
                const res = await api.post<QueryResponse>('/query', {
                    text,
                    top_k: 10,
                    rerank_top_n: 5,
                });
                setData(res.data);
            }
        } catch (err) {
            setError(err instanceof Error ? err.message : 'An error occurred during query');
        } finally {
            setLoading(false);
        }
    };

    return { executeQuery, data, compareData, loading, error };
};
