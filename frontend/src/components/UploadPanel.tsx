import React, { useEffect, useRef, useState } from 'react';
import { AlertCircle, CheckCircle2, Clock, FileAudio, FileText, Image as ImageIcon, Loader2, Network, UploadCloud } from 'lucide-react';
import { api } from '../lib/api';
import type { IngestAcceptedResponse, IngestStatus } from '../types';

const AUDIO_EXTENSIONS = /\.(mp3|mp4|mpeg|mpga|m4a|wav|webm|flac|ogg)$/i;

function isAudioFile(f: File): boolean {
    return f.type.startsWith('audio/') || AUDIO_EXTENSIONS.test(f.name);
}

function formatFileSize(bytes: number): string {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export const UploadPanel = () => {
    const [file, setFile] = useState<File | null>(null);
    const [title, setTitle] = useState('');
    const [authors, setAuthors] = useState('');
    const [year, setYear] = useState('');
    const [sourcePaperId, setSourcePaperId] = useState('');
    const [uploading, setUploading] = useState(false);
    const [uploadProgress, setUploadProgress] = useState(0);
    const [status, setStatus] = useState<IngestStatus | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [isDragOver, setIsDragOver] = useState(false);
    const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);

    const isAudio = file !== null && isAudioFile(file);

    useEffect(() => {
        return () => {
            if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
        };
    }, []);

    const pollStatus = (id: string) => {
        pollIntervalRef.current = setInterval(async () => {
            try {
                const res = await api.get<IngestStatus>(`/ingest/status/${id}`);
                setStatus(res.data);
                if (res.data.status === 'done' || res.data.status === 'error') {
                    if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
                    setUploading(false);
                }
            } catch {
                if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
                setUploading(false);
                setError('Failed to check ingestion status');
            }
        }, 1500);
    };

    const handleFileSelect = (selected: File | null) => {
        setFile(selected);
        setStatus(null);
        setError(null);
    };

    const handleDrop = (e: React.DragEvent) => {
        e.preventDefault();
        setIsDragOver(false);
        const dropped = e.dataTransfer.files?.[0];
        if (dropped) handleFileSelect(dropped);
    };

    const handleUpload = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!file) return;

        setUploading(true);
        setUploadProgress(0);
        setStatus(null);
        setError(null);

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
            const endpoint = isAudio ? '/ingest/audio' : '/ingest/pdf';
            const res = await api.post<IngestAcceptedResponse>(endpoint, formData, {
                onUploadProgress: (evt) => {
                    if (evt.total) {
                        setUploadProgress(Math.round((evt.loaded / evt.total) * 100));
                    }
                },
            });
            setStatus({ status: 'processing' });
            pollStatus(res.data.id);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to upload');
            setUploading(false);
        }
    };

    return (
        <div className="p-6 bg-surface-raised border border-border-default rounded-xl max-w-xl mx-auto shadow-sm">
            <h2 className="text-xl font-semibold text-text-default mb-6">Ingest Document (PDF / Audio)</h2>
            <form onSubmit={handleUpload} className="flex flex-col gap-4">
                <div
                    onClick={() => fileInputRef.current?.click()}
                    onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') fileInputRef.current?.click(); }}
                    onDragOver={e => { e.preventDefault(); setIsDragOver(true); }}
                    onDragLeave={() => setIsDragOver(false)}
                    onDrop={handleDrop}
                    role="button"
                    tabIndex={0}
                    className={`border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-500 ${
                        isDragOver
                            ? 'border-accent-500 bg-accent-50 dark:bg-accent-950'
                            : 'border-border-default hover:bg-surface-hover'
                    }`}
                >
                    <input
                        ref={fileInputRef}
                        type="file"
                        accept="application/pdf,audio/*"
                        onChange={e => handleFileSelect(e.target.files?.[0] || null)}
                        className="hidden"
                    />
                    {file ? (
                        <div className="flex items-center justify-center gap-3">
                            {isAudio ? (
                                <FileAudio className="w-8 h-8 text-accent-600 shrink-0" />
                            ) : (
                                <FileText className="w-8 h-8 text-accent-600 shrink-0" />
                            )}
                            <div className="text-left min-w-0">
                                <p className="text-sm font-medium text-text-default truncate max-w-[16rem]">{file.name}</p>
                                <p className="text-xs text-text-muted">{formatFileSize(file.size)}</p>
                            </div>
                        </div>
                    ) : (
                        <div className="flex flex-col items-center gap-2 text-text-muted">
                            <UploadCloud className="w-8 h-8" />
                            <p className="text-sm">Drag &amp; drop a PDF or audio file, or click to browse</p>
                        </div>
                    )}
                </div>

                <input
                    type="text" placeholder="Title (Optional, auto-extracted for PDF)" value={title}
                    onChange={e => setTitle(e.target.value)}
                    className="border border-border-default bg-surface-raised text-text-default placeholder:text-text-muted p-3 rounded-lg focus:ring-2 focus:ring-accent-500 focus:outline-none transition-shadow duration-150"
                />

                {!isAudio && (
                    <>
                        <input
                            type="text" placeholder="Authors (comma separated, Optional)" value={authors}
                            onChange={e => setAuthors(e.target.value)}
                            className="border border-border-default bg-surface-raised text-text-default placeholder:text-text-muted p-3 rounded-lg focus:ring-2 focus:ring-accent-500 focus:outline-none transition-shadow duration-150"
                        />
                        <input
                            type="number" placeholder="Year (Optional)" value={year}
                            onChange={e => setYear(e.target.value)}
                            className="border border-border-default bg-surface-raised text-text-default placeholder:text-text-muted p-3 rounded-lg focus:ring-2 focus:ring-accent-500 focus:outline-none transition-shadow duration-150"
                        />
                    </>
                )}

                {isAudio && (
                    <input
                        type="text" placeholder="Source Paper ID (Optional)" value={sourcePaperId}
                        onChange={e => setSourcePaperId(e.target.value)}
                        className="border border-border-default bg-surface-raised text-text-default placeholder:text-text-muted p-3 rounded-lg focus:ring-2 focus:ring-accent-500 focus:outline-none transition-shadow duration-150"
                    />
                )}

                <button
                    disabled={!file || uploading}
                    type="submit"
                    className="bg-accent-600 text-white font-medium p-3 rounded-lg hover:bg-accent-700 disabled:bg-neutral-300 dark:disabled:bg-neutral-700 disabled:text-neutral-500 transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-500 focus-visible:ring-offset-2"
                >
                    {uploading ? (status?.status === 'processing' ? 'Processing...' : 'Uploading...') : 'Upload & Ingest'}
                </button>

                {uploading && status?.status !== 'processing' && (
                    <div className="w-full bg-surface-hover rounded-full h-2 overflow-hidden">
                        <div className="bg-accent-600 h-2 rounded-full transition-all duration-300" style={{ width: `${uploadProgress}%` }}></div>
                    </div>
                )}
            </form>

            {error && (
                <div className="mt-4 p-3 bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-900 rounded-lg text-sm text-red-600 dark:text-red-300 flex items-center gap-2">
                    <AlertCircle className="w-4 h-4 shrink-0" />
                    {error}
                </div>
            )}

            {status && <IngestResultCard status={status} />}
        </div>
    );
};

