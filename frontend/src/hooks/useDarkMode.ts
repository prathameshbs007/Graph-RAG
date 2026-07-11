import { useEffect, useState } from 'react';

const STORAGE_KEY = 'researchos-theme';

function getInitialTheme(): boolean {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored === 'dark') return true;
    if (stored === 'light') return false;
    return window.matchMedia('(prefers-color-scheme: dark)').matches;
}

export const useDarkMode = () => {
    const [isDark, setIsDark] = useState<boolean>(getInitialTheme);

    useEffect(() => {
        document.documentElement.classList.toggle('dark', isDark);
        localStorage.setItem(STORAGE_KEY, isDark ? 'dark' : 'light');
    }, [isDark]);

    return { isDark, toggle: () => setIsDark(v => !v) };
};
