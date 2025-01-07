import json
import ipaddress

from autonomous_system import AS
from router import Router

AS_LIST_NAME = "Les_AS"
ROUTER_LIST_NAME = "Les_routers"

def router_list_into_hostname_dictionary(router_list:list[Router]) -> dict[str, Router]:
    dico = {}
    for router in router_list:
        dico[router.hostname] = router
    return dico

def parse_intent_file(file_path:str) -> tuple[list[AS], list[Router]]:
    """
    Fonction de parsing d'un fichier d'intention dans notre format

    entrée: file_path, un chemin relatif ou absolu valide dans le système de fichier
    sortie: tuple contenant la liste des AS, et la liste des routeurs dans le fichier donné

    Si le chemin ne mène pas à un fichier valide, la fonction va renvoyer une exception
    """
    with open(file_path, "r") as file:
        data = json.load(file)
        les_as = []
        for autonomous in data[AS_LIST_NAME]:
            ip = ipaddress.IPv6Network(autonomous["ipv6_prefix"])
            as_number = autonomous["AS_number"]
            routers = autonomous["routers"]
            routage_interne = autonomous["routage_interne"],
            connected_as = autonomous["AS_connectes"]
            les_as.append(AS(ip, as_number, routers, routage_interne, connected_as))
        les_routers = []
        for router in data[ROUTER_LIST_NAME]:
            hostname = router["hostname"]
            links = router["links"]
            as_number = router["AS_number"]
            les_routers.append(Router(hostname, links, as_number))
        return (les_as, les_routers)