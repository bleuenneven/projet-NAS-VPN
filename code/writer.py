from router import Router
from autonomous_system import AS

LINKS_STANDARD = ["GigabitEthernet1/0","GigabitEthernet2/0","GigabitEthernet3/0","GigabitEthernet4/0","GigabitEthernet5/0","GigabitEthernet6/0"]
NOM_PROCESSUS_OSPF_PAR_DEFAUT = "1984"
IPV6_UNICAST_STRING = """no ip domain lookup
ipv6 unicast-routing
ipv6 cef
"""
LOCAL_PREF_ROUTE_MAPS ="""
route-map tag_pref_provider permit 10
 set local-preference 100
route-map tag_pref_peer permit 10
 set local-preference 200
route-map tag_pref_customer permit 10
 set local-preference 300
"""

def get_ospf_config_string(AS, router):
    ospf_config_string = f"ipv6 router ospf {NOM_PROCESSUS_OSPF_PAR_DEFAUT}\n"
    ospf_config_string += f" router-id {router.router_id}\n"
    for passive in router.passive_interfaces:
        ospf_config_string += f"passive-interface {passive}\n"
    return ospf_config_string

def get_rip_config_string(AS, router):
    rip_config_string = f"ipv6 router rip {NOM_PROCESSUS_OSPF_PAR_DEFAUT}\n"
    for passive in router.passive_interfaces:
        rip_config_string += f"passive-interface {passive}\n"
    return rip_config_string

def get_final_config_string(AS:AS, router:Router):
    if AS.internal_routing == "OSPF":
        internal_routing = get_ospf_config_string(AS, router)
    else:
        internal_routing = get_rip_config_string(AS, router)
    total_interface_string = ""
    for (link, config_string) in router.config_str_per_link:
        total_interface_string += config_string
    config = f"""!

!
! Last configuration change at 16:10:58 UTC Wed Dec 11 2024
!
version 15.2
service timestamps debug datetime msec
service timestamps log datetime msec
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
!
no ip domain lookup
ipv6 unicast-routing
ipv6 cef
!
!
multilink bundle-name authenticated
!
!
!
!
!
!
!
!
!
ip tcp synwait-time 5
! 
!
!
!
!
!
!
!
!
!
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
!

{internal_routing}
!
{LOCAL_PREF_ROUTE_MAPS}
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
    return config