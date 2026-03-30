# Financial Dashboard V1.4 - Deployment Walkthrough

Qui troverai il riepilogo delle modifiche e le istruzioni finali per completare la pubblicazione della tua applicazione sul Cloud.

## 1. Sistema di Accesso (Completato)
Il codice della tua applicazione ora integra una schermata di inserimento credenziali prima di rendere visibile il resto del contenuto. 

Le credenziali predefinite configurate in locale sono:
- **Username**: `admin`
- **Password**: `admin123`

## 2. Pubblicazione su Streamlit Cloud (Da fare)
Avendo creato e collegato il tuo progetto a GitHub, ecco i passi per portare la tua app sul web:

1. Vai su [share.streamlit.io](https://share.streamlit.io/) e accedi usando il tuo account GitHub appena creato.
2. Clicca sul tasto azzurro in alto a destra **New app**.
3. Seleziona **"Use existing repo"** (Usa un repository esistente).
4. Compila i campi in questo modo:
   - **Repository**: `IA-007/financial-dashboard`
   - **Branch**: `main`
   - **Main file path**: `app.py`
5. **ATTENZIONE A QUESTO PASSAGGIO - I Segreti!**
   Prima di cliccare "Deploy", scorri in basso e clicca su **Advanced settings** (Impostazioni avanzate).
   Nella casella di testo denominata **Secrets**, devi incollare il contenuto del file `.streamlit/secrets.toml`. Poiché non l'abbiamo caricato su GitHub per sicurezza, eccolo qui sotto da copiare e incollare:

```toml
[credentials.usernames.admin]
email = "admin@example.com"
name = "Admin"
password = "$2b$12$Yeg/xsW8qW2odV1bjZwhWufoCLUyw3HPpWGGMZa/YkpGK24cLCvri"

[cookie]
expiry_days = 30
key = "una_chiave_segreta_molto_lunga_e_casuale_qui"
name = "financial_dashboard_cookie"

[preauthorized]
emails = []
```

6. Clicca **Save** e poi il tasto blu **Deploy!**.

Entro 1-2 minuti la tua dashboard sarà calcolata, dotata di login e accessibile in remoto da ovunque tramite il link che si aprirà automaticamente! 🎉
