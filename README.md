# ⚡ TypoZap

Correcteur français local pour Windows et macOS. Sélectionnez un texte, utilisez le raccourci global et TypoZap le corrige sans envoyer son contenu à un service distant.

## Principes

- un seul modèle : **Ministral 3 3B Instruct 2512 Q4_K_M** ;
- un seul moteur local `llama.cpp`, livré avec l'application ;
- aucun service cloud, compte ou serveur Ollama ;
- téléchargement reprenable et vérifié du modèle au premier lancement ;
- presse-papier transactionnel : tous les formats initiaux sont restaurés et une copie utilisateur reste toujours prioritaire ;
- refus automatique des sélections trop longues et des réponses tronquées.
- découpage automatique des textes longs par paragraphes ;
- aperçu des différences avec acceptation ou refus de chaque modification ;
- annulation rapide de la dernière correction ;
- dictionnaire personnel, guide de style, ton personnalisé et mode strict ;
- profils automatiques selon l'application active ;
- explication locale optionnelle des corrections ;
- statistiques et journal technique sans contenu utilisateur ;
- historique local optionnel, limité à 20 entrées et chiffré par Windows DPAPI.
- démarrage du modèle à la demande et mise en veille automatique pour libérer la mémoire.

## Installation depuis les sources

```bash
python -m pip install -e .
python -m typozap
```

Le binaire officiel `llama-server` doit être placé dans `runtime/` sous le nom `typozap-engine.exe` sous Windows ou `typozap-engine` sous macOS.

Le modèle n'est pas configurable : TypoZap télécharge et utilise exclusivement `Ministral-3-3B-Instruct-2512-Q4_K_M.gguf` dans son répertoire de données utilisateur.

## Utilisation

1. Lancez TypoZap et installez le modèle lors du premier démarrage.
2. Sélectionnez du texte dans une application.
3. Utilisez `Ctrl+Shift+F8` sous Windows ou `⌃⌥C` sous macOS.

Le raccourci Windows évite volontairement `Ctrl+Shift+C`, réservé à l'insertion de code dans Microsoft Teams.
Il peut être modifié depuis l'icône TypoZap → **Configurer le raccourci…** ; le choix est conservé entre les lancements.

TypoZap sauvegarde le presse-papier avant la capture. Des marqueurs privés permettent de détecter toute copie effectuée pendant la correction ou le collage, y compris une copie contenant exactement le même texte. Dans ce cas, la copie utilisateur est conservée et TypoZap annule sa restauration.

Les réglages d'écriture sont accessibles depuis **Préférences d'écriture…**. Les profils applicatifs utilisent le titre de la fenêtre active, par exemple `Teams=informel` ou `Outlook=formel`. Le titre sert uniquement au choix du profil et n'est pas journalisé.

Dans l'onglet **Performance**, le moteur peut être arrêté après 1, 5 ou 15 minutes d'inactivité. La première correction suivant une mise en veille prend quelques secondes supplémentaires, le temps de recharger Ministral.

Le journal technique est enregistré dans `%LOCALAPPDATA%\TypoZap\logs` sous Windows. Il contient les durées et erreurs techniques, jamais le texte traité. L'historique de contenu est désactivé par défaut.

Sous macOS, autorisez TypoZap dans **Réglages Système → Confidentialité et sécurité → Accessibilité**.

## Tests

```bash
python -m unittest discover -v
```

Test d'acceptation avec le runtime et le modèle réellement installés :

```powershell
$env:TYPOZAP_TEST_MODEL="1"; python -m unittest tests.test_model_acceptance -v
```

## Organisation

```text
src/typozap/       interface, moteur, correction et presse-papier
tests/             tests unitaires et corpus français
scripts/           lancement et construction locale
packaging/         PyInstaller et installateur Windows
docs/              documentation de publication
```

## Construction

### Windows

1. Placez le runtime `llama.cpp` dans `runtime/`.
2. Exécutez `scripts/build_windows.bat`.
3. Compilez `packaging/windows/TypoZap.iss` avec Inno Setup.

### macOS

1. Placez le runtime correspondant à l'architecture dans `runtime/`.
2. Lancez `./scripts/build_macos.sh`.
3. Signez et notarisez `dist/TypoZap.app` avant publication.

## Confidentialité

Les corrections sont entièrement locales. La connexion réseau sert uniquement au téléchargement initial du modèle officiel.

## Licence

Le code de TypoZap est sous licence MIT. Ministral 3 et `llama.cpp` conservent leurs licences respectives.
