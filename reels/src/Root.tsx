import {Composition} from 'remotion';
import {Reel} from './Reel';
import data from './script.json';
import type {Script} from './types';

const s = data as unknown as Script;
export const Root = () => (
  <Composition id="Reel" component={Reel} fps={s.fps} width={1080} height={1920}
    durationInFrames={Math.ceil(s.duration * s.fps)} />
);
