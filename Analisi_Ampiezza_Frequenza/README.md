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
| **[`analizza_ringdown_frequenza.py`](./analizza_ringdown_frequenza.py)** | Script Python | Suite completa: elabora tutti i 25 file CSV in `../Misure/`, estrae $f_s$, $\tau$, $Q$, salva la tabella CSV e genera i 4 grafici |
| **[`plot_campana_e_inviluppi.py`](./plot_campana_e_inviluppi.py)** | Script Python | Generazione rapida dedicata per la campana di risonanza e la galleria degli inviluppi con stile minimale accademico |
| **[`simula_duffing_ideale.py`](./simula_duffing_ideale.py)** | Script Python | Simulazione teorica/dimostrativa del regime non-lineare di Duffing con isteresi (sweep-up e sweep-down) |
| **[`tabella_risultati_ringdown.csv`](./tabella_risultati_ringdown.csv)** | Tabella Dati | Valori numerici per ciascun file: $f_{\mathrm{in}}$, $f_s$, $\Delta f$, $A_0$ [mV], $\tau$ [ms], $Q$, $R^2$, $A_{\mathrm{RMS}}$ |
| **[`campana_risonanza_A0_vs_freq.png`](./campana_risonanza_A0_vs_freq.png)** | Grafico 1 | Campana di risonanza $A_0$ vs $f_{\mathrm{in}}$ e risposta centrata vs $\Delta f = f_{\mathrm{in}} - f_s$, in stile Bode minimale (punti e fit dello stesso colore, senza clutter) |
| **[`gallery_inviluppi_ringdown.png`](./gallery_inviluppi_ringdown.png)** | Grafico 2 | Esempi di decadimento libero ed inviluppo Hilbert a diverse frequenze di eccitazione (layout essenziale senza legende ridondanti) |
| **[`deriva_frequenza_e_tau.png`](./deriva_frequenza_e_tau.png)** | Grafico 3 | Verifica della stabilità di $f_s$ lungo la sequenza temporale e invarianza intrinseca di $\tau$ e $Q$ |
| **[`analisi_duffing_intra_ringdown.png`](./analisi_duffing_intra_ringdown.png)** | Grafico 4 | Spettrogramma STFT e frequenza istantanea $f(t)$ per verificare l'assenza di forti non-linearità a $100\,\mathrm{mV}_{\mathrm{pp}}$ |

---

## 🚀 Come rieseguire l'analisi
Dalla cartella corrente:
```bash
# Per la suite completa di misura
py -3 analizza_ringdown_frequenza.py

# Per generare rapidamente solo la campana e gli inviluppi
py -3 plot_campana_e_inviluppi.py
```
oppure dalla radice del repository:
```bash
py -3 Analisi_Ampiezza_Frequenza/plot_campana_e_inviluppi.py
```
