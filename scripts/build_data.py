#!/usr/bin/env python3
"""Régénère les fichiers data/*.js du guide à partir des sources communautaires.

Sources :
  - Tactical Compendium (BotAn) : https://github.com/BotAn14XD/BD2-Overview
  - Banner Recommendation (zormolo & BotAn) : https://github.com/zormolo/BD2-Banner-Recommendation

Usage :
  python scripts/build_data.py                  # clone ou met à jour les sources dans .sources/
  python scripts/build_data.py --tc DIR --banner DIR

Les textes en français (avis, définitions, obtention) sont dans ce fichier.
Un costume ou un terme absent des dictionnaires garde un texte généré automatiquement.
"""
import argparse
import html
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / 'data'
CACHE = ROOT / '.sources'

TC_REPO = 'https://github.com/BotAn14XD/BD2-Overview.git'
BANNER_REPO = 'https://github.com/zormolo/BD2-Banner-Recommendation.git'


# ---------------------------------------------------------------- traductions

ELEMENT = {'fire': 'feu', 'water': 'eau', 'wind': 'vent', 'light': 'lumiere', 'dark': 'tenebres'}
DMG = {'physical': 'phys', 'magic': 'mag'}
DMG_ATT = {'f': 'feu', 'wa': 'eau', 'wi': 'vent', 'l': 'lumiere', 'd': 'tenebres'}

ROLES = {'DPS': 'DPS', 'debuffer': 'Débuffer', 'support': 'Support', 'chainer': 'Chainer',
         'buffer': 'Buffer', 'tank': 'Tank'}

EFFETS = {
    'mediumAOE': 'AoE moyenne', 'smallAOE': 'Petite AoE', 'bigAOE': 'Grande AoE',
    'conditionalDamage': 'Dégâts conditionnels', 'dot': 'DoT', 'spRegen': 'Rend du SP',
    'physAttackSelfAmp': 'Buff ATK sur soi', 'barrierSelfAmp': 'Barrière sur soi',
    'hpScalingDamage': 'Dégâts sur ses PV', 'fixedDamage': 'Dégâts fixes',
    'dispelBuff': 'Retire les buffs ennemis', 'magicAttackAmp': 'Buff MATK',
    'mainTargetDamage': 'Dégâts sur la cible principale', 'barrierAmp': 'Barrière alliée',
    'physAttackAmp': 'Buff ATK', 'silence': 'Silence', 'preemptive': 'Préemptif',
    'critDmgSelfAmp': 'Crit DMG sur soi', 'critDMGSelfAmp': 'Crit DMG sur soi', 'heal': 'Soin',
    'healSelf': 'Soin sur soi', 'mresDebuff': 'Baisse MRES', 'defDebuff': 'Baisse DEF',
    'knockback': 'Knockback', 'energyGuardSelfAmp': 'Energy Guard sur soi',
    'critRateSelfAmp': 'Crit Rate sur soi', 'evasionSelf': 'Esquive', 'evasionSelfAmp': 'Esquive',
    'selfHpConsumption': 'Consomme ses PV', 'spDrain': 'Vole du SP', 'taunt': 'Taunt',
    'counter': 'Contre-attaque', 'propertyDmgAmp': 'Buff dégâts d\'élément',
    'magicAttackSelfAmp': 'Buff MATK sur soi', 'critRateAmp': 'Buff Crit Rate',
    'percentageDamage': 'Dégâts en % des PV', 'focusFire': 'Tir concentré',
    'physVulnerability': 'Vulnerability physique', 'physAttackDebuff': 'Baisse ATK ennemie',
    'summon': 'Invocation', 'vulnerability': 'Vulnerability', 'dispelDebuff': 'Retire les debuffs',
    'propertyDmgSelfAmp': 'Dégâts d\'élément sur soi', 'cooldownReductionSelf': 'Réduit son cooldown',
    'critRate': 'Buff Crit Rate', 'magicAttackDebuff': 'Baisse MATK ennemie',
    'chainReinforcementSelf': 'Chain Reinforcement', 'domain': 'Domaine', 'dmgSelfAmp': 'Dégâts sur soi',
    'dmgAmp': 'Augmentation des dégâts', 'magicVulnerability': 'Vulnerability magique',
    'conditionalDmgAmp': 'Augmentation conditionnelle', 'energyGuardAmp': 'Energy Guard alliée',
    'critDmgAmp': 'Buff Crit DMG', 'spCostIncreaseSelf': 'Coût SP qui augmente',
    'bleedDispel': 'Retire Bleed', 'energyGuard': 'Energy Guard', 'revive': 'Résurrection',
    'chainRetention': 'Chain Retention', 'energyGuardScalingDamage': 'Dégâts sur Energy Guard',
    'buffDurationExtendSelf': 'Prolonge ses buffs', 'cooldownReduction': 'Réduit les cooldowns',
    'chainDmgSelfAmp': 'Dégâts de chain sur soi', 'reactiveVulnerability': 'Vulnerability réactive',
    'spConsumption': 'Consomme du SP', 'summonsVulnerability': 'Vulnerability des invocations',
    'DPS': 'Dégâts', 'mark': 'Marque', 'attackDebuff': 'Baisse ATK ennemie',
    'debuffDurationIncrease': 'Prolonge les debuffs', 'dispelShield': 'Retire les boucliers',
    'spCostReduction': 'Réduit les coûts SP', 'chainReinforcement': 'Chain Reinforcement allié',
    'aura': 'Aura', 'dotVulnerability': 'Vulnerability DoT', 'reactiveDmgAmp': 'Augmentation réactive',
    'darkVulnerability': 'Vulnerability Ténèbres', 'buffDurationSelfIncrease': 'Prolonge ses buffs',
    'windVulnerability': 'Vulnerability Vent', 'pureDamage': 'Dégâts purs', 'selfDestruct': 'Autodestruction',
}

POTS = {'SP -1': '-1 SP', 'Range Up': 'Portée +', 'DEF Reduction': 'Baisse DEF', 'Barrier': 'Barrière',
        'Crit Rate Increase': 'Crit Rate +'}

PRIO = {'ur': 'must', 'sr': 'reco', 'r': 'situ', 'n': 'skip'}
MODE = {'Meta': 'Méta', 'Good': 'Bon', 'Niche': 'Niche', 'Bad': 'Mauvais'}

