# Alertă Cutremur pentru Home Assistant

Aceasta este o integrare Home Assistant care permite recepționarea de alerte de cutremur emise de bot-ul @alertacutremur_bot pe Telegram.

Este necesar Home Assistant 2024.11.0 sau o versiune mai nouă.

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
- După verificarea telefonului, veți introduce codul de verificare primit prin Telegram. Dacă autentificarea în doi pași este activă, vi se va solicita și parola.
- Selectați conversațiile de la care doriți să primiți notificările de cutremur.

### API Telegram

Deoarece roboții de Telegram nu se pot abona la mesajele altor roboți, este necesar ca integrarea să se conecteze la rețeaua Telegram ca utilizator. Drept urmare, este necesar să obțineți un set de credențiale pentru a utiliza integrarea:
1. Mergeți la [Telegram API](https://my.telegram.org/).
2. Logați-vă în contul dvs.
3. Creați o nouă aplicație pentru a obține `api_id` și `api_hash`.

## Utilizare

Începeți prin a vă abona, în aplicația Telegram, la mesajele bot-ului @alertacutremur_bot. Informații despre cum puteți face acest lucru veți găsi pe [pagina aceasta](https://www.infp.ro/index.php?i=tgr). După ce ați efectuat acest pas, configurați integrarea să urmărească conversațiile dorite. Integrarea va monitoriza conversațiile selectate după mesaje care conțin șirul de caractere "magnitudine" (nu contează majusculele). Odată primit un astfel de mesaj, va încerca să extragă valoarea magnitudinii și va trimite un eveniment `telegram_earthquake_alert` împreună cu magnitudinea acestuia. Structura evenimentului arată așa:

```yaml
event_type: telegram_earthquake_alert
data:
  magnitude: "2.1"
  original_text: "Mesajul original primit pe Telegram"
```

Acest eveniment poate fi interceptat folosind o automatizare în felul următor:

```yaml
alias: Cutremur detectat
trigger:
  - platform: event
    event_type: telegram_earthquake_alert
condition: []
action:
  - action: notify.mobile_app_numele_dispozitivului
    data:
      message: "Cutremur detectat. Magnitudine: {{ trigger.event.data.magnitude }}"
      title: "ATENȚIE: CUTREMUR"
mode: single
```

Prima alertă este transmisă imediat. Alertele ulterioare din aceeași conversație sunt filtrate automat până când trec 30 de secunde fără o altă alertă validă, inclusiv în cazul actualizărilor de magnitudine. Fiecare conversație este filtrată separat.

Magnitudinile cu virgulă sunt normalizate cu punct (de exemplu, `3,7` devine `"3.7"`). Câmpul `original_text` păstrează mesajul Telegram nemodificat.

Pentru a testa integrarea, puteți folosi un așa-numit Echo Bot din cei disponibili în rețeaua Telegram. Nu uitați să configurați integrarea pentru a monitoriza conversația cu bot-ul.

## Contribuire

Contribuțiile sunt binevenite! Deschideți un `Pull Request` pentru a contribui cu cod sau un tichet în secțiunea `Issues` a repository-ului pentru a raporta o problemă.

## Licență

Acest proiect este licențiat sub licența Apache 2.0. Vedeți fișierul `LICENSE` pentru mai multe detalii. Iconul folosit în cadrul proiectului provine de la [Earthquake icons created by Magnific - Flaticon](https://www.flaticon.com/free-icons/earthquake)
