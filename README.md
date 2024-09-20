# Alertă Cutremur pentru Home Assistant

Aceasta este o integrare Home Assistant care permite recepționarea de alerte de cutremur de la Institutul Național de Cercetare - Dezvoltare pentru Fizica Pământului (INCDFP) prin intermediul Telegram.

## Avertisment
**Această integrare nu este afiliată sau aprobată de Institutul Național de Cercetare - Dezvoltare pentru Fizica Pământului (INCDFP). Utilizați această integrare pe propriul risc și asigurați-vă că aveți surse alternative de alertare în caz de cutremur.**

## Caracteristici

- Monitorizează pentru mesaje tip notificări de cutremur transmise prin Telegram și trimite un eveniment (event) în Home Assistant.
- Suportă autentificarea cu doi factori pentru conturile Telegram.
- Permite selectarea dialogurilor Telegram din care se vor primi notificările.

## Cum să instalați

1. **Descărcare și copiere**

Pentru a instala această integrare, urmați una din cele două metode de instalare:

- Clonați sau descărcați acest repository și copiați directorul `telegram_earthquake_alert` în dosarul custom_components al Home Assistant.
- Folosind HACS, adăugați adresa acestui repository de GitHub în Custom Repositories și căutați apoi după Alerta Cutremur.

Va fi necesară repornirea Home Assistant indiferent de metoda aleasă.

2. **Configurare prin interfața Home Assistant**
    - Accesați Home Assistant și mergeți la `Configurare` -> `Dispozitive și servicii`.
    - Apăsați pe `Adaugă Integrare`, căutați `Alerta Cutremur` și urmați pașii de configurare.

## Configurare

În pașii de configurare:
- Este necesar să furnizați datele de acces la API (`api_id` și `api_hash`) și numărul dvs. de telefon asociat contului Telegram.
- După verificarea telefonului, veți introduce codul de verificare primit prin Telegram (în cazul autentificării cu doi factori).
- Selectați conversațiile de la care doriți să primiți notificările de cutremur.

### API Telegram

Este necesar să aveți credențiale API valabile pentru a utiliza integrarea:
1. Mergeți la [Telegram API](https://my.telegram.org/).
2. Logați-vă în contul dvs.
3. Creați o nouă aplicație pentru a obține `api_id` și `api_hash`.

## Contribuire

Contribuțiile sunt binevenite! Deschideți un `Pull Request` pentru a contribui cu cod sau un tichet în secțiunea `Issues` a repository-ului pentru a raporta o problemă.

## Licență

Acest proiect este licențiat sub licența Apache 2.0. Vedeți fișierul `LICENSE` pentru mai multe detalii.
