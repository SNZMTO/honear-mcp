/** Les textes de la fenêtre du mini blind test : tout ce qu'elle montre, et rien ailleurs. `{n}` et les autres se remplacent. */

export const TEXTES = {
  pistes: '{total} pistes',
  lancer: 'Écouter la piste {rang}',
  piste: 'Piste {rang} sur {total}',
  placeholder: 'L’artiste, le titre, ou les deux',
  valider: 'Valider',
  reveler: 'Révéler',
  suivante: 'Piste suivante',
  ecouter: 'Écouter',
  juste: 'Juste ! Trouvé : {trouve}.',
  presque: 'Presque.',
  faux: 'Non.',
  tout: 'Tout trouvé !',
  parties: { artiste: 'l’artiste', titre: 'le titre' },
  score: '{points} point(s)',
  fin: 'Fini : {points} point(s) sur {sur}.',
  rejouer: 'Une autre partie ? Demande-la dans la conversation.',
  attente: 'Le mini blind test arrive…',
  inconnue: 'Pas de partie à jouer ici.',
  muet: 'Le son ne part pas tout seul : touche « Écouter ».',
  bilan: 'Mini blind test « {nom} » fini : {points} point(s) sur {sur}. Les pistes : {pistes}.',
  ligne: '{rang}. {titre} — {artiste} (trouvé : {trouve})',
  rien: 'rien',
} as const;

/** Un texte avec ses valeurs. */
export function remplir(modele: string, valeurs: Readonly<Record<string, string | number>>): string {
  return modele.replace(/\{(\w+)\}/g, (tout, cle: string) => String(valeurs[cle] ?? tout));
}
