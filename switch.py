#!/usr/bin/python3
import sys
import struct
import wrapper
import threading
import time
from wrapper import recv_from_any_link, send_to_link, get_switch_mac, get_interface_name

from typing import List, Dict, Union


# MyTODO
class Trunk:
    def __init__(self):
        self.isTrunk: bool = True
    
    def __str__(self):
        return "Port Type: TRUNK"

# MyTODO
class Access:
    def __init__(self, vlan_id: int):
        self.vlan_id: int = vlan_id

    def __str__(self):
        return f"Port Type: ACCESS (vlan_id={self.vlan_id})"




class BlockingPort:
    def __init__(self):
        self.isBlocked: bool = True


class ListeningPort:
    def __init__(self):
        self.isListening: bool = True


class DesignatedPort:
    def __init__(self):
        self.isDesignated: bool = True


class RootPort:
    def __init__(self):
        self.isRootPort: bool = True


PortState = Union[BlockingPort, ListeningPort, DesignatedPort, RootPort]


class SwitchPort:
    def __init__(self, port_id: int, port_name: str, vlan_type: Union[Trunk, Access]):
        self.port_id = port_id
        self.port_name = port_name

        self.vlan_type = vlan_type

        # La initializare, toate porturile sunt in starea LISTENING
        self.port_state: PortState = ListeningPort()

    def __str__(self):
        string = "{\n"
        
        if isinstance(self.vlan_type, Access):
            string += f"\tVLAN type: ACCESS {self.vlan_type.vlan_id},\n"
        elif isinstance(self.vlan_type, Trunk):
            string += f"\tVLAN type: TRUNK,\n"
        
        if isinstance(self.port_state, BlockingPort()):
            string += f"\tPort state: Blcoking,\n"
        elif isinstance(self.port_state, ListeningPort()):
            string += f"\tPort state: Listening,\n"
        
        if self.is_designated_port == True:
            string += "\tDesignated port: True\n"
        else:
            string += "\tDesignated port: False\n"

        string += "}\n"
        return string


# MyTODO
class SwitchConfig:
    def __init__(self, switch_id: int, switch_priority: int, interfaces: List[SwitchPort] = None):
        """
        Configuratia switch-ului.
        """
        self.switch_id = switch_id
        self.switch_priority = switch_priority
        self.interfaces = interfaces or {}

        # Variabile pentru STP (setate la valorile implicite la crearea switch-ului)
        self.own_bridge_id = switch_priority
        self.root_bridge_id = self.own_bridge_id
        self.root_path_cost = 0
        self.root_port = None
        # La initializare, switch-ul este ROOT BRIDGE
        self.is_root_bridge: bool = True

    def __str__(self):
        """
        Returns a JSON formatted string
        """
        string = ""
        string += "{\n"
        string += f"\t\"SwitchID\": {self.switch_id},\n"
        string += f"\t\"Switch Priority\": {self.switch_priority},\n"

        if len(self.interfaces) == 0:
            string += "\t\"Switch Interfaces\": []\n"
            return string

        string += "\t\"Switch Interfaces\":\n"
        string += "\t[\n"

        iter = 0

        # Iterating all KEYS (interface names) and VALUES (interface values "T"/number)
        for port in self.interfaces:
            string += "\t\t{\n"
            string += f"\t\t\tPort name: {port.port_name},\n"
            string += f"\t\t\tPort ID: {port.port_id},\n"

            if isinstance(port.vlan_type, Trunk):
                string += f"\t\t\tVLAN Type: TRUNK,\n"
            elif isinstance(port.vlan_type, Access):
                string += f"\t\t\tVLAN Type: ACCESS (vlan_id={port.vlan_type.vlan_id})\n,"


            iter = iter + 1
            string += "\t\t},\n" if iter != len(self.interfaces) else "\t\t}\n"

        string += "\t]\n"
        string += "}\n"
        return string
    
    def getInterfaceByName(self, name: str) -> SwitchPort:
        for port in self.interfaces:
            if name == port.port_name:
                return port
        return None
    

    def getAllTrunkPorts(self, ports) -> List[SwitchPort]:
        all_trunk_ports = []
        

        for port in self.interfaces:
            if isinstance(port.vlan_type, Trunk):
                all_trunk_ports.append(port)


        return all_trunk_ports


