import { GbaAdapter } from './gba-adapter.mjs';

export async function createGbaCore(romBytes) {
  if (!globalThis.createMgbaModule) {
    await new Promise((resolve, reject) => {
      const script = document.createElement('script');
      script.src = new URL('./vendor/mgba.js', import.meta.url).href;
      script.onload = resolve; script.onerror = reject;
      document.head.appendChild(script);
    });
  }
  const module = await globalThis.createMgbaModule({ locateFile: name => new URL(`./vendor/${name}`, import.meta.url).href });
  return new GbaAdapter(module, romBytes);
}

// Native-rate source PCM, with Web Audio's resampler handling device sample rate.
export class GbaAudio {
  constructor() { this.context = new AudioContext(); this.until = 0; this.sources = new Set(); }
  async resume() { await this.context.resume(); }
  push(chunks) {
    for (const {sampleRate, samples} of chunks) {
      if (!samples.length || this.context.state !== 'running') continue;
      const buffer = this.context.createBuffer(2, samples.length / 2, sampleRate);
      const left=buffer.getChannelData(0),right=buffer.getChannelData(1);
      for(let i=0;i<left.length;i++){left[i]=samples[i*2]/32768;right[i]=samples[i*2+1]/32768;}
      const source=this.context.createBufferSource(); source.buffer=buffer;source.connect(this.context.destination);
      this.until=Math.max(this.until,this.context.currentTime+0.025);
      source.start(this.until);this.until+=buffer.duration;this.sources.add(source);
      source.onended=()=>this.sources.delete(source);
    }
  }
  pause() { for(const source of this.sources)source.stop();this.sources.clear();this.until=0; }
  destroy() { this.pause();return this.context.close(); }
}
