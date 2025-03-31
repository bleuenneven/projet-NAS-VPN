import ipaddress
import json

from autonomous_system import AS, GlobalRouterIDCounter
from ipv4 import SubNetwork
from router import Router
from writer import get_final_config_string

AS_LIST_NAME = "Les_AS"
ROUTER_LIST_NAME = "Les_routeurs"


def router_list_into_hostname_dictionary(router_list: list[Router]) -> dict[str, Router]:
    dico = {}
    for router in router_list:
        dico[router.hostname] = router
    return dico


def as_list_into_as_number_dictionary(as_list: list[AS]) -> dict[int, AS]:
    dico = {}
    for autonomous in as_list:
        dico[autonomous.AS_number] = autonomous
    return dico


def parse_intent_file(file_path: str) -> tuple[list[AS], list[Router]]:
    """
    Fonction de parsing d'un fichier d'intention dans notre format

    entrée: file_path, un chemin relatif ou absolu valide dans le système de fichier
    sortie: tuple contenant la liste des AS, et la liste des routeurs dans le fichier donné

    Si le chemin ne mène pas à un fichier valide, la fonction va renvoyer une exception
    """
    with open(file_path, "r") as file:
        data = json.load(file)
        les_as = []
        global_counter = GlobalRouterIDCounter()
        for autonomous in data[AS_LIST_NAME]:
            as_number = autonomous["AS_number"]
            routers = autonomous["routers"]
            ip = SubNetwork(ipaddress.IPv4Network(autonomous["ipv4_prefix"]), len(routers))
            internal_routing = autonomous["internal_routing"]
            connected_as = autonomous["connected_AS"]
            loopback_prefix = SubNetwork(ipaddress.IPv4Network(autonomous["loopback_prefix"]), len(routers))
            les_as.append(AS(ip, as_number, routers, internal_routing, connected_as, loopback_prefix, global_counter, autonomous.get("route_reflectors", [])))
        les_routers = []
        for router in data[ROUTER_LIST_NAME]:
            hostname = router["hostname"]
            links = router["links"]
            as_number = router["AS_number"]
            position = router.get("position", {"x": 0, "y": 0})
            les_routers.append(Router(hostname, links, as_number, position))
        return (les_as, les_routers)
