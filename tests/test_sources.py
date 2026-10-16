"""Les règles de tenue du code, vérifiées sur les sources elles-mêmes, par leur arbre syntaxique.

Un test rouge ici, c'est une règle enfreinte, pas un test à changer.
"""

import ast
import re
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path

import pytest

RACINE = Path(__file__).parent.parent
PAQUET = RACINE / "src" / "honear_mcp"

COUCHES = ("ressources", "regles", "sources", "reseau", "outils", "serveurs")
"""Du bas vers le haut : chaque couche ne lit que les précédentes, et elle-même."""

PUR = {
    "__future__",
    "collections",
    "dataclasses",
    "difflib",
    "enum",
    "functools",
    "itertools",
    "re",
    "typing",
    "unicodedata",
    "urllib",
}
DEHORS: dict[str, set[str]] = {
    "ressources": {"dataclasses"},
    "regles": PUR | {"pydantic"},
    "sources": PUR | {"pydantic"},
    "reseau": PUR | {"pydantic", "httpx2", "anyio", "time", "datetime", "secrets", "os", "pathlib", "ssl"},
    "outils": PUR | {"pydantic", "mcp"},
    "serveurs": PUR
    | {"pydantic", "mcp", "starlette", "uvicorn", "httpx2", "anyio", "base64", "contextlib", "hashlib", "http", "importlib"}
    | {"logging", "math", "os", "pathlib"},
}
"""Ce que chaque couche lit hors du paquet. Les règles et les sources ne touchent ni au disque, ni au réseau, ni à l'heure."""

SEULS: dict[str, str] = {"time": "reseau/horloge.py", "datetime": "reseau/horloge.py", "secrets": "reseau/hasard.py"}
"""Ce qui ne se lit qu'à un endroit : l'heure, et le hasard des identifiants. `random` ne se lit nulle part."""


@dataclass(frozen=True)
class Source:
    """Un module : son chemin depuis le paquet (ou depuis la racine, pour un test), sa couche, son texte et son arbre."""

    chemin: str
    couche: str
    texte: str
    arbre: ast.Module


def _lire(dossier: Path, depuis: Path) -> list[Source]:
    sources = []
    for fichier in sorted(dossier.rglob("*.py")):
        chemin = fichier.relative_to(depuis).as_posix()
        texte = fichier.read_text(encoding="utf-8")
        sources.append(Source(chemin, chemin.split("/")[0] if "/" in chemin else "", texte, ast.parse(texte)))
    return sources


DU_PAQUET = _lire(PAQUET, PAQUET)
DES_TESTS = _lire(RACINE / "tests", RACINE)
TOUTES = DU_PAQUET + DES_TESTS


def importes(source: Source) -> list[str]:
    noms: list[str] = []
    for noeud in ast.walk(source.arbre):
        if isinstance(noeud, ast.Import):
            noms += [alias.name for alias in noeud.names]
        elif isinstance(noeud, ast.ImportFrom):
            assert noeud.level == 0, f"{source.chemin} importe par un chemin relatif"
            noms.append(noeud.module or "")
    return noms


def _docstrings(arbre: ast.Module) -> set[int]:
    """Les chaînes qui documentent (un module, une classe, une fonction, un attribut) : seules à avoir une ligne pour elles."""
    return {id(n.value) for n in ast.walk(arbre) if isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant)}


def test_les_couches_ne_lisent_que_celles_du_dessous() -> None:
    assert {s.couche for s in DU_PAQUET} == {"", *COUCHES}
    for source in DU_PAQUET:
        for nom in importes(source):
            if nom.startswith("honear_mcp."):
                lue = nom.split(".")[1]
                assert COUCHES.index(lue) <= COUCHES.index(source.couche), f"{source.chemin} ({source.couche}) lit {nom}"
            elif source.couche != "":
                assert nom.split(".")[0] in DEHORS[source.couche], f"{source.chemin} ({source.couche}) lit {nom}"


