"""Le journal du MCP : une ligne par requête qui n'est ni la page d'accueil, ni `/sante`, ni une police ; de quoi voir ce que fait
un client qui n'arrive pas à se brancher, ou qui ne montre pas la fenêtre du mini blind test.

Ni adresse IP, ni contenu : la méthode HTTP, le chemin, le code de la réponse, la méthode MCP demandée (`initialize`,
`tools/list`…), l'outil appelé, le genre de ressource lue (`ui://honear`, `honear://listes`, jamais l'identifiant d'une liste),
le logiciel qui se présente, ce qu'il dit savoir faire (ses capacités, et pour une extension, ses types MIME), la version du
protocole, si la requête donne une session, et les en-têtes Origin, Accept et User-Agent. Les journaux des bibliothèques, qui
garderaient ce contenu, n'écrivent que leurs avertissements (`regler_les_journaux`).
"""

import logging
import re

from pydantic import JsonValue, TypeAdapter, ValidationError
from starlette.datastructures import Headers
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from honear_mcp.ressources.reglages import SERVEUR

JOURNAL = logging.getLogger("honear_mcp.journal")
BAVARDS = ("httpx2", "mcp")
"""Les journaux des bibliothèques, qui n'écrivent que leurs avertissements : celui de httpx2 garderait chaque adresse demandée
à Deezer (ce que quelqu'un cherche) ; celui du SDK, le texte d'un refus (les titres demandés), l'adresse d'une ressource
(l'identifiant d'une liste) et l'identifiant de chaque session."""
_JSON: TypeAdapter[JsonValue] = TypeAdapter(JsonValue)
_METHODE = re.compile(rb'"method"\s*:\s*"([A-Za-z0-9_/.-]{1,64})"')
_ENTETES = {"origine": "origin", "accepte": "accept", "logiciel": "user-agent", "version": "mcp-protocol-version"}
_ENVELOPPE = "io.modelcontextprotocol/"
_GENRE = re.compile(r"[a-z][a-z0-9+.-]*://[^/?#]*")
"""Le début de l'adresse d'une ressource, jusqu'à son hôte : le genre (`honear://listes`), jamais l'identifiant."""


def _entete(entetes: Headers, nom: str) -> str:
    """Un en-tête tel qu'il est venu, coupé, sur une seule ligne ; un tiret s'il manque."""
    return _court(entetes.get(nom, "-"))


def _court(valeur: str) -> str:
    return valeur[: SERVEUR.journal_entete_au_plus].replace("\n", " ").replace("\r", " ")


def _dict(valeur: JsonValue) -> dict[str, JsonValue]:
    return valeur if isinstance(valeur, dict) else {}


def _capacites(capacites: JsonValue) -> str:
    """Ce qu'un client dit savoir faire : ses capacités, et le détail de ses extensions (leurs types MIME)."""
    morceaux = []
    for nom, valeur in sorted(_dict(capacites).items()):
        if nom in {"extensions", "experimental"} and isinstance(valeur, dict):
            detail = (f"{n}:{'|'.join(map(str, _types(v)))}" for n, v in sorted(valeur.items()))
            morceaux.append(f"{nom}({','.join(detail)})")
        else:
            morceaux.append(nom)
    return ",".join(morceaux) or "-"


def _types(extension: JsonValue) -> list[JsonValue]:
    types = _dict(extension).get("mimeTypes")
    return types if isinstance(types, list) else []


def _ce_que_dit_le_corps(corps: bytes) -> dict[str, str]:
    """La méthode MCP du corps ; et s'il se lit en entier, l'outil, le genre de ressource, le client et ses capacités."""
    try:
        message = _dict(_JSON.validate_json(corps))
    except ValidationError:
        message = {}
    if not message:
        return {"mcp": ",".join(m.decode() for m in _METHODE.findall(corps)) or "-"}
    params = _dict(message.get("params"))
    meta = _dict(params.get("_meta"))
    client = _dict(params.get("clientInfo") or meta.get(_ENVELOPPE + "clientInfo"))
    capacites = params.get("capabilities") or meta.get(_ENVELOPPE + "clientCapabilities")
    adresse = params.get("uri")
    dit = {
        "mcp": str(message.get("method", "-")),
        "outil": str(params.get("name", "-")) if message.get("method") == "tools/call" else "-",
        "ressource": genre.group(0) if isinstance(adresse, str) and (genre := _GENRE.match(adresse)) else "-",
        "client": f"{client.get('name', '-')}/{client.get('version', '-')}" if client else "-",
        "capacites": _capacites(capacites) if capacites is not None else "-",
    }
    return {cle: _court(valeur) for cle, valeur in dit.items()}


def regler_les_journaux() -> None:
    """Le nôtre écrit chaque requête ; ceux des bibliothèques (`BAVARDS`), que leurs avertissements."""
    for nom in BAVARDS:
        logging.getLogger(nom).setLevel(logging.WARNING)
    JOURNAL.setLevel(logging.INFO)


def journaliser(app: ASGIApp) -> ASGIApp:
    """`app`, dont chaque requête HTTP laisse une ligne au journal quand sa réponse commence."""

    async def journalise(scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await app(scope, receive, send)
            return
        corps = bytearray()

        async def lire() -> Message:
            message = await receive()
            if message["type"] == "http.request" and len(corps) < SERVEUR.journal_lu_au_plus:
                corps.extend(message.get("body", b"")[: SERVEUR.journal_lu_au_plus - len(corps)])
            return message

        async def envoyer(message: Message) -> None:
            if message["type"] == "http.response.start":
                entetes = Headers(scope=scope)
                ligne = {"http": scope["method"], "chemin": _court(scope["path"]), "code": str(message["status"])}
                ligne |= _ce_que_dit_le_corps(bytes(corps)) if corps else {"mcp": "-"}
                ligne["session"] = "oui" if "mcp-session-id" in entetes else "non"
                ligne |= {cle: _entete(entetes, nom) for cle, nom in _ENTETES.items()}
                JOURNAL.info(" ".join(f"{cle}={valeur!r}" for cle, valeur in ligne.items()))
            await send(message)

        await app(scope, lire, envoyer)

    return journalise
