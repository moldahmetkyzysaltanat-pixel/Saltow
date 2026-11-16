export type Word = {w: string; s: number; e: number};
export type Layout = 'speaker' | 'split' | 'full';
export type Sentence = {
  start: number; end: number; words: Word[];
  zoom?: 1 | 1.2;           // тұрақты зум, таза кесумен
  layout?: Layout;          // тақырып ауысса: split / full
  panel?: {icon: string; title: string; sub?: string}; // split/full панель мазмұны
};
export type Overlay =
  | {type: 'card'; at: number; until: number; side: 'left' | 'right' | 'top'; icon: string; title: string; sub?: string}
  | {type: 'kinetic'; at: number; until: number; text: string};
export type Script = {
  fps: number; duration: number; video: string;
  sentences: Sentence[]; overlays: Overlay[];
  cta: {start: number; title: string; typed: string};
};