# Clés des avis Banner Recommendation -> nom complet du costume
AVIS_NOMS = {
    'innocent_bunny': 'Innocent Bunny Tyr', 'bittersweet_bunny': 'Bittersweet Bunny Darian',
    'celebrity_bunny': 'Celebrity Bunny Loen', 'masquerade_bunny': 'Masquerade Bunny Celia',
    'overheat': 'Overheat Levia', 'robin_hood': 'Robin Hood Zenith', 'vanguard': 'Vanguard Gray',
    'queen_of_gluttis': 'Queen of Gluttis Granadair', 'snow_white': 'Snow White Ventana',
    'shrine_maiden_of_purification': 'Shrine Maiden of Purification Granadair',
    'onsen_manager': 'Onsen Manager Liberta', 'onsen_practitioner': 'Onsen Practitioner Ventana',
    'the_fiend_scholar': 'The Fiend Scholar Olstein', 'onsen_swordfighter': 'Onsen Swordfighter Blade',
    'sword_breaker': 'Sword Breaker Alec', 'apostle_blade': 'Apostle Blade',
    'magical_innovator': 'Magical Innovator Diana', 'maid_name_r': 'Maid Name R Liatris',
    'retired_legend': 'Retired Legend Olivier', 'acting_archbishop': 'Acting Archbishop Michaela',
    'shattered_dream': 'Shattered Dream Palette',
    'reclaimed_destiny_sacred_justia': 'Reclaimed Destiny Sacred Justia',
    'b-rank_idol_helena': 'B-Rank Idol Helena', 'night_of_death': 'Night of Death Mamonir',
    'bikini_agent': 'Bikini Agent Sylvia', 'kind_ruthlessness': 'Kind Ruthlessness Hikage',
    'noble_flame': 'Noble Flame Ikaruga', 'fist_of_conviction': 'Fist of Conviction Yozakura',
    'dancing_snowflake': 'Dancing Snowflake Yumi', 'shadowed_dream': 'Shadowed Dream Sonya',
    'miracle_rose': 'Miracle Rose Liberta', 'maid_bikini': 'Maid Bikini Rubia',
    'miracle_violet': 'Miracle Violet Palette', 'dj': 'DJ Venaka', 'miracle_marine': 'Miracle Marine Mamonir',
    'beach_vacation_morpeah': 'Beach Vacation Morpeah', 'ocean_vanguard': 'Ocean Vanguard Luvencia',
    'deadeye': 'Deadeye Nekyndalia', 'beachside_justice': 'Beachside Justice Michaela',
    'prophetic_dream': 'Prophetic Dream Darian', 'pool_party_justia': 'Pool Party Justia',
    'pool_party_scheherazade': 'Pool Party Scheherazade', 'beachside_angel': 'Beachside Angel Teresse',
    'combat_medic': 'Combat Medic Granhildr', 'b-rank_idol_seir': 'B-Rank Idol Seir',
    'naive_lady': 'Naive Lady Elise', 'pool_party_gray': 'Pool Party Gray',
    'steel_engine': 'Steel Engine Rafina', 'laid-back_lifeguard': 'Laid-back Lifeguard Nebris',
    'tricky_lover': 'Tricky Lover Dalvi', 'anonymous_sage': 'Anonymous Sage Nartas',
    'angel_of_destruction': 'Angel of Destruction Teresse',
    'heavenly_guardian_successor': 'Heavenly Guardian Successor Glacia',
    'lonely_survivor': 'Lonely Survivor Lathel', 'killer_doll': 'Killer Doll Lecliss',
    'comeback_idol_yuri': 'Comeback Idol Yuri', 'the_sword_queen': 'The Sword Queen Sylvia',
    'sunny_inn_hand': 'Sunny Inn Hand Helena', 'the_destruction': 'The Destruction Alec',
    'bright_moon': 'Bright Moon Dalvi', 'savage_warrior': 'Savage Warrior Aquila',
    'young_lady': 'Young Lady Blade', 'ame-no-mitori': 'Ame-no-Mitori Tenka Izumo',
    'piercing_magic_bow': 'Piercing Magic Bow Eleaneer', 'lord_of_the_cosmos': 'Lord of the Cosmos Ren Yamashiro',
    'faithful_wings': 'Faithful Wings Olivier', 'medical_club': 'Medical Club Teresse',
}