# MyTODO
def read_config_file(switch_id: int, filepath: str) -> SwitchConfig:
    try:
        with open(filepath, 'r') as file:
            switch_priority = int(file.readline().strip())
            interfaces: List[SwitchPort] = []

            global map_interface_names_with_ids

            for line in file:
                line_parts = line.strip().split()
                interface_name: str = line_parts[0]
                interface_id: int = map_interface_names_with_ids[interface_name]
                
                if line_parts[1] == "T":
                    interfaces.append(SwitchPort(interface_id, interface_name, Trunk()))
                else:
                    vlan_id = int(line_parts[1])
                    interfaces.append(SwitchPort(interface_id, interface_name, Access(vlan_id)))
            
            return SwitchConfig(switch_id, switch_priority, interfaces)
    except Exception as err:
        print(f"[ERROR] Eroare la citirea fisierului {filepath}: {err}")
        return None  





def parse_ethernet_header(data):
    # Unpack the header fields from the byte array
    #dest_mac, src_mac, ethertype = struct.unpack('!6s6sH', data[:14])
    dest_mac = data[0:6]
    src_mac = data[6:12]
    
    # Extract ethertype. Under 802.1Q, this may be the bytes from the VLAN TAG
    ether_type = (data[12] << 8) + data[13]

    vlan_id = -1
    # Check for VLAN tag (0x8100 in network byte order is b'\x81\x00')
    if ether_type == 0x8200:
        vlan_tci = int.from_bytes(data[14:16], byteorder='big')
        vlan_id = vlan_tci & 0x0FFF  # extract the 12-bit VLAN ID
        ether_type = (data[16] << 8) + data[17]

    return dest_mac, src_mac, ether_type, vlan_id

def create_vlan_tag(vlan_id):
    # 0x8100 for the Ethertype for 802.1Q
    # vlan_id & 0x0FFF ensures that only the last 12 bits are used
    return struct.pack('!H', 0x8200) + struct.pack('!H', vlan_id & 0x0FFF)



# MyTODO
def is_unicast(mac) -> bool:
    """
    Functia primeste o adresa MAC si returneaza daca este adresa UNICAST sau nu.

    Adresele MAC sunt compuse din 48 de biti

    O adresa MAC este considerata UNICAST
    daca si numai daca primul bit din primul octet este setat la 0
    """
    return (mac[0] & 1) == 0


def mac_addr_to_string(mac) -> str:
    """
    Converteste o adresa MAC (primita sub forma de bytes) la un string human-readable
    """
    formatted_mac = ":".join(f"{byte:02x}" for byte in mac)
    return formatted_mac
    


def is_bpdu(dest_mac) -> bool:
    """
    Functia primeste o adresa MAC (adresa MAC destinatie a pachetului)
    si returneaza daca este adresa de BPDU sau nu

    Cadrele BPDU sunt identificate prin adresa multicast MAC destinatie,
    01:80:C2:00:00:00

    Adresa MAC este primita sub forma de bytes
    """
    return mac_addr_to_string(dest_mac) == "01:80:c2:00:00:00"



# MyTODO
def enable_VLAN_sending(vlan_id_packet, src_interface, dst_interface, length, data) -> None:
    """
    Function 'wrapped' on send_to_link
    Additional logic for VLAN tag   -> Implements VLAN support
    """

    global network_switch

    if network_switch is None:
        # Switch is not in the list of switches
        send_to_link(dst_interface, length, data)
        return
    


    src_name: str = get_interface_name(src_interface)
    dst_name: str = get_interface_name(dst_interface)

    src_port_type: Union[Trunk, Access] = network_switch.getInterfaceByName(src_name).vlan_type
    dst_port_type: Union[Trunk, Access] = network_switch.getInterfaceByName(dst_name).vlan_type


    if isinstance(src_port_type, Access) and isinstance(dst_port_type, Access):
        # Access -> Trunk
        if src_port_type.vlan_id != dst_port_type.vlan_id:
            # Nu trimitem intre VLAN-uri diferite
            return
        send_to_link(dst_interface, length, data)
        return
    if isinstance(src_port_type, Trunk) and isinstance(dst_port_type, Trunk):
        # Trunk -> Trunk
        send_to_link(dst_interface, length, data)
        return
    if isinstance(src_port_type, Access) and isinstance(dst_port_type, Trunk):
        # Access -> Trunk
        new_data = data[0:12] + create_vlan_tag(src_port_type.vlan_id) + data[12:]
        new_length = length + 4       # The size of VLAN TAG is 4 bits
        send_to_link(dst_interface, new_length, new_data)
        return
    if isinstance(src_port_type, Trunk) and isinstance(dst_port_type, Access):
        # Trunk -> Access
        if dst_port_type.vlan_id != int(vlan_id_packet):
            # Nu facem transmisia intre doua VLAN-uri diferite
            return
        new_data = data[0:12] + data[16:]
        new_length = length - 4       # Removing 4 bits (size of VLAN)
        send_to_link(dst_interface, new_length, new_data)
        return
    
    
    send_to_link(dst_interface, length, data)
    return
    



