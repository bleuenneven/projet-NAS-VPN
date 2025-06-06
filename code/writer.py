from autonomous_system import AS

LINKS_STANDARD = ["FastEthernet0/0", "GigabitEthernet1/0", "GigabitEthernet2/0", "GigabitEthernet3/0",
                  "GigabitEthernet4/0", "GigabitEthernet5/0", "GigabitEthernet6/0"]
NOM_PROCESSUS_IGP_PAR_DEFAUT = "1984"
IPV4_UNICAST_STRING = """no ip domain lookup
ip unicast-routing
ip cef
"""
LOCAL_PREF_ROUTE_MAPS = """
route-map tag_pref_provider permit 10
 set local-preference 100
route-map tag_pref_peer permit 10
 set local-preference 200
route-map tag_pref_customer permit 10
 set local-preference 300
"""
STANDARD_LOOPBACK_INTERFACE = "Loopback1"

def get_ospf_config_string(AS, router):
    """
    Fonction qui génère la configuration OSPF d'un routeur avec son AS

    entrées : AS: Autonomous System et router un Router
    sortie : str contenant la configuration correspondante
    """
    ospf_config_string = f"router ospf {NOM_PROCESSUS_IGP_PAR_DEFAUT}\n"
    ospf_config_string += f" router-id {router.router_id}.{router.router_id}.{router.router_id}.{router.router_id}\n"# network {router.loopback_address}/128 area 0\n"
    for passive in router.passive_interfaces:
        ospf_config_string += f" passive-interface {passive}\n"
    if not AS.is_vpn_client:
        ospf_config_string += f" mpls traffic-eng router-id Loopback1\n mpls traffic-eng area 0\n"
    return ospf_config_string


def get_rip_config_string(AS, router):
    """
    Fonction qui génère la configuration RIP d'un routeur avec son AS

    entrées : AS: Autonomous System et router un Router
    sortie : str contenant la configuration correspondante
    """
    rip_config_string = f"router rip {NOM_PROCESSUS_IGP_PAR_DEFAUT}\n"
    for passive in router.passive_interfaces:
        pass
        #rip_config_string += f" passive-interface {passive}\n"
    return rip_config_string


def get_final_config_string(AS: AS, router: "Router", mode: str, all_as:dict[int, AS]):
	"""
	Génère le string de configuration "final" pour un router, à mettre à la place de sa configuration interne

	entrées : AS: Autonomous System et router un Router, ainsi que mode indiquant si on est en "cfg" ou "telnet"
	sortie : str contenant la configuration correspondante (bien complète, pas besoin de parsing ou de manipulation de string en +) OU liste de str de commandes si mode == "telnet"
	"""
	if mode == "telnet":
		# todo : telnet command
		return get_all_telnet_commands(AS, router, all_as)
	if AS.internal_routing == "OSPF":
		internal_routing = get_ospf_config_string(AS, router)
	else:
		internal_routing = get_rip_config_string(AS, router)
	total_interface_string = ""
	for config_string in router.config_str_per_link.values():
		total_interface_string += config_string
	for config_string in router.extra_loopbacks.values():
		total_interface_string += config_string["interface_data"]
	route_maps = ""
	community_lists = AS.full_community_lists
	for autonomous in router.used_route_maps:
		if AS.community_data[autonomous].get("route_map_in", False) != False:
			route_maps += AS.community_data[autonomous]["route_map_in"]
		else:
			vrf_def:str = AS.community_data[autonomous].get("vrf_def", [""]).pop()
			for (ce, data) in router.extra_loopbacks.items():
				if ce in all_as[autonomous].routers:
					vrf_def = vrf_def.replace("REPLACEME", "\n" + data["next_hop"])
			
			vrf_def = vrf_def.replace("REPLACEME", "")
			route_maps += vrf_def
			route_maps += AS.community_data[autonomous].get("vpn_route_map", "")

			if all_as[autonomous].vpn_te_route_maps != {}:
				for ((r1, r2),data) in all_as[autonomous].vpn_te_route_maps.items():
					if r1 == router.hostname:

						route_maps += data["route_map_ce_out"]
			else:
				for ((r1, r2),data) in AS.vpn_te_route_maps.items():
					if r1 == router.hostname:
						route_maps += data["route_map_pe_in"]
						community_lists += data["community_list"]
	paths = ""
	routes = ""
	for (path_str, tunnel_interface, route) in router.tunnel_configs:
		total_interface_string += tunnel_interface + "!\n"
		paths += path_str + "!\n"
		routes += route + "!\n"
	route_maps += AS.global_route_map_out
	return f"""!
!
!
!
!
!
service timestamps debug datetime msec
service timestamps log datetime msec
no service password-encryption
!
hostname {router.hostname}
!
boot-start-marker
boot-end-marker
!
!
!
no aaa new-model
no ip icmp rate-limit unreachable
ip cef
!
!
!
!
!
no ip domain lookup
ip cef
!
!
multilink bundle-name authenticated
!
{"" if AS.is_vpn_client else "mpls traffic-eng tunnels"}
!
!
!
!
!
!
!
ip tcp synwait-time 5
no cdp log mismatch duplex
! 
!
!
ip bgp-community new-format
!
!
{paths}
!
!
{community_lists}
!
!
{route_maps}
!
!
interface {STANDARD_LOOPBACK_INTERFACE}
 ip address {router.loopback_address} 255.255.255.255
 {router.internal_routing_loopback_config}
!
!
{total_interface_string}
{router.config_bgp}
!
ip forward-protocol nd
!
!
no ip http server
no ip http secure-server
{routes}
!
{internal_routing}
!
!
!
!
control-plane
!
!
line con 0
 exec-timeout 0 0
 privilege level 15
 logging synchronous
 stopbits 1
line aux 0
 exec-timeout 0 0
 privilege level 15
 logging synchronous
 stopbits 1
line vty 0 4
 login
!
!
end
"""


