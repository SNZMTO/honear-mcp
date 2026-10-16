"""Les cloisons entre les deux serveurs : le serveur public, celui de mcp.honear.fr, ne lit rien de l'assistant d'exploitation."""

from tests.test_sources import DU_PAQUET, importes


def test_le_serveur_public_ne_lit_rien_de_l_exploitation() -> None:
    """mcp.honear.fr ne sert rien de l'assistant d'exploitation, pas même par un module qu'il lirait sans le savoir."""
    par_chemin = {s.chemin: s for s in DU_PAQUET}
    a_lire, lus = ["serveurs/public.py"], set()
    while a_lire:
        chemin = a_lire.pop()
        if chemin in lus:
            continue
        lus.add(chemin)
        for nom in importes(par_chemin[chemin]):
            if nom.startswith("honear_mcp."):
                module = nom.removeprefix("honear_mcp.").replace(".", "/")
                a_lire += [c for c in (f"{module}.py", f"{module}/__init__.py") if c in par_chemin]
    assert len(lus) > 10
    assert not [c for c in lus if "exploitation" in c], sorted(lus)
