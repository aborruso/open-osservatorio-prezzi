# Procedura di rilascio

Il pacchetto si chiama `openosservaprezzi` su PyPI ed è la fonte da cui gli utenti installano (`uv tool install openosservaprezzi`). Un tag su GitHub senza la pubblicazione su PyPI non è un rilascio: chi installa riceve ancora la versione precedente. Per questo ogni passaggio della lista va fatto, in ordine.

## Versioni

Versionamento semantico. Una correzione senza cambi di interfaccia è una patch (`0.4.1` → `0.4.2`); un comando, un'opzione o un campo nuovo è una minor (`0.4.2` → `0.5.0`).

## Prerequisiti

- `twine` con le credenziali PyPI in `~/.pypirc`
- `gh` autenticato

## Passaggi

```bash
# 1. Versione, in due punti
#    pyproject.toml           version = "X.Y.Z"
#    src/osservaprezzi/__init__.py   __version__ = "X.Y.Z"

# 2. Lockfile
uv lock

# 3. CHANGELOG.md: la sezione [Non rilasciato] diventa [X.Y.Z] — AAAA-MM-GG
#    LOG.md: una riga con la versione

# 4. Test: devono passare prima di qualunque pubblicazione
uv run pytest

# 5. Commit e tag annotato
git add -u
git commit -m "Versione X.Y.Z"
git tag -a vX.Y.Z -m "titolo breve della versione"

# 6. Push di branch e tag
git push origin main
git push origin vX.Y.Z

# 7. Release su GitHub, con le note prese dal CHANGELOG
gh release create vX.Y.Z --title "vX.Y.Z" --notes-file note.md

# 8. Build e pubblicazione su PyPI
uv build
twine upload dist/openosservaprezzi-X.Y.Z*

# 9. Verifica del pacchetto PUBBLICATO, non del sorgente: uvx installa da PyPI
#    in un ambiente usa e getta, cioè quello che riceve un utente nuovo. Una
#    dipendenza importata ma non dichiarata funziona in locale e si rompe per
#    gli altri. --refresh evita l'indice in cache: subito dopo l'upload la
#    versione può non risolversi al primo tentativo.
uvx --refresh --from openosservaprezzi==X.Y.Z osservaprezzi agent-context --agent
uvx --from openosservaprezzi==X.Y.Z osservaprezzi catalog --agent

# 10. CLI locale
uv tool install --reinstall .
```

## Lista di controllo

- [ ] Versione in `pyproject.toml` e in `src/osservaprezzi/__init__.py`
- [ ] `uv.lock` aggiornato
- [ ] `CHANGELOG.md` e `LOG.md` aggiornati
- [ ] Test verdi (`uv run pytest`)
- [ ] Commit e tag annotato `vX.Y.Z`
- [ ] Push di `main` e del tag
- [ ] Release su GitHub (`gh release create`)
- [ ] Pubblicato su PyPI (`uv build && twine upload`)
- [ ] Pacchetto pubblicato installato e provato con `uvx`
- [ ] CLI locale reinstallata