# Avis traduits : (texte, [breakpoints])
AVIS_FR = {
    'Innocent Bunny Tyr': ("Bonne seulement si tu as Starlight Guardian Tyr, sinon usage limité. Peu de copies, garde tes pulls.", ['+2 : dégâts 1160 → 1400 % (8 SP)', '+4 : dégâts 1450 → 1690 % (8 SP)']),
    'Bittersweet Bunny Darian': ("Limitée. Moins prioritaire que Celia ou Loen : son skill conditionnel limite son usage.", ['+1 : -1 SP', '+2 : -2 CD']),
    'Celebrity Bunny Loen': ("Limitée. Un des meilleurs DPS de contenu général, très fort contre beaucoup d'ennemis.", ['+1 : -1 SP']),
    'Masquerade Bunny Celia': ("Limitée. Support-chainer présent dans presque chaque saison de Fiend Hunter et Guild Raid, indispensable aux autres costumes de Celia.", ['+1 : -1 SP', '+4 : durée du buff +2 tours']),
    'Overheat Levia': ("Rebuffée, mais pas plus prioritaire que Tyr ou les autres bannières.", ['+1 : -1 SP']),
    'Robin Hood Zenith': ("Support important en Fiend Hunter et Guild Raid. À +3 (Potential fait) son skill devient gratuit.", ['+3 : -1 SP']),
    'Vanguard Gray': ("DPS DoT de niche qui scale sur la MATK ennemie. Endgame seulement.", ['+3 : -1 SP']),
    'Queen of Gluttis Granadair': ("Buffer magique clé, l'équivalent magique d'Homunculus Lathel. À prendre au maximum (aussi au Pub).", ['+1 : -1 SP']),
    'Snow White Ventana': ("Gros nuke, mais breakpoint à +3 et d'autres bannières passent avant.", ['+3 : -1 SP']),
    'Shrine Maiden of Purification Granadair': ("Buffer magique très puissant dans presque tous les modes : même valeur de buff qu'Onsen Liberta, sans condition de chains.", ['+1 : -1 SP']),
    'Onsen Manager Liberta': ("Rotation de Dark Saintess Liberta, bonus pour les teams à beaucoup de chains. Indispensable en Guild Raid, Fiend Hunter et Last Night.", ['+1 : -1 SP']),
    'Onsen Practitioner Ventana': ("Le plus faible des 3 costumes de Ventana (self-buff). Rotation en Fiend Hunter et Guild Raid.", ['+1 : -1 SP', '+3 : Vulnerability Lumière 100 → 200 %']),
    'The Fiend Scholar Olstein': ("Support de niche (SP, silence). Recrute-le au Pub (Story Pack 4) pendant sa bannière : 10 Draw Tickets.", ['+3 : -1 SP']),
    'Onsen Swordfighter Blade': ("DPS pur, légère synergie avec Young Lady, demande beaucoup d'investissement.", ['+1 : -1 SP', '+3 : dégâts conditionnels 70 → 90 %', '+5 : 90 → 110 %']),
    'Sword Breaker Alec': ("Unité PvP de niche. Skip.", ['+3 : -1 SP']),
    'Apostle Blade': ("DPS principal de Blade, gros plafond mais niche en PvE (contre-attaque). Pub du Story Pack 15 : 10 tickets pendant sa bannière.", ['+2 : hits de contre 8 → 10']),
    'Magical Innovator Diana': ("Buffer d'élément : +0 donne déjà 100 % de dégâts d'élément à stacks max. Les copies servent surtout aux rankers.", ['+0 : base suffisante']),
    'Maid Name R Liatris': ("Excellent DPS en FH/GR, mais depuis la hausse du plafond de DoT elle sert surtout au dernier tour : costume de ranking.", ['+2 : dégâts 400 → 475 % (cond. 600 → 675 %)', '+4 : 475 → 550 % (cond. 725 → 800 %)']),
    'Retired Legend Olivier': ("Rend Olivier plus complète en support. Son Domain buffe la MATK (elle ou une 2e team), mais ne se cumule pas avec celui d'Eleaneer.", ['+1 : -1 SP', '+2 : Domain MATK 60 → 80 %', '+4 : 80 → 100 %']),
    'Acting Archbishop Michaela': ("Self-buff inutile sans les autres costumes de Michaela (surtout Queen of Signatures). Pub aléatoire : 10 tickets pendant son rerun.", ['+1 : -1 SP', '+3 : durée Crit DMG 4 → 6 tours', '+4 : Crit DMG 400 → 500 %']),
    'Shattered Dream Palette': ("Bons dégâts même à faibles copies, extension de debuffs unique. 1 copie gratuite au Pub du Story Pack 20.", ['+1 : -1 SP']),
    'Reclaimed Destiny Sacred Justia': ("Très bon DPS AoE : ses dégâts montent avec le nombre d'ennemis. +4 pour lancer le skill chaque tour.", ['+1 : -1 SP', '+4 : -2 CD']),
    'B-Rank Idol Helena': ("Cœur de presque toutes les teams magiques. Prends +1 avec les Recommended Selective Tickets dès le début.", ['+3 : -1 SP']),
    'Night of Death Mamonir': ("DPS sur PV : faible coût, grande AoE, beaucoup de chains, gros dégâts. Pub aléatoire : 10 tickets pendant sa bannière.", ['+1 : -1 SP']),
    'Bikini Agent Sylvia': ("Nuke de Sylvia qui prolonge ses buffs, mais Sylvia dépend de Sword Queen : investissement discutable.", ['+1 : -1 SP']),
    'Kind Ruthlessness Hikage': ("Collab. Surtout Last Night, dépassée comme chainer par Wilhelmina. 1 ou 2 copies suffisent.", ['+1 : -1 SP', '+4 : -2 CD']),
    'Noble Flame Ikaruga': ("Faible. Peut-être en Golden Colosseum, et encore.", ['+1 : -1 SP', '+2 : self-buff 60 → 80 % ATK', '+4 : 80 → 100 %']),
    'Fist of Conviction Yozakura': ("Augmente l'attaque de base : pas d'AoE, dégâts moyens. Skip.", ['+1 : -1 SP', '+3 : Augmentation 400 → 650 %', '+5 : 650 → 900 %']),
    'Dancing Snowflake Yumi': ("Dépassée par presque tous les DPS Eau.", ['+1 : -1 SP', '+3 : Frostbite 10 → 15 %', '+5 : 15 → 20 %']),
    'Shadowed Dream Sonya': ("Excellent amplificateur, polyvalent, encore meilleur en Ténèbres. Ses cases s'alignent avec Little Pumpkin Girl.", ['+1 : -1 SP', '+2 et +4 : Vulnerability en hausse']),
    'Miracle Rose Liberta': ("Pas un buffer, mais un bon chainer à 1 SP qui comble le temps mort de Liberta. Excellente en PvP (Crit Rate).", ['+1 : -1 SP', '+3 : Crit Rate 40 → 70 %']),
    'Maid Bikini Rubia': ("Très importante pour les teams DoT (énorme buff), il faut un bon DPS DoT comme Liatris.", ['+1 : -1 SP', '+3 : Vulnerability DoT 150 → 200 %', '+5 : 200 → 250 %']),
    'Miracle Violet Palette': ("Colle très bien à une team Ténèbres magique, mais ses dégâts dépendent de cette team. Nécessaire à la rotation de Palette.", ['+1 : -1 SP']),
    'DJ Venaka': ("DPS correct qui baisse la MRES, mais écrasée par Nebris et Tyr côté Vent.", ['+1 : -1 SP']),
    'Miracle Marine Mamonir': ("Niche mais valeurs brutes énormes. Recommandée si tu as investi Mamonir, sinon optionnelle (+1 en compromis).", ['+1 : -1 SP']),
    'Beach Vacation Morpeah': ("Au moins +0 : meilleure DPS magique Eau (mai 2026). Ses dégâts montent beaucoup avec les copies. Gratuite via l'Event tab.", ['+0 : base']),
    'Ocean Vanguard Luvencia': ("Aide les autres costumes de Luvencia et stack des chains sur les tours creux. Buff permanent.", ['+1 : -1 SP', '+2 : plus d\'ATK par hit', '+4 : plus de dégâts de chain']),
    'Deadeye Nekyndalia': ("Surtout PvP pour l'instant (un seul costume). Beaucoup de chains : bien en Last Night.", ['+1 : -1 SP']),
    'Beachside Justice Michaela': ("Self-buff pour Queen of Signatures, mais coûte des PV et mauvaise zone.", ['+1 : -1 SP']),
    'Prophetic Dream Darian': ("Excellent DPS si elle touche assez de cases. Pilier de Last Night et des FH/GR où sa zone touche beaucoup.", ['+1 : -1 SP']),
    'Pool Party Justia': ("Self-buff pour dégâts fixes : faible hors PvP, et même en PvP Olivier l'a remplacée.", ['+3 : -1 SP']),
    'Pool Party Scheherazade': ("Stable en PvP. Débutant : 1 copie pour le skin, puis on passe.", ['+3 : -1 SP']),
    'Beachside Angel Teresse': ("Support indispensable, magique comme physique. Son Augmentation est peu diluée. Seul défaut : pousse vers des teams à peu de chains.", ['+1 : -1 SP', '+3 : durée 4 → 8 tours']),
    'Combat Medic Granhildr': ("Si Granhildr est déjà montée : +3 pour le self-buff max de Boo Ghost. Sinon +1 en compromis.", ['+1 : -1 SP', '+3 : Crit DMG 100 → 150 %']),
    'B-Rank Idol Seir': ("Bonne batterie de SP, rarement jouée mais précieuse depuis le Burst.", ['+2 : +1 SP par coup encaissé', '+3 : -1 SP']),
    'Naive Lady Elise': ("Kit correct mais stats de base très faibles : niche, demande Burst 2.", ['+1 : -1 SP', '+2 : Augmentation 4 → 6 %', '+4 : 6 → 8 %']),
    'Pool Party Gray': ("Self-buff de niche, dégâts faibles. Gray est un DPS endgame : peu d'intérêt pour un nouveau joueur.", ['+3 : -1 SP']),
    'Steel Engine Rafina': ("Rafina est peu jouée et son cleanse ne demande pas de copies. Pub : 10 tickets pendant sa bannière.", ['+3 : -1 SP']),
    'Laid-back Lifeguard Nebris': ("Peu de dégâts mais bon self-buff : long buff ATK qui complète la rotation de Nebris.", ['+1 : -1 SP', '+3 : durée du buff ATK 6 → 10 tours']),
    'Tricky Lover Dalvi': ("Doit finir une rotation. La rotation habituelle de 9 tours lui fait rater des stacks de Bleed.", ['+1 : -1 SP']),
    'Anonymous Sage Nartas': ("Mauvaise zone, dégâts moyens, aucun self-buff. Skip.", ['+2 : dégâts conditionnels 450 → 600 %', '+4 : 650 → 800 %']),
    'Angel of Destruction Teresse': ("Costume de rotation (un peu de SP, Bleed). Knockback inutile sur les boss. Pub du Story Pack 7 : 10 tickets pendant sa bannière.", ['+3 : -1 SP']),
    'Heavenly Guardian Successor Glacia': ("Debuff unique (environ +75 % de dégâts au max), mais ses autres costumes ne servent pas en PvE. Surtout team cheerleading en FH.", ['+1 : -1 SP', '+2 : Chain Retention 6 → 9', '+4 : 9 → 12']),
    'Lonely Survivor Lathel': ("Costume de rotation de Lathel, peu de dégâts. Pas obligatoire.", ['+3 : -1 SP']),
    'Killer Doll Lecliss': ("Purement PvP. Pas prioritaire.", ['+3 : -1 SP', '+5 : durée du buff 2 → 4 tours']),
    'Comeback Idol Yuri': ("Bon DPS Lumière, plus fort que Whitebolt mais les deux sont nécessaires. Seulement si tu manques de DPS Lumière et as Whitebolt +1.", ['+1 : -1 SP']),
    'The Sword Queen Sylvia': ("Indispensable si tu construis Sylvia : gros buff ATK exploité par Bikini Agent.", ['+2 : buff ATK 100 → 150 %, 2 → 4 tours', '+5 : 150 → 200 %, 4 → 6 tours']),
    'Sunny Inn Hand Helena': ("Grosse Augmentation sur un allié + petite réduction de cooldown. Complète la rotation d'Helena.", ['+1 : -1 SP', '+3 : durée 6 → 8 tours']),
    'The Destruction Alec': ("PvP, et même là très peu joué.", ['+3 : -1 SP']),
    'Bright Moon Dalvi': ("Costume de rotation de Dalvi. Si tu as Tricky Lover Dalvi, prends +1.", ['+1 : -1 SP']),
    'Savage Warrior Aquila': ("Active chaque tour seulement si l'ennemi frappe 4 fois. +5 si tu construis Aquila. Pub (n'importe quel chapitre) : 10 tickets.", ['+1 : -1 SP', '+3 : buff ATK 15 → 21 %', '+5 : 21 → 27 %']),
    'Young Lady Blade': ("Très bon costume de contenu général (zone 3×3), parfois amplificateur ou petit chainer.", ['+1 : -1 SP']),
    'Ame-no-Mitori Tenka Izumo': ("Collab limitée. Un seul costume, 3 tours de cooldown : jolie pièce de collection, pratique en Story.", ['+1 : -1 SP']),
    'Piercing Magic Bow Eleaneer': ("Surtout PvP (retire les buffs, contre Granhildr). +3 pour suivre les guides FH/GR. Pub aléatoire : 10 tickets.", ['+3 : -1 SP']),
    'Lord of the Cosmos Ren Yamashiro': ("Collab limitée. Kit correct en PvE et PvP, mais un seul costume : peu de chances de rester méta.", ['+1 : -1 SP']),
    'Faithful Wings Olivier': ("Support des autres costumes d'Olivier et batterie de SP avec Retired Legend. Pub du Story Pack 18 : 10 tickets.", ['+1 : -1 SP']),
    'Medical Club Teresse': ("Support très fort (buff ATK + MATK + soin), encore meilleur avec Beachside Angel. Méta en FH, Last Night et Tower of Salvation.", ['+1 : -1 SP']),
}

