from ipaddress import IPv4Address, IPv4Network
from ipv4 import SubNetwork


class GlobalRouterIDCounter:
    def __init__(self):
        self.number = 1
    def get_next_router_id(self) -> int:
        temp = self.number
        self.number += 1
        return temp

class AS:
    def __init__(self, ipv4_prefix: SubNetwork, AS_number: int, routers: list["Router"], internal_routing: str, connected_AS: list[tuple[int, str, dict[str, str], ]], loopback_prefix: SubNetwork, counter:GlobalRouterIDCounter, route_reflectors:list[str]):
        self.ipv4_prefix = ipv4_prefix
        self.AS_number = AS_number
        self.routers = routers
        self.route_distinguishers = 1
        self.allocated_vpn_communities = 0
        self.internal_routing = internal_routing
        self.connected_AS = connected_AS
        self.full_community_lists = "".join([f"ip community-list standard AS{target[0]} permit 1000:{target[0]}\n" for target in connected_AS])
        total_not_client = 0
        self.global_route_map_out = "route-map General-OUT deny 10\n"
        for target in connected_AS:
            if len(target) == 3:
                (as_num, state, list_of_transport) = target
                if state != "client":
                    self.global_route_map_out += f" match community AS{as_num}\n"
                    total_not_client += 1
        self.global_route_map_out += "!\n"
        if total_not_client > 0:
            self.global_route_map_out += "route-map General-OUT permit 20\n!\n"
        else:
            self.global_route_map_out = "route-map General-OUT permit 20\n!\n"
        self.community_data = {}
        self.hashset_pe_routers = set()
        vpn_datas_per_client = {}
        self.vpn_te_route_maps = {}
        for target in connected_AS:
            if len(target) == 4 and not target[3]["am_client"]:
                vpn_datas_per_client[target[3]["client_id"]] = target[3]

        for target in connected_AS:
            if len(target) == 3:
                (as_num, state, list_of_transport) = target
                if state == "peer":
                    self.community_data[as_num] = {
                        "route_map_in":f"route-map Peer-AS{as_num} permit 10\n set local-preference 200\n set community 1000:{as_num}\n!\n",
                        "route_map_in_bgp_name":f"Peer-AS{as_num}",
                        "community_list":f"ip community-list standard AS{as_num} permit 1000:{as_num}\n"
                    }
                elif state == "provider":
                    self.community_data[as_num] = {
                        "route_map_in":f"route-map Provider-AS{as_num} permit 10\n set local-preference 100\n set community 1000:{as_num}\n!\n",
                        "route_map_in_bgp_name":f"Provider-AS{as_num}",
                        "community_list":f"ip community-list standard AS{as_num} permit 1000:{as_num}\n"
                    }
                else:
                    self.community_data[as_num] = {
                        "route_map_in":f"route-map Client-AS{as_num} permit 10\n set local-preference 300\n set community 1000:{as_num}\n!\n",
                        "route_map_in_bgp_name":f"Client-AS{as_num}",
                        "community_list":f"ip community-list standard AS{as_num} permit 1000:{as_num}\n"
                    }
            else:
                (as_num, state, list_of_transport, vpn_data) = target
                am_client = vpn_data["am_client"]
                client_id = vpn_data["client_id"]
                if am_client:
                    self.community_data[as_num] = {
                        "VPN":True,
                        "vpn_route_map":f"route-map VPN-AS{as_num} permit 10\n set local-preference 400\n set community 1000:{as_num}\n!\n",
                        "vpn_route_map_name":f"VPN-AS{as_num}",
                        "am_client":am_client
                    }
                else:
                    imports = ""
                    for (my_router, their_router) in vpn_data.get("preferred_links", []):
                        self.allocated_vpn_communities += 1
                        allocated = self.allocated_vpn_communities
                        self.vpn_te_route_maps[(my_router, their_router)] = {
                            "community_list":f"ip community-list standard VPN{client_id}-P{allocated} permit 200:{allocated}\n",
                            "route_map_pe_in":f"route-map VPN{client_id}-P{allocated}-RM permit 10\n set local-preference 400\n match community VPN{client_id}-P{allocated}\n!\n",
                            "RM_name":f"VPN{client_id}-P{allocated}-RM"
                        }
                        
                        self.vpn_te_route_maps[(their_router, my_router)] = {
                            "route_map_ce_out":f"route-map VPN{client_id}-P{allocated}-RM permit 10\n set community 200:{allocated}\n!\n",
                            "RM_name":f"VPN{client_id}-P{allocated}-RM"
                        }

                    for accept in vpn_data["accept_from"]:
                        if vpn_data["client_id"] in vpn_datas_per_client[accept]["share_with"]:
                            imports += f" route-target import 100:{accept}\n"
                    vrf_defs = []
                    for i in range(len(list_of_transport)):
                        vrf_defs.append(f"vrf definition Client_{client_id}\n rd 100:{self.route_distinguishers}\n route-target export 100:{client_id}\n{imports} route-target import 100:{client_id}\n !\n address-family ipv4\n exit-address-family\n!\n")
                        self.route_distinguishers += 1
                    self.community_data[as_num] = {
                        "VPN":True,
                        "am_client":am_client,
                        "nom_vrf":f"Client_{client_id}",
                        "vrf_def":vrf_defs
                    }
            for router in list_of_transport.keys():
                self.hashset_pe_routers.add(router)
        self.connected_AS_dict = {target[0]:(target[1], target[2]) for target in connected_AS}
        self.hashset_routers = set(routers)
        self.loopback_prefix = loopback_prefix
        self.community = f"{self.AS_number}:1000"
        self.global_router_counter = counter
        self.hashet_RRs = set(route_reflectors)
        self.route_reflectors = route_reflectors
        
    
    def __str__(self):
        return f"prefix:{self.ipv4_prefix}\n as_number:{self.AS_number}\n routers:{self.routers}\n internal_routing:{self.internal_routing}\n connected_AS:{self.connected_AS}"
