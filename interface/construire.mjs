// Construit le script de la fenêtre du mini blind test : src/mini.ts et ce qu'il lit, en un seul module, que le serveur pose
// dans sa page (src/honear_mcp/ressources/mini-blind-test.js). Les licences des paquets embarqués restent à la fin.
//   npm run construire
import { writeFileSync } from 'node:fs';
import { build } from 'esbuild';

const sortie = await build({
  entryPoints: ['src/mini.ts'],
  bundle: true,
  format: 'esm',
  target: 'es2022',
  minify: true,
  legalComments: 'eof',
  write: false,
});
const script = sortie.outputFiles[0].text;
writeFileSync(new URL('../src/honear_mcp/ressources/mini-blind-test.js', import.meta.url), script);
console.log(`${Math.round(script.length / 1024)} Ko`);
