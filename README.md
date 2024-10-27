Scheleton for the Hub implementation.


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
for port in interfaces:
    if port == interface:
        continue
    if CAM_table[port] == dest_mac:
        send_to_link(port, length, data)
        is_dst_interface = True
        break
```


Daca in schimb, nu am gasit nicio `interfata` care sa asocieze `adresa MAC destinate`,
```python 3
if is_dst_interface == False
```
atunci inseamna ca nu stim pe unde sa trimitem pachetul,
si deci il trimitem pe toate interfetele, mai putin cea pe care a venit (logic).


```python 3
# Broadcast
if is_dst_interface == False:
    for port in interfaces:
        if port == interface:
            continue
        send_to_link(port, length, data)
```


