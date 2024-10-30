Cerintele rezolvate: 1, 2


## Links

Enuntul temei: <https://ocw.cs.pub.ro/courses/rl/teme/tema1_sw>

Schelet + infrastructura de testare: <https://gitlab.cs.pub.ro/rl/tema1-public>


## Running

```bash
sudo python3 checker/topo.py
```

This will open 9 terminals, 6 hosts and 3 for the switches. On the switch terminal you will run 

```bash
make run_switch SWITCH_ID=X # X is 0,1 or 2
```

The hosts have the following IP addresses.
```
host0 192.168.1.1
host1 192.168.1.2
host2 192.168.1.3
host3 192.168.1.4
host4 192.168.1.5
host5 192.168.1.6
```

We will be testing using the ICMP. For example, from host0 we will run:

```
ping 192.168.1.2
```

Note: We will use wireshark for debugging. From any terminal you can run `wireshark&`.




## Rezolvare

### Procesul de comutare | Tabela `CAM`
---


In bucla infinita `while True` din `main`, ma folosesc de trei variabile:

- `interface` -> interfata (portul, cablul fizic) pe care pachetul a veni
- `src_mac` -> adresa MAC sursa a pachetului
- `dest_mac` -> adresa MAC destinatie a pachetului


Tabela `CAM` (Content-addressable memory) retine `asocieri` (`mapari`)
intre `interfete` si `adresa MAC`.

O `interfata` poate avea asociata la un moment de timp,
o `adresa MAC` sau niciuna.


Atat `interfetele`, cat si `adresele MAC` sunt unice in tabela `CAM`. 


Aceste asocieri le retin intr-un **dictionar Python**,
iar ordinea in care sunt mapate influenteaza complexitatea in timp a executiei programului.

De vreme ce cunosc `adresa MAC sursa` si `adresa MAC destinatie` a pachetului pe care il primesc,
este de inteles ca voi accesa tabela `CAM` in functie de aceste valori.

> Tabela CAM: { MAC -> interfata }


Astfel, incep printr-un dictionar vid (la inceput nu stim nimic despre maparile dintre interfete si adresele MAC):
```python
CAM_table_dict = dict()     # Empty dictionary
```


Apoi, pe parcurs ce primesc pachetele, updatez tabela CAM,
modificand valoarea cheii `adresa MAC sursa` cu interfata pe care a venit.

```python
CAM_table_dict[src_mac] = interface
```

> La primire are loc procesul de invatare.
>
> Switch-ul face asocierile efective intre `adrese MAC` si `port`-uri
> doar atunci cand primeste.


In cazul in care `adresa MAC destinatie` nu se afla in **dictionarul** tabelei CAM,
inseamna ca nu stiu pe ce port sa trimit (`adresa MAC destinatie` nu are mapata o `interfata`),
deci fac **broadcast**, trimitand pe toate port-urile, mai putin cel pe care a venit.

Daca in schimb `adresa MAC destinatie` se gaseste in **dictionar**,
atunci spun despre ea ca geseste in tabela CAM a switch-ului.
Drep pentru care stiu exact pe ce port sa trimit (fac **unicast**):
pe portul mapat in dictionar la `adresa MAC destinatie`.


> La trimitere switch-ul nu invata nimic.
>
> Doar se foloseste de tabela CAM (informatiile pe care le stie deja)
> pentru a decide unde sa trimita.


```python
# Trimiterea cadrului
if dest_mac in CAM_table_dict:
    # Unicast
    dst_interface = CAM_table_dict[dest_mac]

    if dst_interface == src_interface:
        continue
    enable_VLAN_sending(network_switch, vlan_id, src_interface, dst_interface, length, data)

else:
    # Broadcast
    for dst_interface in interfaces:
        if dst_interface == src_interface:
            continue
        enable_VLAN_sending(network_switch, vlan_id, src_interface, dst_interface, length, data)
```





### `VLAN` (Virtual LAN)
---


`VLAN`-ul este construit deasupra algoritmului `tabelei CAM`.

Spunem despre interfata pe care pachetul a venit pachetul este `src_interface` (interfata sursa).


Spunem despre interfata/interfetele pe care ajunge pachetul sa fie trimis mai departa ca este/sunt `dst_interface` (interfata destinatie).

Voi incepe prin a citi fisierul de configuratie al switch-ului.
Id-ul switch-ului, obtinut ca argument in linia de comanda, `switch_id = sys.argv[1]`
il voi folosi pentru a sti exact ce fisier sa citesc.