def initialize_STP():
    global network_switch
    global all_trunk_ports

    for trunk_port in all_trunk_ports:
        # Set port state to BLOCKING
        trunk_port.port_state = BlockingPort()


    network_switch.own_bridge_id = network_switch.switch_priority
    network_switch.root_bridge_id = network_switch.own_bridge_id
    network_switch.root_path_cost = 0

    if network_switch.own_bridge_id == network_switch.root_bridge_id:
        for trunk_port in all_trunk_ports:
            trunk_port.port_state = DesignatedPort()



def send_bdpu_to_link(trunk_port: SwitchPort, root_bridge_id, sender_bridge_id, sender_path_cost) -> None:
    # destination MAC

    print("Pachetul BDPU va contine:")
    print("{")
    print(f"\tInterface: {trunk_port.port_id},")
    print(f"\tRoot Bridge ID: {root_bridge_id},")
    print(f"\tSender bridge ID: {sender_bridge_id},")
    print(f"\tSender Path Cost: {sender_path_cost}")
    print("}")

    dest = "01:80:c2:00:00:00"
    dst = bytes.fromhex(dest.replace(":", ""))
    # source MAC is switch MAC
    src = get_switch_mac()            
    # packet length
    bpdu_length = 44
    llc_length = bpdu_length.to_bytes(2, byteorder='big')
    dsap = 0x42
    ssap = 0x42
    control = 0x03
    llc_header = dsap.to_bytes(1, byteorder='big') + ssap.to_bytes(1, byteorder='big') + control.to_bytes(1, byteorder='big')
    # bpdu header length
    bpdu_header = 23
    bpdu_header = bpdu_header.to_bytes(4, byteorder='big')
    # uint8_t root_bridge_id[8]
    root_bridge_bytes = root_bridge_id.to_bytes(8, byteorder='big')
    # uint32_t root_path_cost
    root_path_bytes = sender_path_cost.to_bytes(4, byteorder='big')
    # uint8_t bridge_id[8]
    sender_bridge_bytes = sender_bridge_id.to_bytes(8, byteorder='big')
    # uint16_t port_id
    port_id = trunk_port.port_id.to_bytes(2, byteorder='big')

    # get data to send
    bpdu_data = dst + src + llc_length + llc_header + bpdu_header + bytes([0]) + root_bridge_bytes + root_path_bytes + sender_bridge_bytes + port_id
    # send acket to trunk port
    send_to_link(trunk_port.port_id, len(bpdu_data), bpdu_data)

def send_bdpu_every_sec():
    global network_switch
    global all_trunk_ports

    while True:
        # TODO Send BDPU every second if necessary
        
        if network_switch.is_root_bridge == True:
            for trunk_port in all_trunk_ports:
                root_bridge_id = network_switch.own_bridge_id
                sender_bridge_id = network_switch.own_bridge_id
                sender_path_cost = 0
                
                send_bdpu_to_link(trunk_port, root_bridge_id, sender_bridge_id, sender_path_cost)
        


        time.sleep(1)