# Comment obtenir le costume (seulement ce qui est vérifié)
DOUZE_PICK = ['Queen of Gluttis Granadair', 'Shrine Maiden of Purification Granadair', 'Water Park Queen Wilhelmina',
              'Homunculus Lathel', 'Dark Saintess Liberta', 'Onsen Manager Liberta', 'Adventurer of the Unknown Diana',
              'Magical Innovator Diana', 'Robin Hood Zenith', 'B-Rank Idol Helena', 'Pure White Blessing Refithea',
              'Poolside Fairy Refithea']
DOUZE_PICK_REMPL = ['Poolside Guardian Zenith', 'Iron Monarch Wilhelmina', 'Sunny Inn Hand Helena', 'Red Riding Hood Rou',
                    'Young Lady Blade', 'Medical Club Teresse', 'Shadowed Dream Sonya', 'Miracle Marine Mamonir',
                    'Heavenly Guardian Successor Glacia', 'New Hire Seir', 'Shadow Bunny Eleaneer']
SELECTEURS = ['B-Rank Idol Helena', 'Adventurer of the Unknown Diana', 'Homunculus Lathel', 'New Hire Seir',
              'Track and Field Captain Levia', 'Robin Hood Zenith', 'Game Club Rafina']
OBTENTION = {
    'Dream Bride Eclipse': 'Gratuit +5 : event du 2e anniversaire réintroduit (Event tab)',
    'Summer Vacation Dalvi': 'Gratuit +5 : event du 1er anniversaire réintroduit',
    'Stray Cat Rou': 'Gratuit : missions permanentes de l\'Event tab',
    'Beach Vacation Morpeah': 'Gratuit : missions permanentes de l\'Event tab',
    'Daydream Bunny Morpeah': 'Gratuit +5 : event du 1,5 anniversaire réintroduit',
    'Frozen Queen Wilhelmina': 'Gratuit +5 : event du 2,5 anniversaire (permanent)',
    'Eternal Chains Kyouka Uzen': 'Collab Chained Soldier 2 : gratuit +5 + UR EX pendant la collab',
    'Adventurer of the Unknown Diana': 'Pub (Story Pack 10)',
    'Dark Saintess Liberta': 'Pub (Story Pack 15)',
    'Apostle Blade': 'Pub (Story Pack 15)',
    'Apostle Morpeah': 'Pub (Story Pack 17)',
    'Shattered Dream Palette': 'Pub (Story Pack 20)',
    'The Fiend Scholar Olstein': 'Pub (Story Pack 4)',
    'Angel of Destruction Teresse': 'Pub (Story Pack 7)',
    'Faithful Wings Olivier': 'Pub (Story Pack 18)',
    'Queen of Gluttis Granadair': 'Pub (aléatoire)',
    'Night of Death Mamonir': 'Pub (aléatoire)',
    'The Gluttonous Refithea': 'Pub (aléatoire)',
    'The Curse Celia': 'Infinite Draw débutant · Pub (aléatoire)',
    'Piercing Magic Bow Eleaneer': 'Pub (aléatoire)',
    'Acting Archbishop Michaela': 'Pub (aléatoire)',
    'Steel Engine Rafina': 'Pub',
    'Savage Warrior Aquila': 'Pub (n\'importe quel chapitre)',
    'Gentle Maid Anastasia': 'Choix possible de l\'Infinite Draw débutant',
    'Top Idol Helena': 'Choix possible de l\'Infinite Draw débutant',
    'Masquerade Bunny Celia': 'Limitée',
    'Celebrity Bunny Loen': 'Limitée',
    'Ame-no-Mitori Tenka Izumo': 'Collab Chained Soldier 2 (limitée)',
    'Lord of the Cosmos Ren Yamashiro': 'Collab Chained Soldier 2 (limitée)',
}
COLLABS = {
    'goblin_slayer': 'Collab Goblin Slayer (limitée)', 'high_elf_archer': 'Collab Goblin Slayer (limitée)',
    'priestess': 'Collab Goblin Slayer (limitée)', 'sword_maiden': 'Collab Goblin Slayer (limitée)',
    'roxy': 'Collab Mushoku Tensei (limitée)',
    'hikage': 'Collab Senran Kagura (limitée)', 'ikaruga': 'Collab Senran Kagura (limitée)',
    'yomi': 'Collab Senran Kagura (limitée)', 'yozakura': 'Collab Senran Kagura (limitée)',
    'yumi': 'Collab Senran Kagura (limitée)',
    'kyouka_uzen': 'Collab Chained Soldier (limitée)', 'tenka_izumo': 'Collab Chained Soldier (limitée)',
    'ren_yamashiro': 'Collab Chained Soldier (limitée)',
}

# Ton compte (d'après ta capture et le guide V8)
MES_COSTUMES = {
    'Eternal Chains Kyouka Uzen', 'Dream Bride Eclipse', 'Summer Vacation Dalvi', 'New Hire Nebris',
    'Priest of Vitality Arines', 'Kind Student Samay', 'Stray Cat Rou', 'Daydream Bunny Morpeah',
    'Frozen Queen Wilhelmina', 'The Curse Celia', 'Herb Tracker Lathel', 'Little Hunter Rigenette',
    'Seductive Wings Lucrezia', 'Lugo Defense Force Fred',
}
MES_PERSOS = {'kyouka_uzen', 'eclipse', 'dalvi', 'nebris', 'arines', 'samay', 'rou', 'morpeah', 'wilhelmina',
              'celia', 'lathel', 'rigenette', 'lucrezia', 'wiggle', 'fred', 'layla', 'jayden', 'bernie', 'gynt',
              'julie', 'emma', 'cynthia', 'ingrid', 'remnunt', 'andrew', 'beatrice', 'lydia'}

# Costumes absents de character-summary
EXTRA = [
    {'id': 'lord_of_the_cosmos_ren_yamashiro', 'character': 'ren_yamashiro', 'name': 'Lord of the Cosmos Ren Yamashiro',
     'role': ['DPS'], 'damageType': 'magic', 'element': 'light', 'effects': [], 'chains': None, 'spCost': None,
     'spBreak': {'1': None}},
]

