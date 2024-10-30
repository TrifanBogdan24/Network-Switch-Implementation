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


Retin aceste interfete intr-un **dictionar Python**,
pentru care **cheile** represinta `interfete`,
iar **valorile** = `adrese MAC`.

Fiecare **cheie** (`interfata`) de la 0 la `num_interfaces`,
nu va referi initial la nicio `adresa MAC`.


```python 3
CAM_table = {i: None for i in range(num_interfaces)}
```


Atunci cand primim un pachet se updateaza `Tabela CAM`,
stiind ca `interfata` pe care a venit refera `adresa MAC sursa` a pachetului.



```python 3
CAM_table[interface] = src_mac
```


Pentru a trimite pachetul mai departe, `switch`-ul trebuie sa afle pe ce interfata sa il trimita.
Astfel, va itera peste toate `interfetele` (mai putin cea pe care a venit).
Daca vreo `interfata` refera catre `adresa MAC destinatie` a pachetului,
inseamna ca am gasit `interfata` pe care sa fie trimis pachetul,
si ii dam `send` (de fapt `send_to_link`) pe interfata respectiva.


```python 3
for dst_interface in interfaces:
    if dst_interface == interface:
        continue
    if CAM_table[dst_interface] == dest_mac:
        send_to_link(dst_interface, length, data)
        found_dst_interface = True
        break
```


Daca in schimb, nu am gasit nicio `interfata` care sa asocieze `adresa MAC destinate`,
```python 3
if found_dst_interface == False
```
atunci inseamna ca nu stim pe unde sa trimitem pachetul,
si deci il trimitem pe toate interfetele, mai putin cea pe care a venit (logic).


```python 3
# Broadcast
if found_dst_interface == False:
    for dst_interface in interfaces:
        if dst_interface == interface:
            continue
        send_to_link(dst_interface, length, data)
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
- O lista de interfete (numele si tipul `trunk`/`access`)


```python
class SwitchConfig:
    def __init__(self, switch_id: int, switch_priority: int, interfaces: List[SwitchInterface]):
        self.switch_id = switch_id
        self.switch_priority = switch_priority
        self.interfaces = interfaces
```


Fisierul de configuratie al switch-ului
contine pe prima linie un numar, reprezentand `switch_id`-ul,
iar mai apoi, pe toate celelalte:
numele interfetei switch-ului (e.g. "r-1" sau "rr-0-1")
si litera "T" (insemnand ca interfata este configurata a fi o linie `trunk`)
sau un numar (insemnand o linie de `access`, avand `VLAN ID`-ul egal cu numarul respectiv).




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


Aceasta logica se implementeaza, facand **pattern matching** intre tipurile porturilor (`trunk / access`).

> Vedem astfel tipul unei interfete ca fiind o enumerare
> (in python - `Union`) intre porturile de tip `Trunk`
> si cele `Access`, cele din urma retinand valoarea `VLAN ID`-ului aferent.


```python
src_port_type: Union[Trunk, Access] = network_switch.getInterfaceByName(src_name)
    dst_port_type: Union[Trunk, Access] = network_switch.getInterfaceByName(dst_name)

if isinstance(src_port_type, Access) and isinstance(dst_port_type, Access):
    if src_port_type.vlan_id != dst_port_type.vlan_id:
        # Nu trimitem intre VLAN-uri diferite
        return
    send_to_link(dst_interface, length, data)
    return
if isinstance(src_port_type, Trunk) and isinstance(dst_port_type, Trunk):
    send_to_link(dst_interface, length, data)
    return
if isinstance(src_port_type, Access) and isinstance(dst_port_type, Trunk):
    new_data = data[0:12] + create_vlan_tag(int(src_port_type.vlan_id)) + data[12:]
    new_length = length + 4       # The size of VLAN TAG is 4 bits
    send_to_link(dst_interface, new_length, new_data)
    return
if isinstance(src_port_type, Trunk) and isinstance(dst_port_type, Access):
    if int(dst_port_type.vlan_id) != int(vlan_id_packet):
        # Nu facem transmisia intre doua VLAN-uri diferite
        return
    new_data = data[0:12] + data[16:]
    new_length = length - 4       # Removing 4 bits (size of VLAN)
    send_to_link(dst_interface, new_length, new_data)
    return
```