# Suite di Misura: Risposta in Frequenza del Ringdown

Cartella dedicata all'analisi sperimentale dell'ampiezza di decadimento libero (*ringdown*) in funzione della frequenza di eccitazione attorno alla risonanza ammorbidita $f_s$.

## 🔬 Condizioni Sperimentali
- **Dispositivo**: Risonatore capacitivo ad arco MEMS in polisilicio (DIE D4)
- **Tensione DC**: $V_{\mathrm{DC}} = 5.0\,\mathrm{V}$ (regime di *spring softening*)
- **Ampiezza AC**: $V_{\mathrm{in}} = 100\,\mathrm{mV}_{\mathrm{pp}}$
- **Burst**: 2500 cicli sinusoidali
- **Periodo Burst ($T_g$)**: $12\,\mathrm{ms}$
- **File di misura sorgente**: `../Misure/scope_5.csv` ... `../Misure/scope_29.csv` (25 punti)

---

## 📂 Contenuto della Cartella

| File | Tipo | Descrizione |
|---|---|---|
| **[`analizza_ringdown_frequenza.py`](./analizza_ringdown_frequenza.py)** | Script Python | Elabora tutti i file CSV in `../Misure/`, rileva lo spegnimento del gate, applica il blanking di $30\,\mu\mathrm{s}$, calcola l'inviluppo di Hilbert, esegue il fit esponenziale ai minimi quadrati, estrae $f_s$, $\tau$, $Q$ e genera i grafici |
| **[`tabella_risultati_ringdown.csv`](./tabella_risultati_ringdown.csv)** | Tabella Dati | Valori numerici per ciascun file: $f_{\mathrm{in}}$, $f_s$, $\Delta f$, $A_0$ [mV], $\tau$ [ms], $Q$, $R^2$, $A_{\mathrm{RMS}}$ |
| **[`campana_risonanza_A0_vs_freq.png`](./campana_risonanza_A0_vs_freq.png)** | Grafico 1 | Campana di risonanza $A_0$ vs $f_{\mathrm{in}}$ e risposta centrata vs $\Delta f = f_{\mathrm{in}} - f_s^{(i)}$, con fit Lorentziano e banda a $-3\,\mathrm{dB}$ |
| **[`deriva_frequenza_e_tau.png`](./deriva_frequenza_e_tau.png)** | Grafico 2 | Verifica della deriva termica di $f_s$ lungo la sequenza e dimostrazione dell'invarianza intrinseca di $\tau$ e $Q$ |
| **[`gallery_inviluppi_ringdown.png`](./gallery_inviluppi_ringdown.png)** | Grafico 3 | Confronto a 4 riquadri dei segnali nel tempo, inviluppi e fit a diverse frequenze |
| **[`analisi_duffing_intra_ringdown.png`](./analisi_duffing_intra_ringdown.png)** | Grafico 4 | Spettrogramma STFT e traccia della frequenza istantanea $f(t)$ per verificare l'effetto Duffing a grande ampiezza |

---

## 🚀 Come rieseguire l'analisi
Dalla cartella corrente:
```bash
python analizza_ringdown_frequenza.py
```
oppure dalla radice del repository:
```bash
python Analisi_Ampiezza_Frequenza/analizza_ringdown_frequenza.py
```
