/** Browser-safe qualification: unsupported formats fail before emulation. */
export function inspectRom(input) {
  const b = new Uint8Array(input);
  if (b.length < 16 || b[0] !== 78 || b[1] !== 69 || b[2] !== 83 || b[3] !== 26) throw Error('Expected an iNES .nes ROM. Other Nintendo platforms are unsupported.');
  if ((b[7] & 12) === 8) throw Error('NES 2.0 is unsupported by this extractor.');
  if (b[7] & 3) throw Error('VS/PlayChoice console ROMs are unsupported.');
  if (b[9] & 1) throw Error('PAL timing is unsupported; this runtime currently uses NTSC.');
  if (b.slice(12,16).some(v => v)) throw Error('Ambiguous legacy iNES header: reserved bytes must be zero.');
  const mapper = (b[6] >> 4) | (b[7] & 240);
  if (![0,4].includes(mapper)) throw Error(`Mapper ${mapper} is unsupported; qualified CHR-ROM observers cover mapper 0 and 4.`);
  const prgBytes = b[4]*16384, chrBytes=b[5]*8192, trainerBytes=b[6]&4?512:0, chrStart=16+trainerBytes+prgBytes;
  if (trainerBytes) throw Error('Trainer-bearing ROMs are unsupported: trainer initialization is not qualified.');
  if (!prgBytes) throw Error('ROM has no PRG data.');
  if (!chrBytes) throw Error('CHR-RAM requires mutable tile invalidation and is unsupported.');
  if (b.length < chrStart+chrBytes) throw Error('Truncated ROM: declared PRG/CHR exceeds file length.');
  if (mapper===0 && (![16384,32768].includes(prgBytes)||chrBytes!==8192)) throw Error('Invalid NROM bank sizes.');
  return {format:'iNES',platform:'NES',timing:'NTSC',mapper,mapperName:mapper===0?'NROM':'MMC3',prgBytes,chrBytes,chrStart,trainerBytes,byteLength:b.length,trailingBytes:b.length-chrStart-chrBytes,mirroring:b[6]&8?'four-screen':b[6]&1?'vertical':'horizontal',battery:!!(b[6]&2)};
}
export function decodeTile(bytes) {
  return Array.from({length:64},(_,i)=>((bytes[i>>3]>>(7-(i&7)))&1)|(((bytes[(i>>3)+8]>>(7-(i&7)))&1)<<1));
}
