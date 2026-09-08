class NESAudio extends AudioWorkletProcessor {
  constructor() {
    super();
    this.chunks = [];
    this.offset = 0;
    this.port.onmessage = ({ data }) => {
      if (data.flush) {
        this.chunks = [];
        this.offset = 0;
      } else if (data.samples) {
        this.chunks.push(data.samples);
        if (this.chunks.length > 12) {
          this.chunks.shift();
          this.offset = 0;
        }
      }
    };
  }
  process(_inputs, outputs) {
    const left = outputs[0][0],
      right = outputs[0][1];
    if (!left) return true;
    for (let i = 0; i < left.length; i++) {
      const chunk = this.chunks[0];
      if (!chunk) {
        left[i] = 0;
        if (right) right[i] = 0;
        continue;
      }
      left[i] = chunk[this.offset++];
      if (right) right[i] = chunk[this.offset++];
      else this.offset++;
      if (this.offset >= chunk.length) {
        this.chunks.shift();
        this.offset = 0;
      }
    }
    return true;
  }
}
registerProcessor("nes-audio", NESAudio);
