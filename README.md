# projet-GNS3
repo du code du groupe 14 du projet GNS3 en 3TC

## Format du fichier d'intention
- dictionnaire JSON avec 2 éléments top-level :
- "Les_AS" :
    - contient une liste de dictionnaires d'informations pour chaque AS :
        - "ipv6_prefix":le préfixe IPv6 du réseau, **doit être unique**
        - "AS_number":le AS number, **doit être unique**
        - "routers":la liste des hostname des routeurs appartenant à l'AS (**attention, ne pas mettre 1 routeur dans plusieurs AS !**)
        - "internal_routing":le nom du protocole de routage interne, seuls "RIP" et "OSPF" sont corrects
        - "connected_AS": une liste de "tuples" de 3 élements :
            - le numéro d'AS spécifié
            - la relation avec celui-ci ("peer", "provider" ou "client") (**doit être logique des 2 côtés, si peer d'un côté, peer de l'autre, si provider d'un côté, client de l'autre et inversement**)
            - un dictionnaire des préfixes ipv6 de liens à utiliser pour les points de connection avec cet AS partant d'un routeur donné (si on utilise le préfixe 2001:200:401::64 pour le lien entre l'AS 111 et 110 partant de R5 du côté 111, ce dictionnaire aura une entrée "R5":"2001:200:401::/64", , **doivent être uniques par lien entre AS**)
            - RAJOUT DE NAS VPN : si il existe une relation de VPN entre les 2 AS, une liste de plusieurs éléments (des 2 côtés) :
                - identifiant de client (entier positif)
        - "loopback_prefix":le préfixe IPv6 voulu pour allouer les adresses loopback, **doit être unique**
- "Les_routeurs" :
    - contient une liste de dictionnaires d'informations complets pour tous les routeurs :
        - "hostname":le hostname du routeur, **doit être unique**
        - "AS_number": le AS number du router, **doit correspondre à celui dans lequel le routeur est**
        - "links": une liste de dictionnaire représentant les liens de ce routeur avec d'autres :
            - "type": le type de machine vers laquelle le lien pointe, au final seul "Router" est implémenté donc ce paramètre est superflu
            - "hostname": le hostname du routeur distant
            - "interface": OPTIONNEL, l'interface physique complète que ce lien doit utiliser, permet de contrôler l'allocation des interfaces pour différents liens si nécessaire (forcer un lien vers un autre AS à utiliser une interface rapide par exemple)
            - "ospf_cost": OPTIONNEL, permet de donner un coût entier OSPF strictement positif à un lien, écrasant la valeur calculée par le routeur si cette configuration n'est pas fournie
            - REMARQUE : Il ne peut pas y avoir plusieurs liens par interface, et on doit avoir len(links) <= (nombre d'interfaces physiques sur le routeur)
        - "position": dictionnaire donnant la position 2D où mettre le routeur dans le projet GNS3
            - "x": position entière positive horizontale
            - "y": position entière positive verticale

## Exécution
- testé et codé pour python 3.12.x
- nécessite l'installation des modules précis de `requirements.txt` avec `pip install -r requirements.txt`
- lancer GNS3 avec un projet vide ou un état intermédiaire du réseau décrit dans le fichier d'intention voulu
- lancer `GenerateRouterConfig.py {cfg/telnet} {chemin relatif ou absolu vers le fichier d'intention}` avec un interpréteur python 3.12.x

Remarque : Comme seules les loopback sont advertised en BGP, pour ping entre routeurs il faut faire `ping {cible} source lo1` (le `source lo1` met comme adresse source l'adresse de loopback du routeur qui ping, ce qui permet aux ICMP echo reply de revenir)


## Fonctionnalités supportées (Telles que listées sur le document du sujet)
- Network Automation
    - Architecture : oui
    - Addressing : Automated
    - Protocols : oui
    - Policies
        - BGP Policies : oui
        - OSPF Metric Optimization : oui
- Deployment
    - Drag and Drop bot : oui
    - Telnet : oui