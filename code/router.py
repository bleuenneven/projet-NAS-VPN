from GNS3 import Connector
from autonomous_system import AS
from ipv4 import SubNetwork
from writer import LINKS_STANDARD, NOM_PROCESSUS_IGP_PAR_DEFAUT, STANDARD_LOOPBACK_INTERFACE
from ipaddress import IPv4Address


class Router:
    def __init__(self, hostname: str, links, AS_number: int, position=None):
        self.hostname = hostname
        self.links = links
        self.AS_number = AS_number
        self.passive_interfaces = set()
        self.loopback_interfaces = set()
        self.counter_loopback_interfaces = 0
        self.router_id = None
        self.subnetworks_per_link = {}
        self.loopback_subnetworks_per_link = {}
        self.ip_per_link = {}
        self.loopback_ip_per_link = {}
        self.interface_per_link = {}
        self.loopback_interface_per_link = {}
        self.config_str_per_link = {}
        self.loopback_config_str_per_link = {}
        self.voisins_ebgp = {}
        self.voisins_ibgp = set()
        self.available_interfaces = [LINKS_STANDARD[i] for i in range(len(LINKS_STANDARD))]
        self.config_bgp = "!"
        self.position = position if position else {"x": 0, "y": 0}
        self.loopback_address = IPv4Address("0.0.0.0")
        self.internal_routing_loopback_config = ""
        self.route_maps = {}
        self.used_route_maps = set()
        self.is_pe = False
        self.vpn_neighbors = set()
        self.tunnel_configs = []
        self.extra_loopbacks = {}
        self.enforced_loopbacks = {}

    def __str__(self):
        return f"hostname:{self.hostname}\n links:{self.links}\n as_number:{self.AS_number}"
    
    def compute_is_pe(self, autonomous_systems:dict[int, AS], all_routers: dict[str, "Router"]):
        """
        Calcule et stocke si ce routeur est un routeur de bordure dans l'attribut is_pe

        input : self (méthode), dictionnaire numéro_d'AS:AS, dictionnaire nom_des_routeurs:Router
        output : rien, modification de self.is_pe
        """
    
    def compute_connex_neighborhood(self, all_routers:dict[str, "Router"]):
        """
        Calcule le voisinnage connexe du routeur, c'est à dire tous les autres routeurs de son AS qui doivent être en iBGP

        entrées : self (méthode), dictionnaire nom_des_routeurs:Router
        sorties : modification de l'attribut self.connex_neighborhood
        """
        self.connex_neighborhood = set()
        self.routers_to_test = [self.hostname]
        while len(self.routers_to_test) > 0:
            router = all_routers[self.routers_to_test.pop(0)]
            for link in router.links:
                if router.AS_number == all_routers[link["hostname"]].AS_number and not link["hostname"] in self.connex_neighborhood:
                    self.connex_neighborhood.add(link["hostname"])
                    self.routers_to_test.append(link["hostname"])

    def cleanup_used_interfaces(self, autonomous_systems: dict[int, AS], all_routers: dict[str, "Router"],
                                connector: Connector):
        """
        Enlève les interfaces déjà utilisées de self.available_interfaces

        entrées : self (méthode), dictionnaire numéro_d'AS:AS, dictionnaire nom_des_routeurs:Router et Connector au projet GNS3 local
        sorties : changement de self.available_interfaces
        """
        self.compute_connex_neighborhood(all_routers)
        for link in self.links:
            if link.get("interface", False):
                interface_to_remove = link["interface"]
                if interface_to_remove in self.available_interfaces:
                    self.available_interfaces.remove(interface_to_remove)
                    self.interface_per_link[link["hostname"]] = interface_to_remove
            else:
                try:
                    interface_to_remove = connector.get_used_interface_for_link(self.hostname, link["hostname"])
                    if LINKS_STANDARD[interface_to_remove] in self.available_interfaces:
                        self.available_interfaces.remove(LINKS_STANDARD[interface_to_remove])
                        self.interface_per_link[link["hostname"]] = LINKS_STANDARD[interface_to_remove]
                except KeyError as e:
                    print(f"Warning: {e}. Skipping this link.")
                except Exception as e:
                    print(f"Unexpected error during interface cleanup: {self.hostname}->{link['hostname']}: {e}")

    def create_router_if_missing(self, connector: Connector):
        """
        Crée le routeur correspondant dans le projet GNS3 donné si il n'existe pas

        input : Connector au projet GNS3 local
        sorties : changement du projet GNS3
        """
        try:
            connector.get_node(self.hostname)
        except Exception:
            print(f"Node {self.hostname} missing ! Creating node...")
            connector.create_node(self.hostname, "c7200")

    def create_missing_links(self, autonomous_systems: dict[int, AS], all_routers: dict[str, "Router"],
                             connector: Connector):
        """
        Enlève les interfaces déjà utilisées de self.available_interfaces

        entrées :self (méthode), dictionnaire numéro_d'AS:AS, dictionnaire nom_des_routeurs:Router et Connector au projet GNS3 local
        sorties : changement de self.available_interfaces
        """
        for link in self.links:
            if link.get("interface", False):
                interface_1_to_use = link["interface"]
                other_link = None
                for other in all_routers[link["hostname"]].links:
                    if other["hostname"] == self.hostname:
                        other_link = other
                        break
                if other_link != None:
                    if other_link.get("interface", False):
                        interface_2_to_use = other_link["interface"]
                    else:
                        interface_2_to_use = all_routers[link["hostname"]].interface_per_link[self.hostname]
                    print(f"1 : {self.hostname} {link["hostname"]}")
                    connector.create_link_if_it_doesnt_exist(self.hostname, link["hostname"],
                                                             LINKS_STANDARD.index(interface_1_to_use),
                                                             LINKS_STANDARD.index(interface_2_to_use))
                else:
                    raise KeyError("Le routeur cible n'a pas de lien dans l'autre sens")
            else:
                interface_1_to_use = self.interface_per_link[link["hostname"]]
                other_link = None
                for other in all_routers[link["hostname"]].links:
                    if other["hostname"] == self.hostname:
                        other_link = other
                        break
                if other_link != None:
                    if other_link.get("interface", False):
                        interface_2_to_use = other_link["interface"]
                    else:
                        interface_2_to_use = all_routers[link["hostname"]].interface_per_link[self.hostname]
                    print(f"1 : {self.hostname} {link["hostname"]}")
                    connector.create_link_if_it_doesnt_exist(self.hostname, link["hostname"],
                                                             LINKS_STANDARD.index(interface_1_to_use),
                                                             LINKS_STANDARD.index(interface_2_to_use))
                else:
                    
                    raise KeyError(f"Le routeur {link["hostname"]} n'a pas de lien dans l'autre sens vers {self.hostname}")

    def set_interface_configuration_data(self, autonomous_systems: dict[int, AS], all_routers: dict[str, "Router"],
                                         mode: str):
        """
        Génère les string de configuration par lien pour le routeur self

        entrées : self (méthode), dictionnaire numéro_d'AS:AS, dictionnaire nom_des_routeurs:Router
        sorties : changement de plusieurs attributs de l'objet, mais surtout de config_str_per_link qui est rempli des string de configuration valides
        """
        my_as = autonomous_systems[self.AS_number]

        for link in self.links:
            if not self.interface_per_link.get(link["hostname"], False):
                interface_for_link = self.available_interfaces.pop(0)
            else:
                interface_for_link = "FastEthernet2019857/0"

            self.interface_per_link[link["hostname"]] = self.interface_per_link.get(link["hostname"],
                                                                                    interface_for_link)
            if not self.subnetworks_per_link.get(link["hostname"], False):
                if link["hostname"] in my_as.hashset_routers:
                    self.subnetworks_per_link[link["hostname"]] = my_as.ipv4_prefix.next_subnetwork_with_n_routers(2)
                    all_routers[link["hostname"]].subnetworks_per_link[self.hostname] = self.subnetworks_per_link[
                        link["hostname"]]
                else:
                    self.passive_interfaces.add(self.interface_per_link[link["hostname"]])
                    picked_transport_interface = SubNetwork(
                        my_as.connected_AS_dict[all_routers[link["hostname"]].AS_number][1][self.hostname], 2)
                    self.subnetworks_per_link[link["hostname"]] = picked_transport_interface
                    all_routers[link["hostname"]].subnetworks_per_link[self.hostname] = picked_transport_interface
            elif link["hostname"] not in my_as.hashset_routers:
                self.passive_interfaces.add(self.interface_per_link[link["hostname"]])
            ip_address = self.subnetworks_per_link[link["hostname"]].get_ip_address_with_router_id(
                self.subnetworks_per_link[link["hostname"]].get_next_router_id())
            self.ip_per_link[link["hostname"]] = ip_address
            am_vpn_provider = self.AS_number != all_routers[link["hostname"]].AS_number and my_as.community_data[all_routers[link["hostname"]].AS_number].get("VPN", False) and (not my_as.community_data[all_routers[link["hostname"]].AS_number]["am_client"])
            if am_vpn_provider:
                self.vpn_neighbors.add(link["hostname"])
            if mode == "cfg":
                extra_config = "\n!\n"
                mpls_extra = ""
                if self.AS_number == all_routers[link["hostname"]].AS_number:
                    mpls_extra = " mpls ip\n  mpls traffic-eng tunnels\n  ip rsvp bandwidth\n"
                if my_as.internal_routing == "OSPF":
                    if not link.get("ospf_cost", False):
                        if am_vpn_provider:
                            extra_config = f" vrf forwarding {my_as.community_data[all_routers[link["hostname"]].AS_number]["nom_vrf"]}\n ip ospf {NOM_PROCESSUS_IGP_PAR_DEFAUT} area 0\n"
                        else:
                            extra_config = f"ip ospf {NOM_PROCESSUS_IGP_PAR_DEFAUT} area 0\n"
                        
                    else:
                        if am_vpn_provider:
                            extra_config = f"vrf forwarding {my_as.community_data[all_routers[link["hostname"]].AS_number]["nom_vrf"]}\n ip ospf {NOM_PROCESSUS_IGP_PAR_DEFAUT} area 0\n ip ospf cost {link["ospf_cost"]}\n"
                        else:
                            extra_config = f"ip ospf {NOM_PROCESSUS_IGP_PAR_DEFAUT} area 0\n ip ospf cost {link["ospf_cost"]}\n"
                elif my_as.internal_routing == "RIP":
                    if am_vpn_provider:
                        extra_config = f"vrf forwarding {my_as.community_data[all_routers[link["hostname"]].AS_number]["nom_vrf"]}\n ip rip {NOM_PROCESSUS_IGP_PAR_DEFAUT} enable\n"
                    else:
                        extra_config = f"ip rip {NOM_PROCESSUS_IGP_PAR_DEFAUT} enable\n"
                
                self.config_str_per_link[link["hostname"]] = f"interface {self.interface_per_link[link["hostname"]]}\n {extra_config}{mpls_extra} ip address {str(ip_address)} {self.subnetworks_per_link[link["hostname"]].get_subnet_mask()}\n!\n "
            elif mode == "telnet":
                extra_config = ""
                
                if my_as.internal_routing == "OSPF":
                    if not link.get("ospf_cost", False):
                        if am_vpn_provider:
                            extra_config = f" vrf forwarding {my_as.community_data[all_routers[link["hostname"]].AS_number]["nom_vrf"]}\n ip ospf {NOM_PROCESSUS_IGP_PAR_DEFAUT} area 0\n"
                        else:
                            extra_config = f"ip ospf {NOM_PROCESSUS_IGP_PAR_DEFAUT} area 0\n"
                        
                    else:
                        if am_vpn_provider:
                            extra_config = f"vrf forwarding {my_as.community_data[all_routers[link["hostname"]].AS_number]["nom_vrf"]}\n ip ospf {NOM_PROCESSUS_IGP_PAR_DEFAUT} area 0\n ip ospf cost {link["ospf_cost"]}\n"
                        else:
                            extra_config = f"ip ospf {NOM_PROCESSUS_IGP_PAR_DEFAUT} area 0\n ip ospf cost {link["ospf_cost"]}\n"
                elif my_as.internal_routing == "RIP":
                    if am_vpn_provider:
                        extra_config = f"vrf forwarding {my_as.community_data[all_routers[link["hostname"]].AS_number]["nom_vrf"]}\n ip rip {NOM_PROCESSUS_IGP_PAR_DEFAUT} enable\n"
                    else:
                        extra_config = f"ip rip {NOM_PROCESSUS_IGP_PAR_DEFAUT} enable\n"
                if self.AS_number == all_routers[link["hostname"]].AS_number:
                    extra_config += "mpls ip\n mpls traffic-eng tunnels\n ip rsvp bandwidth\n"
                self.config_str_per_link[link[
                    "hostname"]] = f"interface {self.interface_per_link[link["hostname"]]}\n {extra_config} no shutdown\n mpls ip\n ip address {str(ip_address)} {self.subnetworks_per_link[link["hostname"]].get_subnet_mask()}\n exit\n"

    def set_loopback_configuration_data(self, autonomous_systems: dict[int, AS], all_routers: dict[str, "Router"],
                                        mode: str):
        """
        génère la configuration de loopback unique au routeur ou les commandes de l'interface de loopback du routeur en fonction du mode

        entrées: self (méthode), dictionnaire numéro_d'AS:AS, dictionnaire nom_des_routeurs:Router et mode un str valant "cfg" ou "telnet"
        sorties : modifie self.router_id, self.loopback_address
        
        """
        my_as = autonomous_systems[self.AS_number]
        router_id = my_as.global_router_counter.get_next_router_id()
        self.router_id = router_id
        self.loopback_address = my_as.loopback_prefix.get_ip_address_with_router_id(router_id)
        if my_as.internal_routing == "OSPF":
            if mode == "cfg":
                self.internal_routing_loopback_config = f"ip ospf {NOM_PROCESSUS_IGP_PAR_DEFAUT} area 0\n!\n"
            elif mode == "telnet":
                # todo : telnet command
                self.internal_routing_loopback_config = f"interface {STANDARD_LOOPBACK_INTERFACE}\nip address {self.loopback_address} 255.255.255.255\nip ospf {NOM_PROCESSUS_IGP_PAR_DEFAUT} area 0\nmpls traffic-eng tunnels\nip rsvp bandwidth\n"
        elif my_as.internal_routing == "RIP":
            if mode == "cfg":
                self.internal_routing_loopback_config = f"ip rip {NOM_PROCESSUS_IGP_PAR_DEFAUT} enable\n!\n"
            elif mode == "telnet":
                # todo : telnet command
                self.internal_routing_loopback_config = f"interface {STANDARD_LOOPBACK_INTERFACE}\nip address {self.loopback_address} 255.255.255.255\nip rip {NOM_PROCESSUS_IGP_PAR_DEFAUT} enable\nmpls traffic-eng tunnels\nip rsvp bandwidth\n"

    def set_tunnel_config_data(self, autonomous_systems:dict[int, AS], all_routers: dict[str, "Router"], mode: str):
        """
        Génère le string de configuration bgp du router self

        entrées : self (méthode), dictionnaire numéro_d'AS:AS, dictionnaire nom_des_routeurs:Router et string de mode de configuration (cfg ou telnet)
        sorties : changement de plusieurs attributs de l'objet, mais surtout de config_bgp qui contient le string de configuration à la fin de l'exécution de la fonction
        """
        my_as = autonomous_systems[self.AS_number]
        for ((host, source), data) in my_as.global_allocated_tunnels.items():
            if host == self.hostname:
                indice = 1
                explicit_path_str = f"ip explicit-path name path{data["tunnel_number"]} enable\n"
                last_router = self.hostname
                route_index = 1
                penultimate = data["internal_route"][-2]
                for r in data["internal_route"]:
                    next_router = data["internal_route"][route_index if route_index < len(data["internal_route"]) else -1]
                    if last_router == r:
                        pass
                        #explicit_path_str += f" index {indice} next-address loose {all_routers[r].loopback_address}\n"

                    else:
                        explicit_path_str += f" index {indice} next-address {all_routers[r].ip_per_link[last_router]}\n"
                        indice += 1
                    if next_router == r:
                        pass
                        #explicit_path_str += f" index {indice} next-address loose {all_routers[r].loopback_address}\n"
                    else:
                        explicit_path_str += f" index {indice} next-address {all_routers[r].ip_per_link[next_router]}\n"
                    indice += 1
                    route_index += 1
                    last_router = r
                target_address = all_routers[data["internal_route"][-1]].set_and_get_new_enforced_loopback(autonomous_systems, all_routers, mode, data["route"][-1])
                local_tunnel_number = len(self.tunnel_configs) + 1
                interface_tunnel = f"interface Tunnel{local_tunnel_number}\n ip unnumbered Loopback1\n tunnel mode mpls traffic-eng\n tunnel source Loopback1\n tunnel destination {all_routers[data["internal_route"][-1]].ip_per_link[penultimate]}\n tunnel mpls traffic-eng autoroute announce\n tunnel mpls traffic-eng priority 1 1\n tunnel mpls traffic-eng bandwidth 5000\n tunnel mpls traffic-eng path-option 10 explicit name path{data["tunnel_number"]}\n tunnel mpls traffic-eng record-route\n"
                extra_route = f"ip route {target_address} 255.255.255.255 Tunnel{local_tunnel_number}\n"
                self.tunnel_configs.append((explicit_path_str, interface_tunnel, extra_route))

    def set_and_get_new_enforced_loopback(self, autonomous_systems: dict[int, AS], all_routers: dict[str, "Router"], mode: str, client:str):
        """
        génère et renvoie l'addresse d'une nouvelle loopback rajoutée comme next hop à la configuration de la VRF du client correspondant
        """
        if self.extra_loopbacks.get(client, False) == False:
                
            my_as = autonomous_systems[self.AS_number]
            router_id = my_as.global_router_counter.get_next_router_id()
            extra_loopback_address = my_as.loopback_prefix.get_ip_address_with_router_id(router_id)
            if my_as.internal_routing == "OSPF":
                if mode == "cfg":
                    internal_routing_loopback_config = f"ip ospf {NOM_PROCESSUS_IGP_PAR_DEFAUT} area 0\n!\n"
                elif mode == "telnet":
                    # todo : telnet command
                    internal_routing_loopback_config = f"ip ospf {NOM_PROCESSUS_IGP_PAR_DEFAUT} area 0\n"
            elif my_as.internal_routing == "RIP":
                if mode == "cfg":
                    internal_routing_loopback_config = f"ip rip {NOM_PROCESSUS_IGP_PAR_DEFAUT} enable\n!\n"
                elif mode == "telnet":
                    # todo : telnet command
                    internal_routing_loopback_config = f"ip rip {NOM_PROCESSUS_IGP_PAR_DEFAUT} enable\n"
            self.extra_loopbacks[client] = {
                "interface_name":f"Loopback{len(self.extra_loopbacks) + 2}",
                "interface_data":f"interface Loopback{len(self.extra_loopbacks) + 2}\n ip address {extra_loopback_address} 255.255.255.255\n mpls traffic-eng tunnels\n ip rsvp bandwidth\n{internal_routing_loopback_config}",
                "address":extra_loopback_address,
                "next_hop":f"bgp next-hop Loopback{len(self.extra_loopbacks) + 2}\n",
                "bgp_extra":f"  network {extra_loopback_address} mask 255.255.255.255\n"
            }
            return extra_loopback_address
        else:
            return self.extra_loopbacks[client]["address"]

    def set_bgp_config_data(self, autonomous_systems: dict[int, AS], all_routers: dict[str, "Router"], mode: str):
        """
        Génère le string de configuration bgp du router self

        entrées : self (méthode), dictionnaire numéro_d'AS:AS, dictionnaire nom_des_routeurs:Router
        sorties : changement de plusieurs attributs de l'objet, mais surtout de config_bgp qui contient le string de configuration à la fin de l'exécution de la fonction
        """
        self.set_tunnel_config_data(autonomous_systems, all_routers, mode)
        my_as = autonomous_systems[self.AS_number]
        if len(my_as.hashet_RRs) == 0 or self.hostname in my_as.hashet_RRs:
            self.voisins_ibgp = my_as.hashset_routers.difference({self.hostname}).intersection(self.connex_neighborhood)
        else:
            self.voisins_ibgp = my_as.hashet_RRs.intersection(self.connex_neighborhood)
        for link in self.links:
            if all_routers[link["hostname"]].AS_number != self.AS_number:
                self.voisins_ebgp[link["hostname"]] = all_routers[link["hostname"]].AS_number
        if mode == "telnet":
            # todo : telnet commands
            self.config_bgp = f"router bgp {self.AS_number}\nbgp router-id {self.router_id}.{self.router_id}.{self.router_id}.{self.router_id}\n"
            config_ipv4_af = "address-family ipv4 unicast\n"
            config_vpnv4_af = "address-family vpnv4 unicast\n"
            config_neighbors_ibgp = ""
            for voisin_ibgp in self.voisins_ibgp:
                remote_ip = all_routers[voisin_ibgp].loopback_address
                config_neighbors_ibgp += f"neighbor {remote_ip} remote-as {self.AS_number}\nneighbor {remote_ip} update-source {STANDARD_LOOPBACK_INTERFACE}\n"
                if len(my_as.hashet_RRs) == 0 or not self.hostname in my_as.hashet_RRs:
                    config_ipv4_af += f"neighbor {remote_ip} activate\nneighbor {remote_ip} send-community both\n"
                    config_vpnv4_af += f"neighbor {remote_ip} activate\nneighbor {remote_ip} send-community both\n"
                else:
                    config_vpnv4_af += f"  neighbor {remote_ip} activate\n  neighbor {remote_ip} send-community both\n neighbor {remote_ip} route-reflector-client\n"
                    config_ipv4_af += f"  neighbor {remote_ip} activate\n  neighbor {remote_ip} send-community both\n neighbor {remote_ip} route-reflector-client\n"
                
            config_neighbors_ebgp = ""
            for voisin_ebgp in self.voisins_ebgp:
                if voisin_ebgp not in self.vpn_neighbors:
                    remote_ip = all_routers[voisin_ebgp].ip_per_link[self.hostname]
                    remote_as = all_routers[voisin_ebgp].AS_number
                    config_neighbors_ebgp += f"neighbor {remote_ip} remote-as {all_routers[voisin_ebgp].AS_number}\n"  # neighbor {remote_ip} update-source {STANDARD_LOOPBACK_INTERFACE}\n neighbor {remote_ip} ebgp-multihop 2\n"
                    if my_as.community_data[remote_as].get("route_map_in_bgp_name", False) != False:
                        config_ipv4_af += f"neighbor {remote_ip} activate\nneighbor {remote_ip} send-community both\nneighbor {remote_ip} route-map {my_as.community_data[remote_as]["route_map_in_bgp_name"]} in\n"
                        if my_as.connected_AS_dict[remote_as][0] != "client":
                            config_ipv4_af += f"neighbor {remote_ip} route-map General-OUT out\n"
                    else:
                        config_ipv4_af += f"neighbor {remote_ip} activate\nneighbor {remote_ip} send-community both\n"
                    if self.hostname in all_routers[voisin_ebgp].vpn_neighbors:
                        config_ipv4_af += f"neighbor {remote_ip} allowas-in 5\n"
                        if (self.hostname, voisin_ebgp) in autonomous_systems[remote_as].vpn_te_route_maps.keys():
                            config_ipv4_af += f"neighbor {remote_ip} route-map {autonomous_systems[remote_as].vpn_te_route_maps[(self.hostname, voisin_ebgp)]["RM_name"]} out\n"
                    self.used_route_maps.add(remote_as)

            config_ipv4_af += f"network {self.loopback_address} mask 255.255.255.255\nexit\n"
            for data in self.extra_loopbacks.values():
                config_ipv4_af += data["bgp_extra"] + "exit\n"
            config_vpnv4_af += "exit\n"
            self.config_bgp += config_neighbors_ibgp
            self.config_bgp += config_neighbors_ebgp
            self.config_bgp += config_ipv4_af
            self.config_bgp += config_vpnv4_af
            vpn_address_families = ""
            for voisin_vpn in list(self.vpn_neighbors):
                remote_ip = all_routers[voisin_vpn].ip_per_link[self.hostname]
                remote_as = all_routers[voisin_vpn].AS_number
                self.used_route_maps.add(remote_as)
                extra_route_mapping = ""
                if my_as.vpn_te_route_maps.get((self.hostname, voisin_vpn), False) != False:
                    extra_route_mapping = f"  neighbor {remote_ip} route-map {my_as.vpn_te_route_maps[(self.hostname, voisin_vpn)]["RM_name"]} in\n"
                vpn_address_families += f"address-family ipv4 vrf {autonomous_systems[self.AS_number].community_data[remote_as]["nom_vrf"]}\nneighbor {remote_ip} remote-as {remote_as}\nneighbor {remote_ip} activate\n{extra_route_mapping} exit\n"
            self.config_bgp += vpn_address_families
            self.config_bgp += "exit\nexit\n"
            
        elif mode == "cfg":
            config_vpnv4_af = ""
            config_ipv4_af = ""
            config_neighbors_ibgp = ""
            for voisin_ibgp in self.voisins_ibgp:
                remote_ip = all_routers[voisin_ibgp].loopback_address
                config_neighbors_ibgp += f"  neighbor {remote_ip} remote-as {self.AS_number}\n  neighbor {remote_ip} update-source {STANDARD_LOOPBACK_INTERFACE}\n"
                #if self.hostname in my_as.hashset_pe_routers and voisin_ibgp in my_as.hashset_pe_routers:
                if len(my_as.hashet_RRs) == 0 or not self.hostname in my_as.hashet_RRs:
                    config_vpnv4_af += f"  neighbor {remote_ip} activate\n  neighbor {remote_ip} send-community both\n"
                    config_ipv4_af += f"  neighbor {remote_ip} activate\n  neighbor {remote_ip} send-community both\n"
                else:
                    config_vpnv4_af += f"  neighbor {remote_ip} activate\n  neighbor {remote_ip} send-community both\n neighbor {remote_ip} route-reflector-client\n"
                    config_ipv4_af += f"  neighbor {remote_ip} activate\n  neighbor {remote_ip} send-community both\n neighbor {remote_ip} route-reflector-client\n"
            config_neighbors_ebgp = ""
            for voisin_ebgp in self.voisins_ebgp:
                if voisin_ebgp not in self.vpn_neighbors:
                    remote_ip = all_routers[voisin_ebgp].ip_per_link[self.hostname]
                    remote_as = all_routers[voisin_ebgp].AS_number
                    config_neighbors_ebgp += f"  neighbor {remote_ip} remote-as {all_routers[voisin_ebgp].AS_number}\n"  # neighbor {remote_ip} update-source {STANDARD_LOOPBACK_INTERFACE}\n neighbor {remote_ip} ebgp-multihop 2\n"
                    if my_as.community_data[remote_as].get("route_map_in_bgp_name", False) != False:
                        config_ipv4_af += f"  neighbor {remote_ip} activate\n  neighbor {remote_ip} send-community both\n  neighbor {remote_ip} route-map {my_as.community_data[remote_as]["route_map_in_bgp_name"]} in\n"
                        if my_as.connected_AS_dict[remote_as][0] != "client":
                            config_ipv4_af += f"  neighbor {remote_ip} route-map General-OUT out\n"
                    else:
                        config_ipv4_af += f"  neighbor {remote_ip} activate\n  neighbor {remote_ip} send-community both\n"
                    if self.hostname in all_routers[voisin_ebgp].vpn_neighbors:
                        config_ipv4_af += f"  neighbor {remote_ip} allowas-in 5\n"
                        if (self.hostname, voisin_ebgp) in autonomous_systems[remote_as].vpn_te_route_maps.keys():
                            config_ipv4_af += f"  neighbor {remote_ip} route-map {autonomous_systems[remote_as].vpn_te_route_maps[(self.hostname, voisin_ebgp)]["RM_name"]} out\n"
                    
                    self.used_route_maps.add(remote_as)
            
            config_ipv4_af += f"  network {self.loopback_address} mask 255.255.255.255\n"
            for data in self.extra_loopbacks.values():
                config_ipv4_af += data["bgp_extra"]
            vpn_address_families = ""
            for voisin_vpn in list(self.vpn_neighbors):
                remote_ip = all_routers[voisin_vpn].ip_per_link[self.hostname]
                remote_as = all_routers[voisin_vpn].AS_number
                self.used_route_maps.add(remote_as)
                extra_route_mapping = ""
                if my_as.vpn_te_route_maps.get((self.hostname, voisin_vpn), False) != False:
                    extra_route_mapping = f"  neighbor {remote_ip} route-map {my_as.vpn_te_route_maps[(self.hostname, voisin_vpn)]["RM_name"]} in\n"
                vpn_address_families += f" address-family ipv4 vrf {autonomous_systems[self.AS_number].community_data[remote_as]["nom_vrf"]}\n  neighbor {remote_ip} remote-as {remote_as}\n  neighbor {remote_ip} activate \n{extra_route_mapping} exit-address-family\n!\n"
            
            self.config_bgp = f"""
router bgp {self.AS_number}
 bgp router-id {self.router_id}.{self.router_id}.{self.router_id}.{self.router_id}
 bgp log-neighbor-changes
{config_neighbors_ibgp}{config_neighbors_ebgp}
 address-family vpnv4
{config_vpnv4_af}
 exit-address-family
!
 address-family ipv4
{config_ipv4_af}
 exit-address-family
!
{vpn_address_families}
!
"""

    def update_router_position(self, connector):
        try:
            connector.update_node_position(self.hostname, self.position["x"], self.position["y"])
        except Exception as e:
            print(f"Error updating position for {self.hostname}: {e}")