def get_all_telnet_commands(AS:AS, router:"Router", all_as:dict[int, AS]):
	"""
	Génère et renvoie une liste de commandes telnet à partir d'un AS et d'un routeur que l'on SUPPOSE avoir été configuré en mode "telnet"
	
	entrées : AS: Autonomous System et router un Router
	sortie : liste de str de commandes telnet à exécuter telles quelles sur une session telnet ouverte du routeur correspondant dans le projet GNS3 voulu
	"""
	community_list_setup = AS.full_community_lists.split("\n")
	liste_raw = AS.global_route_map_out.split("\n")
	if len(liste_raw) > 3:
		route_maps_setup = liste_raw[:len(liste_raw) - 3] + ["exit"] + [liste_raw[-3]] + ["exit"]
	else:
		route_maps_setup = [AS.global_route_map_out.split("\n")[0]] + ["exit"]
	if AS.internal_routing == "OSPF":
		internal_routing = get_ospf_config_string(AS, router).split("\n") + ["exit"]
	else:
		internal_routing = get_rip_config_string(AS, router).split("\n") + ["exit"]
	bgp_setup = router.config_bgp.split("\n")
	loopback_setup = router.internal_routing_loopback_config.split("\n") + ["exit"]
	for autonomous in router.used_route_maps:
		if AS.community_data[autonomous].get("route_map_in", False) != False:
			route_maps_setup += AS.community_data[autonomous]["route_map_in"].split("\n")
			route_maps_setup += ["exit"]
		else:
			vrf_def:str = AS.community_data[autonomous].get("vrf_def", [""]).pop()
			for (ce, data) in router.extra_loopbacks.items():
				if ce in all_as[autonomous].routers:
					vrf_def = vrf_def.replace("REPLACEME", "\n" + data["next_hop"])
			vrf_def = vrf_def.replace("REPLACEME", "")
			route_maps_setup += vrf_def.split("\n")
			route_maps_setup += AS.community_data[autonomous].get("vpn_route_map", "").split("\n")
			if all_as[autonomous].vpn_te_route_maps != {}:
				for ((r1, r2),data) in all_as[autonomous].vpn_te_route_maps.items():
					if r1 == router.hostname:

						route_maps_setup += data["route_map_ce_out"].split("\n")
			else:
				for ((r1, r2),data) in AS.vpn_te_route_maps.items():
					if r1 == router.hostname:
						route_maps_setup += data["route_map_pe_in"].split("\n")
						community_list_setup += data["community_list"].split("\n")
		
	interface_configs = []
	for interface in router.config_str_per_link.values():
		interface_configs += interface.split("\n")
	for config_string in router.extra_loopbacks.values():
		interface_configs += config_string["interface_data"].split("\n") + ["exit"]
	paths = []
	routes = []
	for (path_str, tunnel_interface, route) in router.tunnel_configs:
		interface_configs += tunnel_interface.split("\n") + ["exit"]
		paths += path_str.split("\n") + ["exit"]
		routes += route.split("\n")
	final = (["config t", "ip bgp-community new-format", "mpls traffic-eng tunnels" if not AS.is_vpn_client else "",
	          "ip unicast-routing"] + community_list_setup + route_maps_setup + paths + internal_routing + loopback_setup + interface_configs + ([f"router ospf {NOM_PROCESSUS_IGP_PAR_DEFAUT}", "mpls traffic-eng router-id Loopback1", "exit"] if not AS.is_vpn_client else []) + routes + bgp_setup)
	for commande in list(final):
		if "!" in commande:
			final.remove(commande)
		elif commande == "":
			final.remove(commande)
	return final