# BD2 Guide Parfait

Guide Brown Dust 2 personnalisé (compte Celia + Kyouka 80), en français.

Ouvre `index.html` dans un navigateur : tout fonctionne en local, sans serveur.

## Contenu

- **Horloge du jeu** : reset quotidien, Rapport, semaine de jeu, Mirror Wars, Golden Colosseum, Fiend Hunter (boss et élément conseillé), Guild Raid, Season Event, shops, saison de 28 jours, Soul Wager, boutiques mensuelles, bannières. Tout est calculé en direct, à l'heure locale.
- **Plan de compte** : qui monter, cibles long terme, nombre de teams par mode, budget Dia et pulls, usage de chaque ressource.
- **Guide complet** : combat, gacha, Pub, progression, gear, tous les modes, toutes les boutiques.
- **Routine** qui se décoche toute seule à chaque reset (jour, semaine, event, mois, saison, Soul Wager).
- **FAQ** d'une centaine de questions.
- **Bases de données** : 187 costumes (avis de bannière traduits), réponses de Rapport, boss du Fiend Hunter, glossaire.
- **Recherche** en haut de page : pose ta question, `/` pour y aller, `Entrée` pour ouvrir le premier résultat.

## Mettre à jour les données

```bash
python scripts/build_data.py
```

Le script clone (ou met à jour) les sources communautaires dans `.sources/` puis régénère `data/*.js` :

- [Tactical Compendium](https://github.com/BotAn14XD/BD2-Overview) : fiches costumes, Rapport, boss du Fiend Hunter, glossaire, calendrier.
- [Banner Recommendation](https://github.com/zormolo/BD2-Banner-Recommendation) : bannières actives et avis.

Les traductions (avis, définitions, obtention) sont dans `scripts/build_data.py`. Les textes du guide sont dans `index.html`.
