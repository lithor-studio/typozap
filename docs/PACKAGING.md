# Publication de TypoZap

## Ressources requises

- Windows x64 : `runtime/typozap-engine.exe` et ses bibliothèques natives associées.
- macOS Apple Silicon : `runtime/typozap-engine` arm64.
- macOS Intel : `runtime/typozap-engine` x64.
- Ne jamais mélanger des bibliothèques provenant de releases différentes.

Le seul modèle pris en charge est `Ministral-3-3B-Instruct-2512-Q4_K_M.gguf`, téléchargé à la demande depuis le dépôt officiel Mistral. Son URL, sa taille et son SHA-256 sont figés dans `src/typozap/model_installer.py`. Aucun fallback Ollama ni modèle configurable ne doit être ajouté au paquet.

## Windows

1. Construire l'exécutable sur Windows avec `scripts/build_windows.bat`.
2. Tester l'exécutable sur une machine Windows propre.
3. Compiler `packaging/windows/TypoZap.iss` avec Inno Setup.
4. Signer l'exécutable et l'installateur avec le certificat de signature de code.
5. Tester installation, premier téléchargement, correction et désinstallation.

## macOS

1. Construire séparément sur Intel et Apple Silicon, ou produire une application universelle.
2. Exécuter `scripts/build_macos.sh`.
3. Signer les binaires natifs et l'application avec Developer ID.
4. Notariser puis agrafer le ticket Apple.
5. Tester les permissions Accessibilité sur un compte neuf.

## Critères de publication

- suite unitaire verte sur les trois systèmes ;
- corpus français réel validé avec le modèle livré ;
- nouvelle copie utilisateur jamais écrasée ;
- réponse tronquée jamais collée dans le document ;
- erreur moteur jamais collée dans le document ;
- empreinte du modèle vérifiée ;
- installateur et désinstallateur testés sur machine propre ;
- licences MIT, Apache-2.0 et licence `llama.cpp` incluses.
