How to connect pi with Laptop Ubuntu

*Ubuntu terminal already contain ssh so don’t need to download PuTTY.

*Download VNC if need GUI

0. Plug in LAN cable to Pi5 and Laptop


1. On Pi5 run “nmcli device status”
   
expected output:

DEVICE     TYPE        STATE         CONNECTION

eth0     ethernet     connected   Wired connection 1
   
wlan0      wifi       connected    your_wifi_name


2. Set static IP for Pi 5 (Bookworm method)

         sudo nmcli connection show

   usually "Wired connection 1"
 
 Assign ip to Pi5
 
        sudo nmcli connection modify "Wired connection 1" ipv4.addresses 192.168.0.2/24 ipv4.gateway 192.168.0.1 ipv4.method manual autoconnect yes

        sudo nmcli connection up "Wired connection 1"

Checking: ip addr show eth0. Exp output: inet 192.168.0.2/24.


3. On laptop Ubuntu

   Set laptop’s Ethernet to 192.168.0.1/24 (GUI or nmcli):

        sudo nmcli connection modify "Wired connection 1" ipv4.addresses 192.168.0.1/24 ipv4.method manual autoconnect yes

        sudo nmcli connection up "Wired connection 1"
   

5. Test link

           ping 192.168.0.2

   Exp output:
    
   PING 192.168.0.2 (192.168.0.2) 56(84) bytes of data.

   64 bytes from 192.168.0.2: icmp_seq=1 ttl=64 time=0.146 ms
   
   64 bytes from 192.168.0.2: icmp_seq=2 ttl=64 time=0.125 ms
   
   64 bytes from 192.168.0.2: icmp_seq=3 ttl=64 time=0.129 ms
   
   
Connect to pi5

        ssh tridentcontrol@192.168.0.2
        
fill pi’s password
        
Prompt name change to tridentcontrol → finish
