import { useState } from 'react';
import axios from 'axios';

export const useQuery = () => {
    const [loading, setLoading] = useState(false);
    const [data, setData] = useState<any>(null);
    const [error, setError] = useState<string | null>(null);

    const executeQuery = async (text: string, imageBase64?: string | null) => {
        setLoading(true);
        setError(null);
        try {
            const res = await axios.post('http://localhost:8054/query', {
                text,
                image_base64: imageBase64,
                top_k: 10,
                rerank_top_n: 5
            });
            setData(res.data);
        } catch (err: any) {
            setError(err.message || 'An error occurred during query');
        } finally {
            setLoading(false);
        }
    };

    return { executeQuery, data, loading, error };
};
