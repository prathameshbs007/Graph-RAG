import React, { useState } from 'react';

export const UploadPanel = () => {
    const [file, setFile] = useState<File | null>(null);
    const [title, setTitle] = useState('');
    const [authors, setAuthors] = useState('');
    const [year, setYear] = useState('');
    const [sourcePaperId, setSourcePaperId] = useState('');
    const [uploading, setUploading] = useState(false);
    const [result, setResult] = useState<any>(null);
    const [progress, setProgress] = useState(0);

    const isAudio = file?.type.startsWith('audio/') || file?.name.match(/\.(mp3|wav|m4a)$/i);

    const handleUpload = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!file) return;

        setUploading(true);
        setProgress(10);
        const formData = new FormData();
        formData.append('file', file);
        if (title) formData.append('title', title);

        if (isAudio) {
            if (sourcePaperId) formData.append('source_paper_id', sourcePaperId);
        } else {
            if (authors) formData.append('authors', authors);
            if (year) formData.append('year', year);
        }

        try {
            setProgress(40);
            const endpoint = isAudio ? '/ingest/audio' : '/ingest/pdf';
            const res = await fetch(`http://localhost:8054${endpoint}`, {
                method: 'POST',
                body: formData
            });
            setProgress(80);
            const data = await res.json();
            setResult(data);
            setProgress(100);
        } catch (error) {
            console.error('Upload failed', error);
            setResult({ error: 'Failed to upload' });
        } finally {
            setUploading(false);
            setTimeout(() => setProgress(0), 2000);
        }
    };

    return (
        <div className="p-6 bg-white border rounded-xl max-w-xl mx-auto shadow-sm">
            <h2 className="text-2xl font-semibold mb-6">Ingest Document (PDF / Audio)</h2>
            <form onSubmit={handleUpload} className="flex flex-col gap-4">
                <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center hover:bg-gray-50 transition-colors">
                    <input
                        type="file"
                        accept="application/pdf,audio/*"
                        onChange={e => setFile(e.target.files?.[0] || null)}
                        className="w-full text-gray-500"
                    />
                </div>

                <input
                    type="text" placeholder="Title (Optional, auto-extracted for PDF)" value={title}
                    onChange={e => setTitle(e.target.value)}
                    className="border border-gray-300 p-3 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none"
                />

                {!isAudio && (
                    <>
                        <input
                            type="text" placeholder="Authors (comma separated, Optional)" value={authors}
                            onChange={e => setAuthors(e.target.value)}
                            className="border border-gray-300 p-3 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none"
                        />
                        <input
                            type="number" placeholder="Year (Optional)" value={year}
                            onChange={e => setYear(e.target.value)}
                            className="border border-gray-300 p-3 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none"
                        />
                    </>
                )}

                {isAudio && (
                    <input
                        type="text" placeholder="Source Paper ID (Optional)" value={sourcePaperId}
                        onChange={e => setSourcePaperId(e.target.value)}
                        className="border border-gray-300 p-3 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none"
                    />
                )}

                <button
                    disabled={!file || uploading}
                    type="submit"
                    className="bg-blue-600 text-white font-medium p-3 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                    {uploading ? 'Processing...' : 'Upload & Ingest'}
                </button>

                {uploading && progress > 0 && (
                    <div className="w-full bg-gray-200 rounded-full h-2.5 mt-2 overflow-hidden">
                        <div className="bg-blue-600 h-2.5 rounded-full transition-all duration-300" style={{ width: `${progress}%` }}></div>
                    </div>
                )}
            </form>

            {result && (
                <div className="mt-6 p-4 bg-gray-50 border border-gray-200 rounded-lg text-sm overflow-auto max-h-64">
                    <h3 className="font-semibold text-gray-700 mb-2">Ingestion Result</h3>
                    <pre className="text-gray-600 whitespace-pre-wrap">{JSON.stringify(result, null, 2)}</pre>
                </div>
            )}
        </div>
    );
};