# Traductions des usages du glossaire ("Used as a ...")
USAGE_FR = [
    (r'PvP Tank costume', 'tank PvP'), (r'PvP Tank', 'tank PvP'), (r'PvP DPS', 'DPS PvP'),
    (r'PvP Costume', 'costume PvP'), (r'core Magic Support', 'support magique clé'),
    (r'Physical Buffer', 'buffer physique'), (r'Property Buffer \(Support\)', 'buffer d\'élément'),
    (r'Property Buffer', 'buffer d\'élément'), (r'defensive Support', 'support défensif'),
    (r'Self-Support Costume and Concentrated Fire Support', 'self-buff et tir concentré'),
    (r'Self-Buffer and PvP Costume', 'self-buff et costume PvP'), (r'Self-Buff Costume', 'self-buff'),
    (r'Self-Buffer', 'self-buff'), (r'Self-Support', 'self-buff'), (r'SP Battery', 'batterie de SP'),
    (r'Knockback unit', 'knockback'), (r'Knockback Costume', 'knockback'), (r'Dispel Costume', 'dispel'),
    (r'DEF and MRES Shredder', 'baisse DEF et MRES'), (r'DEF Shredder', 'baisse DEF'),
    (r'DoT DPS', 'DPS DoT'), (r'weak DPS', 'DPS faible'), (r'early DPS', 'DPS early'), (r'PvE DPS', 'DPS PvE'),
    (r'low Chainer and Sub DPS', 'petit chainer et DPS secondaire'), (r'Sub DPS', 'DPS secondaire'),
    (r'Amplifier', 'amplificateur'), (r'Chainer', 'chainer'), (r'Buffer', 'buffer'), (r'Support', 'support'),
    (r'Staller', 'staller'), (r'Tank', 'tank'), (r'DPS', 'DPS'),
]


def usage_fr(desc):
    m = re.search(r'(?:Primarily used|Used) as (?:an? )?(.+?)\.?$', desc)
    if not m:
        return ''
    u = m.group(1)
    u = re.sub(r'\b(an?|the) ', '', u)
    for a, b in USAGE_FR:
        u = re.sub(a, b, u, flags=re.I)
    u = re.sub(r'(?<!et) costume(?= et|$)', '', u)
    u = u.replace(' and ', ' et ').replace(', ', ', ')
    return u[0].upper() + u[1:] if u else ''


