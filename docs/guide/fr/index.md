# Babakoto

Babakoto est un projet Apache-2.0 pour héberger des agents vocaux en malgache.
Le navigateur transmet l'appel au worker LiveKit via WebRTC. Le worker détecte
la parole avec Silero VAD, la transcrit, transmet le texte au modèle de langage
configuré et lit la réponse de synthèse vocale.

Le projet est en phase de préversion. L'interface d'essai affiche les sous-titres
et la latence de chaque réponse. On peut interrompre l'agent pendant qu'il parle.
Les agents enregistrés peuvent utiliser une consigne, un message d'accueil et des
documents privés. La validation des appels, de la reconnaissance vocale et de la
qualité de la voix sur des données approuvées est en cours.

- [Installer l'interface d'essai](installation.md)
- [Configurer un agent et exploiter le service](exploitation.md)
- [Read the English guide](../index.md)
