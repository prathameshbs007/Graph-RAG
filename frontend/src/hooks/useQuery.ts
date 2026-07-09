import { useState } from 'react';
import { api } from '../lib/api';
import type { QueryResponse } from '../types';

export const useQuery = () => {
    const [loading, setLoading] = useState(false);
    const [data, setData] = useState<QueryResponse | null>(null);
    const [error, setError] = useState<string | null>(null);

    const executeQuery = async (text: string) => {
        setLoading(true);
        setError(null);
        try {
            const res = await api.post<QueryResponse>('/query', {
                text,
                top_k: 10,
                rerank_top_n: 5,
            });
            setData(res.data);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'An error occurred during query');
        } finally {
            setLoading(false);
        }
    };

    return { executeQuery, data, loading, error };
};