# Définitions du glossaire (hors persos et costumes)
GLOSS_FR = {
    # Ressources
    'Ability Skill Books': "Livres ★1 à ★4 pour monter le rang d'une capacité de terrain (Crafting, Alchemy...). ★1-★2 : shop du Story Pack 3. ★3 : shop du Story Pack 10 ou Evil Castle. ★4 : Evil Castle.",
    'Ancient Crystal': "Sert à crafter le gear UR. Sources : events, Event Shop, Golden Colosseum Shop, Tower of Salvation, Tower of Pride, Last Night.",
    'Awakening Elixir': "Sert à l'Awakening (200 pour un 5★). Sources : Last Night (jusqu'à 5 par jour), Guild Shop, Tower of Salvation, Golden Colosseum Shop.",
    'Cooked Rice': "Énergie quotidienne des Hunting Grounds et du Path of Adventure (Gold, Slimes, matériaux). Le Rice « payant » des events se garde.",
    'Costume Selective Enhancement': "« Unidupe » : une copie du costume non limité de ton choix. 1 600 Golden Thread, une fois par mois. Meilleur achat structurel du jeu.",
    'Draw Ticket': "Ticket rouge : 1 pull sur une bannière (vaut 200 Dia).",
    'Engraving Scroll': "Sert à l'Engraving (1 110 pour un 5★ complet). Surtout au shop de l'Evil Castle.",
    'Essences': "Essence of Strength (ATK/MATK), of Perseverance (DEF/MRES), of Life (PV) : pour l'Engraving.",
    'Golden Thread': "Obtenu quand tu tires une copie d'un costume déjà +5. Sert à l'unidupe, aux Sparks et au costume featured.",
    'Powder of Hope': "Obtenu avec les Draw Points non utilisés à la fin d'une bannière. Achète des costumes (200 la copie).",
    'Property Crystal': "Crystals d'élément (Eau, Feu, Vent, Lumière, Ténèbres) pour le Potential. Farm : Magic Crystal Caves avec les Torches.",
    'Property Selective Draw Exchange Ticket': "Tu choisis un élément et reçois un 5★ aléatoire de cet élément.",
    'Pulls': "Terme global pour les Draw Tickets et les Dia utilisables en gacha.",
    'Recommended ★5 Costume Selective Ticket': "Ticket arc-en-ciel : choisis 1 costume parmi 12 proposés. 12 donnés par le Guide Pass.",
    'Recruitment Contract': "Contrats ★3, ★4 et ★5 pour recruter au Pub.",
    'Refining Crystal': "Reroll des substats du gear SR et UR. Sources : Event Shop, Golden Colosseum, Tower of Salvation, démontage SR/UR.",
    'Refining Powder': "Monte et raffine le gear. Sources : events, démontage (surtout N monté à +7).",
    'Refining Stone': "Reroll des substats (gear R, puis SR/UR avant les Crystals). 10 Stones = 1 Crystal. Démontage de gear R.",
    'Selective Draw Ticket': "Ticket violet : pulls sur les bannières sélectives (12-Pick).",
    'Slime': "Slimes jaunes (200 EXP), bleus (800) et rouges (2 000) : niveaux des persos. Farm : Slime Empire.",
    'Rank-Up Stars': "Étoiles ★1 à ★4 pour relever le plafond de niveau d'un perso (paliers 20, 40, 60, 80, 100).",
    'Spark of Rampage': "Monnaie du Burst (60 par palier pour un 5★). Environ 530 à 585 par mois.",
    'Tear of Goddess': "Monnaie des grands nœuds de Potential (1 par nœud, irréversible). La ressource la plus rare du compte.",
    # Mécaniques
    'Amplifier': "Costume qui augmente les dégâts subis par la cible, surtout via la Vulnerability.",
    'Area of Effect': "Cases touchées par un skill. « Grosse AoE » = beaucoup de cases.",
    'Attack': "ATK : stat de dégâts des unités physiques.",
    'Augmentation': "Buff de dégâts des alliés, souvent conditionnel. Non réduit par Pressure.",
    'Basic Attack': "Attaque d'une case sans multiplicateur de skill.",
    'Basic Skill': "S1 à S4 : skills qu'un boss utilise par défaut, dans l'ordre affiché. Le dernier tue la team.",
    'Burst': "B0 à B3 : palier de Burst d'un costume (plus de SP pour un skill renforcé).",
    'Chainer': "Costume avec beaucoup de hits, qui monte vite les chains (ex. Wilhelmina, Celia).",
    'Chains': "Chaque hit ajoute une chain, chaque chain +10 % de dégâts sur la cible pour le tour.",
    'Conditional Skill': "C1 à C4 : skills de boss déclenchés quand une condition est remplie.",
    'Crit Fish': "Relancer le tour ou le combat pour obtenir des crits.",
    'Critical Damage': "Crit DMG : bonus de dégâts d'un coup critique.",
    'Critical Rate': "Crit Rate : chance de critique. Au-delà de 100 %, chaque point devient 6 points de Crit DMG.",
    'Damage Dealer': "DPS : costume qui fait les gros dégâts.",
    'Damage Over Time': "DoT : dégâts infligés à la fin de chaque tour (Bleed, poison...).",
    'Defence': "DEF : réduit les dégâts physiques subis (plafond 90 %).",
    'Energy Guard': "Bouclier de PV temporaires consommé avant les PV.",
    'Flat Stat': "Bonus de stat fixe, appliqué avant les bonus en %, surtout sur le gear.",
    'Health Points': "PV : santé du perso.",
    'Knockback': "Repousse l'ennemi. S'il percute un autre ennemi, gros dégâts selon ses PV (plafond 50 000). Inutile sur les boss.",
    'Magical Attack': "MATK : stat de dégâts des unités magiques.",
    'Magical Resistance': "MRES : réduit les dégâts magiques subis (plafond 90 %).",
    'Naked Character': "Perso sans gear, volontairement ou non.",
    'Nuke': "Gros hit qui vide les PV ennemis d'un coup. En verbe : tout lâcher sur un tour.",
    'Nuke Turn': "Le tour où tu lâches tout, après avoir posé buffs et debuffs.",
    'Potential Liberation': "« Pots » : arbre de progression d'un costume (stats et améliorations de skill).",
    'Pressure': "Debuff qui réduit l'efficacité de tes buffs de stats.",
    'Property': "Élément. Eau > Feu > Vent > Eau, Lumière et Ténèbres se battent entre elles, Neutre sans bonus.",
    'Property Damage': "Dégâts bonus grâce à l'avantage d'élément (50 % de base).",
    'Stat Reduction': "« Shred » : baisse d'ATK, MATK, DEF ou MRES ennemie.",
    'Skill Points': "SP : réserve commune pour lancer les costumes, remonte à chaque tour.",
    'SP Generation': "Rendre du SP à l'équipe.",
    'SP Generator': "« Battery » : costume qui rend du SP à l'équipe.",
    'Staller': "Costume qui fait durer le combat.",
    'Vault': "Ciblage qui vise le deuxième ennemi de la colonne.",
    'Very Front': "Ciblage qui vise le premier ennemi de la colonne.",
    'Vulnerability': "Debuff qui augmente les dégâts subis par la cible.",
    'Weak Point': "Case de boss (Fiend Hunter, Guild Raid) qui prend plus de dégâts.",
    # Contenu
    'Character Pack': "Pack d'histoire dans un univers alternatif, hors histoire principale.",
    'Daily Missions': "Missions quotidiennes, remises à zéro chaque jour à 00:00 UTC.",
    'Event Pack': "Pack d'event dans un univers alternatif.",
    'Evil Castle': "Pack de 5 tours : Pride, Desire, Salvation, Wrath, Jealousy (Story Pack 4).",
    'Fantasia Square': "Place en ligne : Goddess Statue, statues de Champion, Territory, Hall of Fame.",
    'Fated Guest': "Client du Glupy Diner avec une histoire et des scènes interactives (Live2D).",
    'Fiend Hunter': "Boss d'event toutes les 2 semaines, jusqu'à 3 teams, niveaux infinis. 30 tickets + 1 Tear au niveau 10.",
    'Glupy Diner': "Restaurant passif : Gold, Powder, Crystals, Deco Coins, clients spéciaux.",
    'Golden Colosseum': "PvP hebdomadaire en costumes, sans gear (Story Pack 6).",
    'Golden Thread Shop': "Shop en Golden Thread : unidupe, Sparks, costume featured.",
    'Guild Raid': "Boss de guilde, grille 5×5 et 7 persos.",
    'Last Night': "Un tour, 20 costumes, score qui donne des rewards quotidiens à vie (Story Pack 3).",
    'Mirror Wars': "PvP hebdomadaire, 40 combats par jour, Dia selon le rang (Story Pack 3).",
    'Player vs. Environment Content': "PvE : contenu contre l'IA.",
    'Player vs. Player Content': "PvP : Mirror Wars et Golden Colosseum.",
    'Powder of Hope Shop': "Shop en Powder of Hope : costumes featured, Sparks.",
    'Story Pack': "Chapitres de l'histoire principale, en Normal, Hard et Very Hard.",
    'Taros Tactical Manual': "Combats-puzzles avec persos imposés, saison de 28 jours.",
    'The Soul Wager': "Auto-battler d'inventaire, saison de 8 semaines. Shop : Tear en premier.",
    'Tower of Desire': "Tour de l'Evil Castle, 250 étages, 1 Draw Ticket par étage.",
    'Tower of Jealousy': "Tour de l'Evil Castle, 100 étages, team PHYSIQUE uniquement.",
    'Tower of Pride': "Tour de l'Evil Castle au score, rewards quotidiens (6 étages).",
    'Tower of Salvation': "Roguelike de saison (4 semaines) de l'Evil Castle (Story Pack 9).",
    'Tower of Wrath': "Tour de l'Evil Castle, 100 étages, team MAGIQUE uniquement.",
    # Divers
    'Cheerleading Team': "Team de Fiend Hunter qui fait peu de dégâts mais pose des bonus pour la suivante.",
    'Costume Collection': "Affichage de tous tes costumes, en général via Last Night.",
    'Fiend Hunt Damage Threshold': "Dégâts minimum en un combat pour valider un niveau de Fiend Hunter le dernier jour.",
    'Gear Calculator': "Calculateur de substats de Souseha.",
    'Lancelot': "Allié spécial du Guild Raid avec des capacités uniques pendant quelques tours.",
    # Gear
    'Charming Gaze': "Accessoire UR · Crit DMG + PV %. Pour les DPS sur PV.",
    'Crown of Galaxy': "Casque UR · MRES + PV %.",
    "Death's Shroud": "Armure UR · MRES + PV fixes.",
    "Demon's Forbidden Book": "Arme UR · MATK + MATK fixe. Magique late game, et DPS à dégâts fixes.",
    'Dragon Scales Protection': "Gants UR · MATK % + MATK fixe. Magique late game.",
    "Evil Dragon's Blade": "Arme UR · ATK + Crit DMG. Physique early game, DPS sur PV.",
    'Eye of the Destroyer': "Arme UR · MATK + MATK %. Magique late game.",
    'Fiend Guard': "Armure UR · MRES + MRES. Contre les ennemis magiques.",
    "God-King's Silver Arm": "Gants UR · ATK % + ATK %. Physique, idéal débutant.",
    'Hammer of Thunder': "Arme UR · ATK + ATK %. Physique late game.",
    'Helm of Carnage': "Casque UR · DEF + DEF. Contre les ennemis physiques.",
    'Helm of Death': "Casque UR · DEF + PV %.",
    'Immortal Golden Armor': "Armure UR · DEF + PV %.",
    'Invulnerable Armor': "Armure UR · DEF + DEF. Contre les ennemis physiques.",
    'Peerless Javelin': "Arme UR · ATK + ATK fixe. Physique late game.",
    'Prime Authority': "Gants UR · ATK % + ATK fixe. Physique late game.",
    'Promise of Harmony': "Accessoire UR · Crit Rate + PV %.",
    'Rebellion': "Gants UR · ATK + Crit Rate.",
    'Ring of Fury': "Gants UR · MATK + Crit Rate.",
    'Ring of the Lake': "Accessoire UR · Crit DMG + PV fixes.",
    'Scale of the Sea God': "Armure UR · DEF + PV fixes.",
    'Shackle of Treachery': "Gants UR · MATK % + MATK %. Magique, idéal débutant.",
    'Solar Brilliance': "Casque UR · MRES + PV fixes.",
    'SR Exclusive Gear': "EX SR : gear exclusif d'un perso, à peu près un UR III crafté.",
    "Travel God's Friend": "Arme UR · MATK + Crit DMG. Magique early game.",
    'Undefeated Glory': "Casque UR · DEF + PV fixes.",
    'UR Exclusive Gear': "EX UR : gear exclusif d'un perso, niveau UR IV + une stat exclusive (+10 à 20 % de dégâts).",
    'Venomous Touch': "Accessoire UR · Crit DMG + Crit DMG. L'accessoire prioritaire de presque tous les DPS.",
    'Warmth of the Brazier': "Accessoire UR · Crit Rate + Crit Rate.",
}
GLOSS_CAT = {'Resource': 'Ressource', 'Game Mechanics': 'Mécanique', 'Content': 'Contenu',
             'Miscellaneous': 'Divers', 'Gear': 'Gear'}
