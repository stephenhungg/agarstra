import { defineConfig } from "vite";
import { runtimeContext } from './scripts/runtime-context.mjs';
export default defineConfig(async () => {
  const runtime = await runtimeContext();
  return {
    base: "./",
    define: {__ASSET_BUILD_PROFILE__: JSON.stringify(process.env.ASSET_PROFILE === 'prototype' ? 'prototype' : 'production'),__ASSET_RUNTIME_SHA256__: JSON.stringify(runtime.sha256)},
    plugins: [{name:'runtime-evidence-context',generateBundle(){this.emitFile({type:'asset',fileName:'build-profile.json',source:JSON.stringify({profile:process.env.ASSET_PROFILE === 'prototype' ? 'prototype' : 'production'})});this.emitFile({type:'asset',fileName:'runtime-build.json',source:runtime.bytes});}}],
    build: {target:"chrome138",assetsInlineLimit:0,chunkSizeWarningLimit:900},
  };
});
