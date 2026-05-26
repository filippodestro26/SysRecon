# 🔍 SysRecon — Strumento Didattico di Cybersecurity

> ⚠️ **SOLO PER USO DIDATTICO** — Questo strumento è stato creato esclusivamente per studiare le tecniche di reconnaissance e post-exploitation in ambienti controllati (es. macchine virtuali). L'uso su sistemi senza autorizzazione esplicita è **illegale** e perseguibile penalmente.

---

## 📌 Descrizione del progetto

**SysRecon** è uno strumento Python che raccoglie automaticamente informazioni dettagliate su un sistema Windows, sviluppato a scopo didattico per lo studio della cybersecurity. Include anche un keylogger che registra i tasti premuti indicando la finestra attiva.

L'obiettivo è capire cosa un attaccante potrebbe raccogliere nella fase di **reconnaissance** (ricognizione) e **post-exploitation** (dopo aver compromesso un sistema), in modo da imparare a difendersi.

---

## 📋 Cosa raccoglie

### 🌐 Rete
| Sezione | Descrizione |
|---|---|
| IP | IP locale, maschera, gateway, IP pubblico |
| DNS | Server DNS configurati |
| Wi-Fi | SSID, protocollo (WPA2/WPA3), segnale |
| Routing | Tabella di routing completa |
| Interfacce | Tutte le interfacce di rete con stato |
| ARP | Dispositivi nella rete locale con nome |
| Connessioni | Connessioni attive (ESTABLISHED) con hostname |
| LISTENING | Porte in ascolto |
| Port scan | Scansione porte comuni locali |

### 🔒 Sicurezza
| Sezione | Descrizione |
|---|---|
| Antivirus | Nome e versione |
| Firewall | Stato dei 3 profili (Domain, Private, Public) |
| UAC | Attivo o disattivo |
| Secure Boot | Attivo o disattivo |
| Password policy | Lunghezza minima, scadenza, complessità |
| Certificati | Certificati installati con data scadenza |
| Windows Update | Ultimi 10 aggiornamenti installati |

### 💻 Sistema
| Sezione | Descrizione |
|---|---|
| OS | Nome, versione, release, architettura |
| BIOS/UEFI | Produttore, versione, data |
| GPU | Scheda grafica, driver, VRAM |
| Uptime | Da quando è acceso il sistema |
| Utente | Nome e privilegi (admin o standard) |
| Utenti | Lista di tutti gli utenti del sistema |
| Accessi | Ultimi login con orario |
| Variabili | Variabili d'ambiente (PATH, APPDATA...) |
| CPU | Modello, core fisici e logici |
| RAM | Totale, usata, disponibile |
| Dischi | Spazio per ogni partizione |

### ⚠️ Attività
| Sezione | Descrizione |
|---|---|
| Processi | Tutti i processi attivi con PID e utente |
| Software | Programmi installati con versione |
| Servizi | Servizi Windows in esecuzione |
| Task | Task pianificate (spesso usate da malware) |
| Avvio | Programmi in avvio automatico |
| File recenti | Ultimi 20 file aperti |

### ⌨️ Keylogger
Registra ogni tasto premuto indicando la **finestra attiva** al momento della digitazione:
```
[Finestra: Google Chrome]
password di esempio

[Finestra: Blocco note]
questo è un testo di prova
```

---

## 🛠️ Installazione

### 1. Clona la repository
```bash
git clone https://github.com/tuonome/sysrecon.git
cd sysrecon
```

### 2. Installa le dipendenze
```bash
pip install pynput psutil requests
```

### Dipendenze usate
| Libreria | Scopo |
|---|---|
| `pynput` | Intercettare i tasti premuti |
| `psutil` | RAM, dischi, processi, rete |
| `requests` | Recuperare l'IP pubblico |
| `socket` | IP locale e scansione porte |
| `platform` | Info sul sistema operativo |
| `subprocess` | Eseguire comandi PowerShell |
| `ctypes` | Ottenere la finestra attiva |
| `json` | Parsare l'output di PowerShell |
| `concurrent.futures` | Risoluzione DNS con timeout sicuro |

---

## 🚀 Utilizzo

```bash
python codice_key1.py
```

Le informazioni vengono salvate in `keys.txt` nella stessa cartella dello script.

Per fermare il keylogger: **Ctrl+C**

> **Nota:** alcune sezioni (es. ultimi accessi, Windows Update) richiedono i **privilegi di amministratore** per funzionare correttamente.

---

## 📁 Struttura del file di output