GLOSS_EXTRA = [
    ('Gear', 'Radiant Wisdom', 'MRES Helm', "Casque UR résistance magique, associé à Fiend Guard contre les ennemis magiques."),
    ('Gear', 'Hellfire Robe', 'MRES / HP Armor', "Armure UR résistance magique + PV, associée à Crown of Galaxy."),
    ('Resource', 'Spark of the Otherworld', 'Otherworld Sparks', "Monnaie de Burst réservée aux costumes de collab, en quantité limitée pendant la collab (60 par palier + 50K Gold)."),
    ('Resource', 'Devil Coin', 'EC Coins', "Monnaie de l'Evil Castle (Tower of Pride surtout) : Engraving Scrolls et Essences."),
    ('Resource', 'Medal of the Fighting Spirit', 'Medals, MW Medals', "Monnaie de Mirror Wars, gagnée à chaque combat : costume featured et Refining Crystals."),
    ('Resource', 'Aurum Coin', 'GC Coins', "Monnaie du Golden Colosseum : Property tickets, Sparks, Draw Tickets."),
    ('Resource', 'Mercenary Alliance Deed', 'Deeds', "Monnaie de guilde : Tear, Sparks, 10 Draw Tickets, Elixirs."),
    ('Resource', 'Alea Chip', 'Chips', "Monnaie du Soul Wager : Tear en premier. Expire avec la saison."),
    ('Resource', 'Refinement Remnants', 'Remnants', "Obtenus en raffinant du gear : Sparks ×200 par mois, puis tickets de score 23/24."),
    ('Resource', 'Lucky Silver Coin', 'Fishing coins', "Monnaie de la pêche : Gold, Refining Powder, Deco Coins."),
    ('Resource', 'Blood Cocktail', 'Cocktails', "Entrées de Mirror Wars : 40 par jour, reset 00:00 UTC. Ne pas acheter en Dia."),
    ('Resource', 'Torch', 'Torches', "Énergie quotidienne des Magic Crystal Caves (Crystals d'élément)."),
    ('Resource', 'Ability Pill', 'Pills', "Coût des capacités de terrain, du craft et de l'Alchemy."),
    ('Resource', 'Deco Coin', 'Deco', "Déco de My Room. Glupy Diner (20 par jour max) et pêche."),
    ('Resource', 'Draw Points', 'Pity, points', "1 point par pull sur une bannière. 200 = le costume featured au choix. Les restes deviennent du Powder of Hope."),
    ('Mécanique', 'Death Time', 'DT', "Après le tour 10 : tous les 2 tours, +100 % ATK/MATK, -100 % DEF/MRES et +50 % de dégâts subis pour tout le monde."),
    ('Mécanique', 'Pure Damage', 'Pure DMG', "Dégâts qui peuvent crit, ignorent DEF, MRES et Energy Guard."),
    ('Mécanique', 'Fixed Damage', 'Fixed DMG', "Dégâts sans crit qui ignorent DEF, MRES et réductions. Faibles hors PvP."),
    ('Mécanique', 'Chain Reinforcement', 'CR buff', "Chaque hit ajoute une chain de plus. Cumulable : Celia 7 → 14 → 21 chains."),
    ('Mécanique', 'Bond', 'Lien', "Chaque perso est lié à un costume : ses nœuds moyens de Potential ne marchent que sur le costume lié."),
    ('Mécanique', 'Breakpoint', 'BP', "Nombre de copies qui change vraiment un costume (souvent -1 SP à +1 ou +3)."),
    ('Mécanique', 'Rotation', 'Rota', "Enchaînement des costumes d'un même perso d'un tour à l'autre : un costume par tour, les cooldowns obligent à alterner."),
    ('Mécanique', 'Set Costume Order', 'Ordre programmé', "10 emplacements qui programment les costumes à lancer, en boucle. Écrase les choix manuels quand il est actif."),
    ('Mécanique', 'Preset', 'Presets', "12 teams sauvegardées (persos, gear, ordre, placement)."),
    ('Divers', 'Quick Battle', 'QB', "Rejoue instantanément un combat déjà réussi (events après les clear rewards des combats 5/10/15, Fiend Hunter avec ton meilleur score de la veille)."),
    ('Divers', 'Quick Hunt', 'QH', "Menu qui balaie les Hunting Grounds et le Path of Adventure sans relancer les combats."),
]


# ---------------------------------------------------------------- utilitaires

def run(cmd):
    subprocess.run(cmd, check=True)


def source(url, name, given):
    if given:
        return Path(given)
    path = CACHE / name
    if path.exists():
        run(['git', '-C', str(path), 'pull', '-q'])
    else:
        CACHE.mkdir(exist_ok=True)
        run(['git', 'clone', '-q', '--depth', '1', url, str(path)])
    return path


def load(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))


IDENT = re.compile(r'^[A-Za-z_$][A-Za-z0-9_$]*$')


def js(v, ind=0):
    pad = '  ' * ind
    if v is None:
        return 'null'
    if v is True:
        return 'true'
    if v is False:
        return 'false'
    if isinstance(v, (int, float)):
        return str(v)
    if isinstance(v, str):
        v = v.replace('—', ', ').replace('–', '-').replace(' ,', ',')
        return "'" + v.replace('\\', '\\\\').replace("'", "\\'").replace('\n', '\\n') + "'"
    if isinstance(v, list):
        if not v:
            return '[]'
        if all(not isinstance(x, (dict, list)) for x in v):
            return '[' + ', '.join(js(x) for x in v) + ']'
        inner = ',\n'.join(pad + '  ' + js(x, ind + 1) for x in v)
        return '[\n' + inner + '\n' + pad + ']'
    if isinstance(v, dict):
        parts = []
        for k, x in v.items():
            key = k if IDENT.match(k) else js(k)
            parts.append(key + ': ' + js(x, ind + 1))
        one = '{ ' + ', '.join(parts) + ' }'
        if len(one) < 150 and '\n' not in one:
            return one
        return '{\n' + ',\n'.join(pad + '  ' + p for p in parts) + '\n' + pad + '}'
    raise TypeError(type(v))


def write(name, var, value, head):
    body = '// ' + head + '\n// Fichier généré par scripts/build_data.py : ne pas modifier à la main.\n'
    body += 'window.BD2 = window.BD2 || {};\n'
    body += 'BD2.' + var + ' = ' + js(value) + ';\n'
    (DATA / name).write_text(body, encoding='utf-8')
    print('écrit', name)


def norm(s):
    return re.sub(r'[^a-z0-9]', '', s.lower())


# ---------------------------------------------------------------- construction

def parse_glossary(md):
    src = re.sub(r'<!--.*?-->', '', md, flags=re.S)
    out = []
    for it in re.findall(r'<li class="slang-item"[^>]*>(.*?)</li>', src, flags=re.S):
        h = re.search(r'<h3>(.*?)</h3>', it, flags=re.S)
        tags = re.findall(r'<span class="alias-tag([^"]*)">(.*?)</span>', it, flags=re.S)
        ps = re.findall(r'<p>(.*?)</p>', it, flags=re.S)
        cat = next((t[1] for t in tags if 'ignore-exact' in t[0]), '')
        alias = [re.sub('<[^>]+>', '', t[1]).strip() for t in tags if 'ignore-exact' not in t[0]]
        desc = ' '.join(re.sub(r'\s+', ' ', re.sub('<[^>]+>', '', html.unescape(x))).strip() for x in ps)
        title = re.sub('<[^>]+>', '', h.group(1)).strip() if h else ''
        out.append({'cat': cat, 'term': title, 'alias': [a for a in alias if a], 'desc': desc})
    return out


