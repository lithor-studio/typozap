# ⚡ TypoZap

**Zappez vos fautes instantanément !**

TypoZap est un correcteur orthographique intelligent pour Windows qui corrige votre texte à la volée, n'importe où dans le système. Sélectionnez, zappez, c'est corrigé !

![TypoZap Logo](logo.svg)

## ✨ Fonctionnalités

- ⚡ **Correction instantanée** - Ctrl+Shift+C pour zapper les fautes
- 🎯 **Fonctionne partout** - Word, navigateur, email, messagerie...
- 🎨 **5 styles de correction**
  - Standard : Correction simple
  - Formel : Style professionnel
  - Informel : Ton décontracté
  - Concis : Version courte
  - Détaillé : Version enrichie
- 🔄 **Remplacement automatique** - Le texte est corrigé directement
- 📋 **Gestion intelligente du presse-papier** - Votre presse-papier est préservé
- 🌐 **IA locale avec Ollama** - Pas besoin d'internet

## 🚀 Installation rapide

### Méthode 1 : Télécharger l'exécutable (Recommandé)

1. Téléchargez `TypoZap.exe` depuis la [page des releases](https://github.com/votre-username/typozap/releases)
2. Installez [Ollama](https://ollama.ai)
3. Téléchargez un modèle : `ollama pull llama3.2`
4. Lancez `TypoZap.exe`

### Méthode 2 : Installation depuis les sources

```bash
# Cloner le repo
git clone https://github.com/votre-username/typozap.git
cd typozap

# Installer les dépendances
pip install -r requirements.txt

# Installer Ollama et télécharger un modèle
ollama pull llama3.2

# Lancer TypoZap
python typozap.py
```

## 📖 Utilisation

1. **Démarrez TypoZap** - Une icône éclair ⚡ apparaît dans la barre des tâches
2. **Sélectionnez du texte** avec des fautes n'importe où
3. **Appuyez sur Ctrl+Shift+C** - Le texte est corrigé instantanément !

### Via le menu contextuel

- Clic droit sur l'icône ⚡
- Choisissez un style de correction
- Le texte est corrigé selon le style choisi

## ⚙️ Configuration

### Changer le modèle Ollama

Dans `typozap.py` ligne 52 :
```python
self.model = "llama3.2"  # ou "mistral", "llama3.2:1b", etc.
```

### Modèles recommandés

- `llama3.2` - Rapide et précis (recommandé)
- `mistral` - Excellent pour le français
- `llama3.2:1b` - Ultra-rapide et léger

### Changer le raccourci clavier

Dans `typozap.py` ligne 217 :
```python
keyboard.HotKey.parse('<ctrl>+<shift>+c')  # Modifiez ici
```

## 🔧 Compiler l'exécutable

```bash
# Installer les dépendances de build
pip install pyinstaller pillow

# Créer l'icône
python create_icon.py

# Compiler
pyinstaller typozap.spec

# L'exécutable est dans dist/TypoZap.exe
```

Ou simplement :
```bash
build.bat
```

## 🌟 Lancement au démarrage

1. Appuyez sur `Win+R`
2. Tapez `shell:startup` et validez
3. Créez un raccourci vers `TypoZap.exe` dans ce dossier

## 🐛 Dépannage

### "Aucun texte sélectionné"
- Vérifiez que vous sélectionnez bien le texte AVANT d'appuyer sur le raccourci
- Essayez d'augmenter le délai dans ClipboardWorker (ligne 130)

### "Ollama indisponible"
- Vérifiez qu'Ollama est démarré : `ollama list`
- Testez la connexion : `curl http://localhost:11434/api/tags`

### Le raccourci ne fonctionne pas
- Lancez TypoZap en tant qu'administrateur
- Vérifiez qu'aucune autre application n'utilise Ctrl+Shift+C

## 📝 Contribuer

Les contributions sont les bienvenues ! N'hésitez pas à :
- 🐛 Signaler des bugs
- 💡 Proposer de nouvelles fonctionnalités
- 🔧 Soumettre des pull requests

## 📄 Licence

MIT License - Libre d'utilisation et de modification

## 🙏 Remerciements

- [Ollama](https://ollama.ai) - Pour l'IA locale
- [PyQt5](https://www.riverbankcomputing.com/software/pyqt/) - Pour l'interface
- Tous les contributeurs !

---

**Fait avec ⚡ par la communauté**