# Idée 1 du format 

Tout en JSON

pas complet, rajoutez ce qu'il faut

## Liste d'AS

Chaque AS a :
- un numéro d'AS
- un préfixe IPV6
- une liste de routeurs (chaque hostname doit être unique et ne peut pas être dans 2 AS)
- nom du protocole de routage interne (ou identifiant unique pour celui-ci)
- une liste des AS connus avec qui on veut parler qui nous dit si ils sont peer, fournisseurs ou clients, ET les réseaux d'interconnection à utiliser PAR INTERCONNECTION (préciser lesquels sont pour lesquels en remplaçant les réseaux d'interconnection par un dictionnaire avec comme clés les routers de l'AS et valeurs les sous-réseaux)

## Liste de tous les routeurs

Chaque routeur a :
- son hostname
- une liste des appreils auxquels il est connecté avec chaque autre appareil sous forme de dictionnaire {"type":"Router"|"Switch"|..., "hostname":"le hostname", "interface":"nom de l'interface"}, interface peut être ommis
- son AS number

## Trucs en Plus 

- RSVP 
    - pas les réservations de capacité
    - tunnel pour dévier du chemin le plus court
    - tester avec des traceroute et regarder les messages PATH