def build(tc, banner):
    docs = tc / 'docs'
    summary = load(docs / 'assets/data/character-summary.json') + EXTRA
    gloss = parse_glossary((docs / 'misc/slang.md').read_text(encoding='utf-8'))
    archive = load(banner / 'public/json/archive_data.json')
    current = load(banner / 'public/json/data.json')['banner']
    charinfo = load(banner / 'public/json/character_info.json')

    # Avis par nom de costume
    avis = {}
    for key, v in archive.items():
        nom = AVIS_NOMS.get(key)
        if nom:
            avis[nom] = {'prio': PRIO.get(v.get('pullPriority'), ''), 'date': (v.get('startDate') or '')[:10]}
    for v in current:
        nom = AVIS_NOMS.get(v['imgName'])
        if nom:
            avis[nom] = {'prio': PRIO.get(v.get('pullPriority'), ''), 'date': v['startDate'][:10],
                         'modes': {k: MODE.get(x, x) for k, x in (v.get('modes') or {}).items()}}
    for nom, a in avis.items():
        txt, bps = AVIS_FR.get(nom, ('', []))
        a['texte'] = txt
        a['bp'] = bps

    gloss_by = {norm(g['term']): g for g in gloss}
    info_char = {norm(k): v for k, v in charinfo.items()}

    costumes = []
    seen = set()
    for c in summary:
        name = c['name']
        if norm(name) in seen:
            continue
        seen.add(norm(name))
        g = gloss_by.get(norm(name), {})
        char = c['character']
        personame = char.replace('_', ' ').title().replace('Kyouka Uzen', 'Kyouka').replace('Tenka Izumo', 'Tenka') \
            .replace('Ren Yamashiro', 'Ren')
        el = ELEMENT.get(c.get('element'), '')
        if not el and norm(char) in info_char:
            att = info_char[norm(char)]['dmgAtt']
            el = next((v for k, v in DMG_ATT.items() if att.startswith(k)), '')
        sp_break = c.get('spBreak') or {}
        breaks = [('+' + k + ' : ' + str(v) + ' SP') for k, v in sp_break.items() if v is not None]
        obt = OBTENTION.get(name) or COLLABS.get(char, '')
        tags = []
        if name in DOUZE_PICK:
            tags.append('12-Pick')
        if name in DOUZE_PICK_REMPL:
            tags.append('12-Pick (remplacement)')
        if name in SELECTEURS:
            tags.append('Selector 5★')
        entry = {
            'id': c['id'], 'nom': name, 'perso': personame, 'pid': char, 'el': el,
            'type': DMG.get(c.get('damageType'), ''),
            'roles': [ROLES.get(r, r) for r in c.get('role', [])],
            'effets': [EFFETS.get(e, e) for e in c.get('effects', [])],
            'hits': c.get('chains'), 'sp': c.get('spCost'), 'spBreak': breaks,
            'pots': [POTS.get(p.get('label'), p.get('label')) for p in c.get('potentials', []) if p.get('label')],
            'alias': g.get('alias', []), 'usage': usage_fr(g.get('desc', '')),
            'obtention': obt, 'tags': tags, 'moi': name in MES_COSTUMES, 'persoMoi': char in MES_PERSOS,
        }
        if name in avis:
            entry['avis'] = avis[name]
        costumes.append(entry)
    missing = [n for n in avis if norm(n) not in seen]
    if missing:
        print('avis sans fiche :', missing, file=sys.stderr)
    costumes.sort(key=lambda x: (x['perso'], x['nom']))

    glossaire = []
    for g in gloss:
        if g['cat'] in ('Character', 'Costume'):
            continue
        fr = GLOSS_FR.get(g['term'])
        if not fr:
            print('terme sans traduction :', g['term'], file=sys.stderr)
            fr = g['desc']
        glossaire.append({'cat': GLOSS_CAT.get(g['cat'], g['cat']), 'terme': g['term'], 'alias': g['alias'], 'def': fr})
    for cat, term, alias, fr in GLOSS_EXTRA:
        glossaire.append({'cat': GLOSS_CAT.get(cat, cat), 'terme': term, 'alias': [a.strip() for a in alias.split(',')], 'def': fr})
    glossaire.sort(key=lambda x: (x['cat'], x['terme'].lower()))

    persos = []
    for c in gloss:
        if c['cat'] == 'Character':
            m = re.search(r'playable (\w+) Character', c['desc'])
            persos.append({'nom': c['term'], 'alias': c['alias'],
                           'el': {'Fire': 'feu', 'Water': 'eau', 'Wind': 'vent', 'Light': 'lumiere',
                                  'Darkness': 'tenebres'}.get(m.group(1), '') if m else ''})

    rap = load(docs / 'assets/data/rapport.json')['costumes']
    rapport = []
    for r in rap:
        rows = []
        for e in r['encounters']:
            intro = [x for x in (e.get('intro') or []) if x.strip()]
            rows.append({'n': e['n'], 'q': intro[-1] if intro else '', 'ok': e.get('correct', ''), 'ko': e.get('wrong', '')})
        rapport.append({'costume': r['costume'], 'perso': r['character'],
                        'boissons': [d['name'] for d in r.get('drinks', [])], 'rencontres': rows})

    fh = load(docs / 'assets/data/fiend-hunter-bosses.json')
    bosses, keys = [], set()
    for b in fh:
        k = (b.get('name'), b.get('dateStart'))
        if k in keys:
            continue
        keys.add(k)
        bosses.append({'saison': int(b['season']), 'event': b.get('seasonEvent', ''), 'nom': b['name'],
                       'el': {'Fire': 'feu', 'Water': 'eau', 'Wind': 'vent', 'Light': 'lumiere',
                              'Darkness': 'tenebres'}.get(b.get('property'), ''),
                       'debut': b['dateStart'], 'fin': b['dateEnd']})
    bosses.sort(key=lambda x: x['debut'])

    ck = load(docs / 'assets/data/checklist.json')
    overrides = [{'id': o['id'], 'debut': o['start'], 'fin': o['end'], 'cloture': o.get('settlement_start', o['end'])}
                 for o in ck.get('overrides', [])]
    bannieres = []
    for v in current:
        nom = AVIS_NOMS.get(v['imgName'], v['costumeName'] + ' ' + v['charName'])
        bannieres.append({'nom': nom, 'debut': v['startDate'], 'fin': v['endDate'],
                          'prio': PRIO.get(v.get('pullPriority'), ''), 'texte': AVIS_FR.get(nom, ('', []))[0]})
    calendrier = {'ancre': ck['anchor_date'], 'cycle': ck.get('patch_cycle_days', 28), 'decalages': overrides,
                  'bannieres': bannieres, 'maj': datetime.now(timezone.utc).strftime('%Y-%m-%d')}

    DATA.mkdir(exist_ok=True)
    write('costumes.js', 'costumes', costumes, f'{len(costumes)} costumes : Compendium + Banner Recommendation + glossaire')
    write('persos.js', 'persos', persos, f'{len(persos)} personnages jouables')
    write('glossaire.js', 'glossaire', glossaire, f'{len(glossaire)} termes')
    write('rapport.js', 'rapport', rapport, f'{len(rapport)} costumes avec réponses de Rapport')
    write('fiend-hunter.js', 'bosses', bosses, f'{len(bosses)} saisons de Fiend Hunter')
    write('calendrier.js', 'calendrier', calendrier, 'Cycle de 28 jours, décalages et bannières actives')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tc')
    ap.add_argument('--banner')
    a = ap.parse_args()
    tc = source(TC_REPO, 'BD2-Overview', a.tc)
    banner = source(BANNER_REPO, 'BD2-Banner-Recommendation', a.banner)
    build(tc, banner)


if __name__ == '__main__':
    main()
