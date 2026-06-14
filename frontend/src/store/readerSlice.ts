import { create } from 'zustand';
import { ReaderSettings } from '@/types/reader';

interface ReaderState {
  settings: ReaderSettings;
  updateSettings: (partial: Partial<ReaderSettings>) => void;
}

const defaultSettings: ReaderSettings = {
  fontSize: 18,
  fontFamily: 'Georgia, serif',
  lineHeight: 1.8,
  theme: 'day',
  padding: 32,
};

const saved = localStorage.getItem('reader_settings');
const initial: ReaderSettings = saved ? { ...defaultSettings, ...JSON.parse(saved) } : defaultSettings;

export const useReaderStore = create<ReaderState>((set) => ({
  settings: initial,
  updateSettings: (partial) =>
    set((state) => {
      const next = { ...state.settings, ...partial };
      localStorage.setItem('reader_settings', JSON.stringify(next));
      return { settings: next };
    }),
}));