function IngestResultCard({ status }: { status: IngestStatus }) {
    if (status.status === 'processing') {
        return (
            <div className="mt-6 p-4 bg-surface-hover border border-border-default rounded-lg text-sm text-text-muted flex items-center gap-2">
                <Loader2 className="w-4 h-4 animate-spin" />
                Processing — this can take a moment for larger files...
            </div>
        );
    }

    if (status.status === 'error') {
        return (
            <div className="mt-6 p-4 bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-900 rounded-lg text-sm text-red-600 dark:text-red-300 flex items-start gap-2">
                <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                <span>{status.detail}</span>
            </div>
        );
    }

    const isAudioResult = 'audio_id' in status;

    return (
        <div className="mt-6 p-4 bg-surface-hover border border-border-default rounded-lg animate-fade-in">
            <div className="flex items-center gap-2 text-sm font-medium text-text-default mb-3">
                <CheckCircle2 className="w-4 h-4 text-green-600 dark:text-green-400" />
                Ingestion complete
            </div>
            <div className="grid grid-cols-2 gap-3 text-sm">
                {isAudioResult ? (
                    <>
                        <StatTile icon={FileAudio} label="Segments" value={status.segments} />
                        <StatTile icon={FileText} label="Chunks" value={status.chunks_created} />
                        <StatTile icon={Clock} label="Duration" value={`${status.duration_seconds.toFixed(1)}s`} />
                    </>
                ) : (
                    <>
                        <StatTile icon={FileText} label="Chunks" value={status.chunks_created} />
                        <StatTile icon={ImageIcon} label="Figures" value={status.figures_extracted} />
                        <StatTile icon={Network} label="Graph Nodes" value={status.graph_nodes_created} />
                    </>
                )}
            </div>
        </div>
    );
}

function StatTile({ icon: Icon, label, value }: { icon: typeof FileText; label: string; value: number | string }) {
    return (
        <div className="flex items-center gap-2 bg-surface-raised border border-border-default rounded-lg px-3 py-2">
            <Icon className="w-4 h-4 text-accent-600 shrink-0" />
            <div>
                <p className="text-xs text-text-muted leading-none">{label}</p>
                <p className="text-sm font-semibold text-text-default leading-tight">{value}</p>
            </div>
        </div>
    );
}
