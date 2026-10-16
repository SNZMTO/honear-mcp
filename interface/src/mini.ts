/**
 * La fenêtre du mini blind test, dans la conversation (MCP Apps). Elle reçoit de l'hôte le résultat de `jouer_ici` (une
 * partie, sans ses réponses), puis appelle les outils du serveur qui ne sont qu'à elle : `mini_piste` (l'extrait de la piste en
 * cours), `mini_repondre` (le jugement d'une saisie) et `mini_reveler` (la réponse, et la suite). À la fin, elle dit au modèle
 * le score et les pistes : la partie est finie, plus rien à souffler.
 */

import { App } from '@modelcontextprotocol/ext-apps/app-with-deps';
import { remplir, TEXTES } from './textes';

type Objet = Readonly<Record<string, unknown>>;
const objet = (x: unknown): Objet | undefined => (typeof x === 'object' && x !== null && !Array.isArray(x) ? (x as Objet) : undefined);
const texte = (x: unknown): string => (typeof x === 'string' ? x : '');
const nombre = (x: unknown): number => (typeof x === 'number' && Number.isFinite(x) ? x : 0);
const textes = (x: unknown): string[] => (Array.isArray(x) ? x.filter((y): y is string => typeof y === 'string') : []);

interface Revelee {
  readonly rang: number;
  readonly titre: string;
  readonly artiste: string;
  readonly trouve: readonly string[];
}

const app = new App({ name: 'honear-mini-blind-test', version: '1.0.0' }, {});
const scene = document.getElementById('mini') as HTMLElement;
const audio = new Audio();
let partie = '';
let nom = '';
let total = 0;
let points = 0;
const revelees: Revelee[] = [];

/** Un élément, sa classe, son texte et ses enfants. */
function el<K extends keyof HTMLElementTagNameMap>(tag: K, classe = '', contenu = '', ...enfants: Node[]): HTMLElementTagNameMap[K] {
  const e = document.createElement(tag);
  if (classe !== '') e.className = classe;
  if (contenu !== '') e.textContent = contenu;
  e.append(...enfants);
  return e;
}

function bouton(contenu: string, quand: () => void, classe = ''): HTMLButtonElement {
  const b = el('button', classe, contenu);
  b.type = 'button';
  b.addEventListener('click', quand);
  return b;
}

function montrer(...enfants: Node[]): void {
  scene.replaceChildren(el('p', 'sous-titre', nom), ...enfants);
}

const disque = (dedans: Node | string = '♪'): HTMLDivElement => {
  const etiquette = el('div', 'etiquette');
  etiquette.append(dedans);
  return el('div', 'disque', '', etiquette);
};

/** Un outil du serveur ; son contenu structuré, ou une erreur qui dit sa phrase. */
async function appeler(name: string, args: Record<string, unknown>): Promise<Objet> {
  const resultat = await app.callServerTool({ name, arguments: { partie, ...args } });
  const contenu = objet(resultat.structuredContent);
  if (resultat.isError === true || contenu === undefined) {
    const premier = objet(resultat.content[0]);
    throw new Error(texte(premier?.['text']).replace(/^Error executing tool \w+: /, ''));
  }
  return contenu;
}

function erreur(e: unknown): void {
  montrer(el('p', 'erreur', e instanceof Error ? e.message : String(e)));
}

function accueil(rang: number): void {
  montrer(el('h1', 'titre', remplir(TEXTES.piste, { rang, total })), disque(), bouton(remplir(TEXTES.lancer, { rang }), () => void ecouter()));
}