def on_receiving_bpdu(src_interface, data):
    global network_switch
    global all_trunk_ports


    src_switch_port: SwitchPort = network_switch.getInterfaceByName(get_interface_name(src_interface))

    bdpu_root_bridge_id: int = int(data[22:30])
    bdpu_sender_path_cost: int = int(data[30:34])


    if bdpu_root_bridge_id < network_switch.root_bridge_id:
        network_switch.root_bridge_id = bdpu_root_bridge_id
        network_switch.root_path_cost = bdpu_sender_path_cost + 10
        src_switch_port.port_state = RootPort() # Root Port-l este port-ul de unde BPDU-ul a fost primit
        root_port: SwitchPort = src_switch_port

        # if we were the root bridge
        if network_switch.is_root_bridge == True:
            # set all interfaces not to hosts to blocking except the root port 
            for trunk_port in all_trunk_ports:
                if not isinstance(trunk_port, RootPort):
                    trunk_port.port_state = BlockingPort()

        # Acum nu mai suntem root bridge
        network_switch.is_root_bridge = False

        if isinstance(root_port.port_state, BlockingPort()):
            root_port = ListeningPort()

        # Update and forward this BPDU to all other trunk ports with:
        #  sender_bridge_ID = own_bridge_ID
        #  sender_path_cost = root_path_cost

        for trunk_port in all_trunk_ports:
            if isinstance(trunk_port, RootPort()):
                continue
            root_bridge_id = network_switch.own_bridge_id
            sender_bridge_id = network_switch.own_bridge_id
            sender_path_cost = network_switch.root_path_cost
            send_bdpu_to_link(trunk_port, root_bridge_id, sender_bridge_id, sender_path_cost)

    elif bdpu_root_bridge_id == network_switch.root_bridge_id:
        if isinstance(src_switch_port.port_state, RootPort()) and bdpu_sender_path_cost + 10 < network_switch.root_path_cost:
            network_switch.root_path_cost = bdpu_sender_path_cost + 10
        elif not isinstance(src_switch_port.port_state, RootPort()):
            if bdpu_sender_path_cost > network_switch.root_path_cost:
                if not isinstance(src_switch_port.port_state, DesignatedPort()):
                    src_switch_port.port_state = DesignatedPort()

    else:
        pass

    if network_switch.own_bridge_id == network_switch.root_bridge_id:
        for trunk_port in all_trunk_ports:
            trunk_port.port_state = DesignatedPort()

network_switch: SwitchConfig = None
all_trunk_ports: List[SwitchPort] = []
map_interface_names_with_ids: Dict[str, int] = {}


def main():
    # init returns the max interface number. Our interfaces
    # are 0, 1, 2, ..., init_ret value + 1
    switch_id = sys.argv[1]

    # MyTODO cast to int
    switch_id: int = int(switch_id)


    num_interfaces = wrapper.init(sys.argv[2:])
    interfaces = range(0, num_interfaces)

    # MyTODO
    global map_interface_names_with_ids
    for port in interfaces:
        map_interface_names_with_ids[get_interface_name(port)] = int(port)
    

    # MyTODO init the CAM table
    CAM_table_dict = dict()     # Empty dictionary

    # MyTODO
    global network_switch
    network_switch = read_config_file(switch_id, f"configs/switch{switch_id}.cfg")

    # MyTODO
    global all_trunk_ports
    all_trunk_ports = network_switch.getAllTrunkPorts(interfaces)




    # MyTODO
    initialize_STP()


    # Create and start a new thread that deals with sending BDPU
    t = threading.Thread(target=send_bdpu_every_sec)
    t.start()



    while True:
        # Note that data is of type bytes([...]).
        # b1 = bytes([72, 101, 108, 108, 111])  # "Hello"
        # b2 = bytes([32, 87, 111, 114, 108, 100])  # " World"
        # b3 = b1[0:2] + b[3:4].
        interface, data, length = recv_from_any_link()

        dest_mac, src_mac, ethertype, vlan_id = parse_ethernet_header(data)


        # Note. Adding a VLAN tag can be as easy as
        # tagged_frame = data[0:12] + create_vlan_tag(10) + data[12:]


        # TODO: Implement forwarding with learning

        # MyTODO updatez interfata pe care a venit pachetul cu adresa MAC sursa a pachetului
        CAM_table_dict[src_mac] = interface
        
        src_interface = interface
            



        # MyTODO trimiterea cadrului
        if is_unicast(dest_mac):
            # MyTODO Unicast

            if dest_mac in CAM_table_dict:
                dst_interface = CAM_table_dict[dest_mac]

                if dst_interface == src_interface:
                    continue
                enable_VLAN_sending(vlan_id, src_interface, dst_interface, length, data)

            else:
                # MyTODO Broadcast
                for dst_interface in interfaces:
                    if dst_interface == src_interface:
                        continue
                    enable_VLAN_sending(vlan_id, src_interface, dst_interface, length, data)
        else:
            if is_bpdu(dest_mac):
                on_receiving_bpdu(src_interface, data)
                continue
            
            # MyTODO Broadcast
            for dst_interface in interfaces:
                if dst_interface == src_interface:
                    continue
                enable_VLAN_sending(vlan_id, src_interface, dst_interface, length, data)





        # TODO: Implement VLAN support
        # TODO: Implement STP support

        # data is of type bytes.
        # send_to_link(i, length, data)

if __name__ == "__main__":
    main()
