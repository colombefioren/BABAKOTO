# Lancer l'interface d'essai en local

Installez Docker avec Compose, Node.js, pnpm, uv et just sur la machine qui
hébergera le service.

```sh
git clone https://github.com/colombefioren/BABAKOTO.git && cd BABAKOTO
just dev
just up cpu
```

Après `just dev`, renseignez `GLADIA_API_KEY` et les paramètres du modèle de
langage dans le fichier local `.env`, puis lancez le profil CPU. Le fichier
contient aussi les identifiants locaux de LiveKit, des services et de
l'opérateur. Le profil CPU envoie le son du microphone à Gladia et joue par
défaut un signal sonore de test. La commande attend que le worker s'enregistre
auprès de LiveKit.
[Conservation des données chez Gladia](https://eu1.docs.gladia.io/data/retention/)

Sur la machine hôte, ouvrez [localhost:3000](http://localhost:3000). Connectez-vous
avec le nom `babakoto` et le mot de passe `WEB_PLAYGROUND_PASSWORD` de `.env`.
Autorisez l'accès au microphone, puis cliquez sur **Start conversation**. Pour
arrêter le service, lancez `just down`. Le volume de la base de données et les
caches sont conservés.

## Activer la reconnaissance vocale locale

Installez le pilote NVIDIA et NVIDIA Container Toolkit. Acceptez les conditions
d'accès à Sunflower sur Hugging Face. Configurez `HF_TOKEN` et le commit exact
`SUNFLOWER_MODEL_REVISION` dans `.env`. Lancez `just down`, puis `just up gpu`.
Le profil GPU utilise Sunflower en local par défaut. Le texte transcrit est
transmis au modèle de langage choisi.

## Ouvrir le tableau de bord

Lancez `just up-dashboard` pour démarrer l'API privée et PostgreSQL. Ouvrez
**Agent configurations** depuis l'interface d'essai. Le tableau de bord peut
fonctionner indépendamment des services vocaux.

[Paramètres disponibles](https://github.com/colombefioren/BABAKOTO/blob/main/.env.example)
