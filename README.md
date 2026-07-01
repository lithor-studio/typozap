# ⚡ TypoZap

Correcteur français local pour Windows et macOS. Sélectionnez un texte, utilisez le raccourci global et TypoZap le corrige sans envoyer son contenu vers un service distant.

## Fonctionnalités

- correction standard, formelle, informelle, concise ou détaillée ;
- `Ctrl+Shift+C` sous Windows et `⌘⇧C` sous macOS ;
- moteur local TypoZap embarqué avec repli Ollama pour le développement ;
- Ministral 3 3B Instruct Q4_K_M, environ 2,15 Go ;
- téléchargement reprenable et vérifié au premier lancement ;
- préservation des différents formats du presse-papier ;
- annulation automatique si l'utilisateur copie autre chose pendant une correction ;
- une seule correction active à la fois.

## Installation depuis les sources

```bash
python -m pip install -r requirements.txt
```

Pour le mode de développement avec Ollama :

```bash
ollama pull ministral-3:3b
ollama create typozap-mistral-fr -f Modelfile
python typozap.py
```

Le moteur embarqué est utilisé automatiquement lorsque `runtime/typozap-engine` (ou `runtime/typozap-engine.exe`) et le modèle sont disponibles. Les chemins peuvent être remplacés avec `TYPOZAP_ENGINE` et `TYPOZAP_MODEL_PATH`.

## Utilisation

1. Lancez TypoZap.
2. Sélectionnez du texte dans une application.
3. Utilisez `Ctrl+Shift+C` sous Windows ou `⌘⇧C` sous macOS.

Si vous copiez une autre donnée pendant la correction, TypoZap annule le remplacement et conserve votre nouvelle copie. Le mode aperçu est disponible depuis l'icône de la barre système.

Sous macOS, autorisez TypoZap dans **Réglages Système → Confidentialité et sécurité → Accessibilité** lorsque le système le demande.

## Tests

Tests rapides, sans modèle :

```bash
python -m unittest discover -v
```

Tests d'acceptation réels avec Ollama et `typozap-mistral-fr` :

```bash
# macOS/Linux
TYPOZAP_TEST_MODEL=1 python -m unittest tests.test_model_acceptance -v

# Windows PowerShell
$env:TYPOZAP_TEST_MODEL="1"; python -m unittest tests.test_model_acceptance -v
```

La CI exécute les tests sous Windows, macOS et Linux avec Python 3.10 et 3.12.

## Construction

### Windows

1. Placez le binaire officiel du moteur dans `runtime/` sous le nom `typozap-engine.exe`.
2. Exécutez `build.bat`.
3. Compilez `installer/windows/TypoZap.iss` avec Inno Setup.

### macOS

1. Placez le binaire du moteur correspondant à l'architecture dans `runtime/` sous le nom `typozap-engine`.
2. Rendez le script exécutable puis lancez `./build_macos.sh`.
3. Signez et notarisez `dist/TypoZap.app` avant publication.

Le modèle n'est pas inclus dans l'installateur léger. Il est téléchargé depuis le dépôt officiel Mistral au premier lancement et vérifié par SHA-256.

## Confidentialité

Les corrections sont effectuées localement. TypoZap ne collecte pas les textes sélectionnés. Une connexion est uniquement nécessaire pour télécharger le modèle lors de la première installation.

## Licence

Le code de TypoZap est sous licence MIT. Ministral 3 et `llama.cpp` conservent leurs licences respectives, qui doivent accompagner les distributions.