```python
switch_id = sys.argv[1]
network_switch: SwitchConfig = read_config_file(switch_id, f"configs/switch{switch_id}.cfg")
```


Fisierul de configuratie este ulterior parsat intr-o structura de date,
reprezentata de clasa `SwitchConfig`
care va contine urmatoarele informatii:
- ID-ul switch-ului
- Prioritatea switch-ului
- Interfetele switch-ului (retinute drept **asocieri** intre numele interfetei si tipul interfetei)


```python
class SwitchConfig:
    def __init__(self, switch_id: int, switch_priority: int, interfaces: Dict[str, PortType]):
        """
        interfaces = { interface_name -> interface_type }
        e.g. interfaces = { "r-1" -> "1", "rr-0-1" -> "T" }
        """
        self.switch_id = switch_id
        self.switch_priority = switch_priority
        self.interfaces = interfaces
```


Am optat pentru implementarea interfetelor citite din fisierul de configuratie
sub forma unui **dictionar**,
pentru a putea obtine mai usor (si mai eficient cred) tipul unei interfete in functie de nume:


```python
class SwitchConfig:
    ...
    def getInterfaceTypeByName(self, name: str) -> str:
        if name in self.interfaces:
            return self.interfaces[name]
        # The KEY (interface name) is not in dictionary
        return None
```

> Fiind un **dictionar**,
> verificarea existentei unei chei si obtinerea valorii aferente
> ar trebui sa ruleze in `O(1)`.



Fisierul de configuratie al switch-ului
contine pe prima linie un numar, reprezentand `switch_id`-ul,
iar mai apoi, pe toate celelalte:
numele interfetei switch-ului (e.g. "r-1" sau "rr-0-1")
si litera "T" (insemnand ca interfata este configurata a fi o linie `trunk`)
sau un numar (insemnand o linie de `access`, avand `VLAN ID`-ul egal cu numarul respectiv).



Pentru a face o mai buna separatia in cod intre `trunk` si `access`
(nu e o idee tocmai buna sa compar un string cu *"T"* pentru a decide daca este `trunk` sau nu),
am creat doua clase aditionale, una pentru `trunk` si `access`,
pe care l-am unit intr-un nou tip de date, numit `PortType`.


```python

from typing import Dict, Union


class Trunk:
    def __init__(self):
        self.isTrunk: bool = True
    
    def __str__(self):
        return "Port Type: TRUNK"

class Access:
    def __init__(self, vlan_id: int):
        self.vlan_id: int = vlan_id

    def __str__(self):
        return f"Port Type: ACCESS (vlan_id={self.vlan_id})"


PortType = Union[Trunk, Access]
```


> Astfel, folosind `isinstance` pe obiecte de tip `PortType`,
> pot face usor (un fel de) **pattern matching** pe tipurile de port-uri.
>
> In plus, codul devine mai usor de urmarit (cel putin pentru mine).




In timpul procesului de invatare (`tabela CAM`),
in loc sa trimit direct pachetul,
apelez o functie construita peste `send_to_link`, care,
in functie de tipul porturilor sursa si destinatie (`trunk` / `access`),
trimite sau nu pachetul, cu sau fara **TAG** de VLAN.


`VLAN`-ul introduce astfel 4 cazuri:

- 1\. Portul pe care pachetul a venit este de tip `access`, iar portul destinatie este `access`:
trimit pachetul **daca si numai daca** porturile au acelasi `VLAN ID`
(altfel nu trimit nimic)

- 2\. Portul sursa este `trunk` si portul destinatie este `trunk`:
trimit pachetul asa cum a venit

- 3\. Portul sursa este `access`, iar portul destinatie este `trunk`:
adaug **TAG**-ul de `VLAN` in pachet,
avand `VLAN ID`-ul egal cu cel al interfetei sursa,
si trimit pachetul.


4\. Portul sursa este `trunk`, iar portul destinatie este `access`,
trimit pachetul **daca si numai daca**
`VLAN ID`-ul din pachet coincide cu `VLAN ID`-ului portului destinatie,
caz in care elimin **TAG**-ul de `VLAN` din pachet inainte sa trimit
(altfel, daca `VLAN ID`-urile sunt diferite, pachetul se va pierde)


Aceasta logica se implementeaza, facand un fel de **pattern matching**
intre tipurile (`trunk / access`) porturilor sursa si destinatie.




```python
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
```