```
========================================
  Scansione: 2026-05-25 20:18:56
========================================
--- IP ---                    <- IP locale, maschera, gateway, IP pubblico
--- DNS ---                   <- server DNS
--- WI-FI ---                 <- SSID e protocollo
--- TABELLA DI ROUTING ---    <- rotte di rete
--- INTERFACCE DI RETE ---    <- tutte le interfacce
--- TABELLA ARP ---           <- dispositivi in rete con nome
--- CONNESSIONI ATTIVE ---    <- chi sta comunicando con chi
--- PORTE IN ASCOLTO ---      <- porte che aspettano connessioni
--- PORTE COMUNI APERTE ---   <- scan porte locali
--- ANTIVIRUS ---             <- nome e versione AV
--- FIREWALL ---              <- stato profili firewall
--- UAC ---                   <- controllo account utente
--- SECURE BOOT ---           <- stato secure boot
--- PASSWORD POLICY ---       <- regole password
--- CERTIFICATI ---           <- certificati installati
--- WINDOWS UPDATE ---        <- ultimi aggiornamenti
--- SISTEMA OPERATIVO ---     <- versione Windows
--- BIOS / UEFI ---           <- info BIOS
--- SCHEDA GRAFICA ---        <- GPU e driver
--- UPTIME ---                <- da quanto è acceso
--- UTENTE CORRENTE ---       <- utente e privilegi
--- UTENTI DEL SISTEMA ---    <- tutti gli utenti
--- ULTIMI ACCESSI ---        <- log login
--- VARIABILI D'AMBIENTE ---  <- PATH, APPDATA ecc.
--- PROCESSORE ---            <- CPU e core
--- RAM ---                   <- memoria
--- DISCHI ---                <- partizioni
--- PROCESSI ---              <- processi attivi
--- SOFTWARE INSTALLATO ---   <- programmi e versioni
--- SERVIZI ATTIVI ---        <- servizi Windows
--- TASK PIANIFICATE ---      <- task scheduler
--- AVVIO AUTOMATICO ---      <- startup programs
--- FILE RECENTI ---          <- ultimi file aperti
--- TASTI PREMUTI ---         <- keylogger output
```

---

## 🧩 Struttura del codice e funzioni

```
codice_key1.py
│
├── esegui_powershell(comando, timeout)
│     Funzione helper che esegue qualsiasi comando PowerShell
│     forzando la codifica UTF-8 per evitare errori con
│     caratteri speciali. Usata da tutte le altre funzioni.
│
├── risolvi_nome_dispositivo(ip)
│     Tenta di risolvere il nome host di un IP tramite DNS.
│     Gestisce automaticamente multicast, broadcast e loopback.
│     Usa concurrent.futures per non bloccare lo script.
│
├── ottieni_finestra_attiva()
│     Usa le API Windows (ctypes) per leggere il titolo
│     della finestra in primo piano in tempo reale.
│
├── gestisci_tasti(tasto)
│     Callback del keylogger: chiamata ad ogni tasto premuto.
│     Scrive il carattere nel log e rileva i cambi di finestra.
│
├── salva_rete(file_)
│     Raccoglie tutti i dati di rete:
│     IP, DNS, Wi-Fi, routing, interfacce, ARP,
│     connessioni attive, porte in ascolto, port scan.
│
├── salva_sicurezza(file_)
│     Raccoglie i dati di sicurezza:
│     antivirus, firewall, UAC, Secure Boot,
│     password policy, certificati, Windows Update.
│
├── salva_sistema(file_)
│     Raccoglie le info di sistema:
│     OS, BIOS, GPU, uptime, utenti, accessi,
│     variabili d'ambiente, CPU, RAM, dischi.
│
├── salva_processi_software(file_)
│     Raccoglie processi e software:
│     processi attivi, software installato, servizi,
│     task pianificate, avvio automatico, file recenti.
│
└── main
      Apre il file di log, chiama tutte le funzioni in ordine
      con try/except separati (così se una crasha le altre
      continuano), poi avvia il keylogger.
```

---

## 🔐 Perché è utile per la cybersecurity?

Capire cosa un malware o un attaccante raccoglie è il primo passo per difendersi. Questo strumento mostra in pratica:

- **Reconnaissance**: raccolta di informazioni sulla rete e sul sistema prima di un attacco
- **Post-exploitation**: cosa si può sapere di un sistema dopo avervi accesso
- **Persistence**: le task pianificate e l'avvio automatico sono i metodi più comuni per mantenere accesso a un sistema
- **Lateral movement**: la tabella ARP e le connessioni attive mostrano altri dispositivi raggiungibili

---

## ⚠️ Note legali

Questo strumento è sviluppato **esclusivamente per scopi didattici** nell'ambito dello studio della cybersecurity su macchine virtuali personali. L'autore non si assume alcuna responsabilità per usi impropri. Usare **solo** su sistemi di propria proprietà o con esplicita autorizzazione scritta del proprietario.

---

## 👤 Autore

**Filippo** — Studente di Cybersecurity
