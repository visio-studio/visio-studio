import { defineConfig } from 'vite';

// `npm run build`         → sito autonomo in dist/ (three.js incluso nel bundle).
// `npm run build:sito`    → pagina /sole/ del sito, scritta nella cartella sole/ alla radice del repository.
// `npm run build:preview` → anteprima su claude.ai: three.js da CDN tramite import map.
export default defineConfig(({ mode }) => {
  if (mode === 'sito') {
    return {
      base: '/sole/',
      build: { outDir: '../../sole', emptyOutDir: true, chunkSizeWarningLimit: 1000 },
    };
  }
  if (mode !== 'preview-artifact') return { build: { chunkSizeWarningLimit: 1000 } };
  const external = (id) => id === 'three' || id.startsWith('three/');
  return {
    build: {
      outDir: 'dist-preview',
      cssCodeSplit: false,
      modulePreload: false,
      rolldownOptions: { external, output: { codeSplitting: false } },
      rollupOptions: { external },
    },
  };
});