async function ecouter(): Promise<void> {
  try {
    const piste = await appeler('mini_piste', {});
    audio.src = texte(piste['extrait']);
    const rang = nombre(piste['rang']);
    const leDisque = disque();
    const chrono = el('div', 'chrono', '', el('span'));
    const verdict = el('p', 'verdict');
    const saisie = el('input');
    saisie.placeholder = TEXTES.placeholder;
    saisie.autocomplete = 'off';
    const formulaire = el('form', '', '', saisie, el('button', '', TEXTES.valider));
    formulaire.addEventListener('submit', (evt) => {
      evt.preventDefault();
      void repondre(saisie, verdict);
    });
    montrer(el('h1', 'titre', remplir(TEXTES.piste, { rang, total })), leDisque, chrono, formulaire, verdict, bouton(TEXTES.reveler, () => void reveler(), 'discret'));
    audio.ontimeupdate = () => {
      (chrono.firstElementChild as HTMLElement).style.width = `${(100 * audio.currentTime) / (audio.duration || 30)}%`;
    };
    audio.onplaying = () => leDisque.classList.add('tourne');
    audio.onended = () => void reveler();
    saisie.focus();
    await audio.play().catch(() => {
      verdict.textContent = TEXTES.muet;
      formulaire.after(bouton(TEXTES.ecouter, () => void audio.play()));
    });
  } catch (e) {
    erreur(e);
  }
}

async function repondre(saisie: HTMLInputElement, verdict: HTMLElement): Promise<void> {
  if (saisie.value.trim() === '') return;
  try {
    const jugee = await appeler('mini_repondre', { saisie: saisie.value });
    const trouve = textes(jugee['trouve']);
    const v = texte(jugee['verdict']);
    points = nombre(jugee['points']);
    saisie.value = '';
    verdict.className = `verdict ${v}`;
    verdict.textContent = v === 'juste' ? remplir(TEXTES.juste, { trouve: nommer(trouve) }) : v === 'presque' ? TEXTES.presque : TEXTES.faux;
    if (trouve.length >= 2) {
      verdict.textContent = TEXTES.tout;
      await reveler();
    }
  } catch (e) {
    erreur(e);
  }
}

const nommer = (parties: readonly string[]): string =>
  parties.map((p) => (p === 'artiste' || p === 'titre' ? TEXTES.parties[p] : p)).join(', ') || TEXTES.rien;

async function reveler(): Promise<void> {
  audio.onended = null;
  audio.pause();
  try {
    const r = await appeler('mini_reveler', {});
    const revelee: Revelee = { rang: nombre(r['rang']), titre: texte(r['titre']), artiste: texte(r['artiste']), trouve: textes(r['trouve']) };
    revelees.push(revelee);
    points = nombre(r['points']);
    const image = texte(r['pochette']);
    const pochette = image !== '' ? Object.assign(el('img'), { src: image, alt: '' }) : '♪';
    const anecdote = texte(r['anecdote']);
    const finie = r['finie'] === true;
    montrer(
      el('h1', 'titre', remplir(TEXTES.piste, { rang: revelee.rang, total })),
      disque(pochette),
      el('p', 'reponse', `${revelee.titre} — ${revelee.artiste}`),
      ...(anecdote !== '' ? [el('p', 'anecdote', anecdote)] : []),
      ...(finie
        ? [el('p', 'score', remplir(TEXTES.fin, { points, sur: total * 2 })), el('p', '', TEXTES.rejouer)]
        : [el('p', 'score', remplir(TEXTES.score, { points })), bouton(TEXTES.suivante, () => void ecouter())]),
    );
    if (finie) await bilan();
  } catch (e) {
    erreur(e);
  }
}

/** La partie finie : le score, et ce qu'on a trouvé, pour le modèle, qui peut maintenant en parler. */
async function bilan(): Promise<void> {
  const sur = total * 2;
  const pistes = revelees.map((p) => remplir(TEXTES.ligne, { ...p, trouve: nommer(p.trouve) })).join(' ; ');
  await app.updateModelContext({ content: [{ type: 'text', text: remplir(TEXTES.bilan, { nom, points, sur, pistes }) }] }).catch(() => undefined);
}

app.addEventListener('toolresult', (resultat) => {
  const prete = objet(resultat.structuredContent);
  partie = texte(prete?.['partie']);
  nom = texte(prete?.['nom']);
  total = nombre(prete?.['total']);
  if (partie === '') montrer(el('p', '', texte(prete?.['message']) || TEXTES.inconnue));
  else accueil(1);
});

scene.append(el('p', 'sous-titre', TEXTES.attente));
await app.connect();