def test_chaque_dependance_declaree_sert_et_rien_d_autre_ne_s_importe() -> None:
    projet = tomllib.loads((RACINE / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    declarees = {re.split(r"[=<>\[ ]", d)[0] for d in projet["dependencies"]}
    tierces = {n for n in set().union(*DEHORS.values()) if n not in sys.stdlib_module_names}
    lues = {n.split(".")[0] for s in DU_PAQUET for n in importes(s)} & tierces
    assert lues == declarees == tierces


def test_l_heure_et_le_hasard_ne_se_lisent_qu_a_leur_place() -> None:
    for source in TOUTES:
        for nom in importes(source):
            racine = nom.split(".")[0]
            assert racine != "random", f"{source.chemin} tire au sort : le hasard est une graine"
            if racine in SEULS and source.chemin != SEULS[racine]:
                pytest.fail(f"{source.chemin} lit {racine}, qui ne se lit que dans {SEULS[racine]}")
        if source.chemin != "reseau/horloge.py" and source in DU_PAQUET:
            assert not re.search(r"\b(anyio|asyncio)\.(sleep|current_time)\b", source.texte), (
                f"{source.chemin} attend sans horloge"
            )


def _decalages(arbre: ast.Module) -> set[int]:
    """Les nombres qui décalent un indice (`b[j - 2]`) : un rang dans une suite, pas un réglage."""
    calculs = [c for i in ast.walk(arbre) if isinstance(i, ast.Subscript) for c in ast.walk(i.slice) if isinstance(c, ast.BinOp)]
    return {
        id(o) for c in calculs if isinstance(c.op, ast.Add | ast.Sub) for o in (c.left, c.right) if isinstance(o, ast.Constant)
    }


def test_aucun_nombre_de_reglage_hors_des_ressources() -> None:
    for source in DU_PAQUET:
        if source.couche == "ressources":
            continue
        decalages = _decalages(source.arbre)
        for noeud in ast.walk(source.arbre):
            if isinstance(noeud, ast.Constant) and type(noeud.value) in {int, float, complex} and id(noeud) not in decalages:
                assert noeud.value in {0, 1}, (
                    f"{source.chemin}:{noeud.lineno} écrit {noeud.value!r} : un réglage se lit dans une table"
                )


def test_les_ressources_sont_des_donnees_jamais_du_code() -> None:
    for source in DU_PAQUET:
        if source.couche != "ressources":
            continue
        for noeud in ast.walk(source.arbre):
            assert not isinstance(noeud, ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda), f"{source.chemin}:{noeud.lineno}"
            if isinstance(noeud, ast.ClassDef):
                assert all(isinstance(n, ast.AnnAssign | ast.Expr) for n in noeud.body), f"{source.chemin} : {noeud.name}"
                assert [ast.unparse(d) for d in noeud.decorator_list] == ["dataclass(frozen=True)"], (
                    f"{source.chemin} : {noeud.name}"
                )


def _est_une_phrase(texte: str) -> bool:
    """Trois mots au moins, et rien d'une expression régulière ni d'un en-tête (un « ; » collé au mot, comme dans une CSP ; le
    français l'espace) : un texte que quelqu'un lira."""
    mots = [m for m in texte.split() if m.strip(",.;:!?«»()’'").isalpha()]
    return len(mots) >= 3 and not re.search(r"[\\|]|\(\?|\S;", texte)


def test_les_textes_montres_aux_gens_sont_dans_un_seul_module() -> None:
    for source in DU_PAQUET:
        if re.fullmatch(r"ressources/textes(_\w+)?\.py", source.chemin):
            continue
        documentation = _docstrings(source.arbre)
        for noeud in ast.walk(source.arbre):
            if isinstance(noeud, ast.Constant) and isinstance(noeud.value, str) and id(noeud) not in documentation:
                assert not _est_une_phrase(noeud.value), f"{source.chemin}:{noeud.lineno} écrit « {noeud.value} »"


def test_le_typage_reste_strict_et_rien_ne_s_ecrit_a_l_ecran() -> None:
    for source in TOUTES:
        for noeud in ast.walk(source.arbre):
            assert not (isinstance(noeud, ast.Name) and noeud.id in {"Any", "cast", "print"}), f"{source.chemin}:{noeud.lineno}"
            assert not (isinstance(noeud, ast.Attribute) and noeud.attr in {"Any", "cast"}), f"{source.chemin}:{noeud.lineno}"
        assert not re.search(r"#\s*(type:\s*ignore|noqa|pragma)", source.texte), source.chemin


def test_rien_de_provisoire_n_est_commite() -> None:
    for source in DU_PAQUET:
        assert not re.search(r"\b(TODO|FIXME|XXX)\b|temporaire|pour plus tard|pour les tests", source.texte), source.chemin


def test_chaque_module_dit_son_role_et_reste_court() -> None:
    for source in TOUTES:
        assert ast.get_docstring(source.arbre), f"{source.chemin} ne dit pas à quoi il sert"
        assert source.texte.count("\n") <= 200, f"{source.chemin} a plus de 200 lignes"
        assert not re.search(r"(^|/)(utils?|helpers?|divers|commun|misc)(\.py|/)", source.chemin), source.chemin
