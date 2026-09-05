# Caratterizzazione in Frequenza, Sfasamento e De-Embedding BVD (Butterworth-Van Dyke)

Questa cartella contiene l'analisi sperimentale dello sweep in frequenza attorno alla risonanza del risonatore MEMS ad arco capacitivo (**DIE D4**), con eccitazione sinusoidale continua a piccolo segnale ($V_{\text{in}} \approx 100\,\text{mV}$, $V_{\text{DC}} = 5.0\,\text{V}$) e lettura tramite front-end a transimpedenza (TIA) con guadagno equivalente:
$$G_e = R_F \times G_{\text{post}} = 500\,\text{k}\Omega \times 10 = 5.0\,\text{M}\Omega \quad (5.0\times 10^6\,\text{V/A})$$

---

## 1. Verifica della Capacità Parassita $C_p$ (scope_70 e scope_69)

Per isolare il vero comportamento meccanico del risonatore (de-embedding del modello BVD), è fondamentale determinare con assoluta accuratezza la capacità parassita di feedthrough $C_p$ dovuta all'accoppiamento elettrostatico diretto tra ingresso e uscita (gap a riposo, piazzole, bonding e package PLCC).

### [A] Misura Diretta Off-Resonance a 50 kHz (`scope_70.csv`)
A frequenze sufficientemente lontane dalla risonanza (es. $f = 50\,\text{kHz}$ contro $f_0 \approx 417.8\,\text{kHz}$, con $Q \approx 2500$ e banda meccanica $\approx 168\,\text{Hz}$), la trave di silicio è **completamente immobile** ($I_{\text{mot}} \equiv 0$). 
Tutta la corrente misurata all'uscita è al 100% puramente capacitiva:
$$I_p = \omega C_p V_{\text{in}} = 2\pi f C_p V_{\text{in}}$$
Poiché $V_{\text{out}} = G_e \cdot I_p$:
$$\boxed{C_p = \frac{V_{\text{out}}}{2\pi f \cdot G_e \cdot V_{\text{in}}} = \frac{\text{Gain}}{2\pi f \cdot G_e}}$$

Dall'elaborazione del file [`scope_70.csv`](file:///c:/Users/lucaa/Downloads/ESM2/ES2M/sfasamento/scope_70.csv):
- **Frequenza:** $f = 50\,000.0\,\text{Hz}$ ($50.0\,\text{kHz}$)
- **Ingresso Ch 3:** $V_{\text{in}} = 99.85\,\text{mV}$ ($V_{\text{pp}} = 199.7\,\text{mV}$)
- **Uscita Ch 1:** $V_{\text{out}} = 140.97\,\text{mV}$ ($V_{\text{pp}} = 281.9\,\text{mV}$)
- **Guadagno misurato:** $\text{Gain} = \frac{V_{\text{out}}}{V_{\text{in}}} = 1.4119\,\text{V/V}$
- **Sfasamento:** $\Delta \phi = +87.43^\circ$ (prossimo ai $+90^\circ$ ideali di una pura capacità)
- **Stima Diretta di $C_p$:**
  $$C_p = \frac{1.41188}{2\pi \times 50\,000 \times 5.0\times 10^6} = \mathbf{0.8989\,\text{pF}} \quad (\mathbf{898.9\,\text{fF}})$$

### [B] Misura Diretta a 417.79 kHz con $V_{\text{DC}} = 0\,\text{V}$ (`scope_69.csv`)
Anche questa misura è stata acquisita con **polarizzazione nulla** ($V_{\text{DC}} = 0\,\text{V}$):
- Poiché il coefficiente di accoppiamento elettromeccanico è proporzionale alla tensione continua $\eta = V_{\text{DC}} \frac{\partial C}{\partial x}$, a $V_{\text{DC}} = 0\,\text{V}$ l'attuazione e il readout sono completamente disattivati: **il ramo motionale non conduce alcuna corrente ($I_{\text{mot}} \equiv 0$)**.
- Nel file [`scope_69.csv`](file:///c:/Users/lucaa/Downloads/ESM2/ES2M/sfasamento/scope_69.csv) ($f = 417\,790.1\,\text{Hz}$):
  - $V_{\text{in}} = 100.2\,\text{mV}$, $V_{\text{out}} = 1.2118\,\text{V} \implies \text{Gain} = 12.094\,\text{V/V}$, $\Delta \phi = +70.91^\circ$.
  - Stima diretta di $C_p$ ad alta frequenza:
    $$C_p = \frac{12.094}{2\pi \times 417\,790 \times 5.0\times 10^6} = \mathbf{0.9214\,\text{pF}} \quad (\mathbf{921.4\,\text{fF}})$$
- **Origine della discrepanza (0.899 pF vs 0.921 pF, ~2.5%) e dello sfasamento ($+70.9^\circ$ anziché $+90^\circ$):**
  A $417.8\,\text{kHz}$, la risposta non ideale del front-end TIA reale (polo del circuito a $f_p \approx 1.1\div 1.2\,\text{MHz}$ dovuto alla capacità di compensazione in retroazione o al GBWP dell'amplificatore) introduce un ritardo di fase di circa $-19^\circ$ ($90^\circ - 19^\circ = 71^\circ$) e una leggera alterazione del guadagno effettivo della catena.

### [C] Confronto con il De-Embedding di Nyquist dello Sweep (42 Punti a $V_{\text{DC}} = 5\,\text{V}$)
- Basamento $C_p$ estratto dal fit analitico BVD sullo sweep con trave attiva: $C_p = \mathbf{0.8968\,\text{pF}}$ ($896.8\,\text{fF}$).
- Discrepanza tra misura diretta a 50 kHz ($0.8989\,\text{pF}$) e de-embedding BVD ($0.8968\,\text{pF}$):
  $$\Delta = \frac{|0.8989 - 0.8968|}{0.8968} \times 100 = \mathbf{0.23\%} \quad (< 2.1\,\text{fF})$$
  Questo conferma in modo eccezionale che la capacità parassita del chip/package è di circa **$0.90\,\text{pF}$** in entrambe le condizioni sperimentali.

---

## 2. Diagramma di Bode Compensato (Ramo Motionale Puro)

Quando il contributo di $C_p$ viene sottratto vettorialmente:
$$\vec{H}_{\text{mot}}(f) = \vec{H}_{\text{misurato}}(f) - \vec{H}_{\text{base}}(f)$$
si isola la risposta puramente meccanica del ramo serie RLC ($R_m - L_m - C_m$):

1. **Modulo Compensato $|H_{\text{mot}}|$:**
   - La curva asimmetrica di Fano (picco a $f_s$ e buca a $f_p$) scompare completamente.
   - Diventa una **campana lorentziana perfettamente simmetrica** centrata sull'autentica frequenza di risonanza meccanica:
     $$f_0 = 417\,718.8\,\text{Hz} \approx 417.72\,\text{kHz}$$
   - Ampiezza di picco: $A_{0,\text{mot}} = 0.4431\,\text{V/V}$.
   - Banda a $-3\,\text{dB}$: $\Delta f_{-3\text{dB}} = \frac{f_0}{Q} = \frac{417719}{2486.7} = 168.0\,\text{Hz}$.

2. **Fase Compensata $\Delta \phi_{\text{mot}}$:**
   - Mostra la **canonica transizione di fase da $180^\circ$** tipica di un risonatore serie del secondo ordine:
     $$\Delta \phi_{\text{mot}}(f) = -\arctan\left( 2Q \frac{f - f_0}{f_0} \right)$$
     - Per $f \ll f_0$ (comportamento capacitivo): $\Delta \phi \to +90^\circ$
     - A $f = f_0$ (risonanza puramente resistiva): $\Delta \phi = 0^\circ$
     - Per $f \gg f_0$ (comportamento induttivo): $\Delta \phi \to -90^\circ$
   - I punti sperimentali compensati seguono perfettamente questa curva teorica a "S", spiegando perché nello sweep grezzo la fase sembrava "strana": il grosso fasore capacitivo $C_p$ ($\approx 11.8\,\text{V/V}$) mascherava la rotazione di $180^\circ$ del piccolo vettore motionale ($\approx 0.44\,\text{V/V}$).

---

## 3. Parametri Fisici e Circuitali BVD Riassuntivi

| Parametro | Descrizione Fisica | Valore Estratto |
| :--- | :--- | :--- |
| **$f_s$** | Picco risonanza serie (analitico grezzo) | **$417\,644.4\,\text{Hz}$** ($G = 12.017\,\text{V/V}$) |
| **$f_p$** | Minimo antirisonanza (analitico grezzo) | **$417\,811.3\,\text{Hz}$** ($G = 11.579\,\text{V/V}$) |
| **$\Delta f$** | Separazione picco-buca ($f_p - f_s$) | **$166.9\,\text{Hz}$** |
| **$f_0$** | Risonanza meccanica intrinseca | **$417\,718.81\,\text{Hz}$** |
| **$Q$** | Fattore di qualità meccanico | **$2486.7$** |
| **$\Delta f_{-3\text{dB}}$** | Banda passante a $-3\,\text{dB}$ | **$168.0\,\text{Hz}$** |
| **$A_0$** | Guadagno motionale al picco | **$0.4431\,\text{V/V}$** |
| **$C_p$ (misurato a 50 kHz)** | Capacità parassita da `scope_70.csv` | **$0.8989\,\text{pF}$** ($898.9\,\text{fF}$) |
| **$C_p$ (de-embedding sweep)** | Capacità parassita da baseline BVD/Nyquist | **$0.8972\,\text{pF}$** ($897.2\,\text{fF}$) |
| **$R_m$** | Resistenza equivalente motionale ($G_e / A_0$) | **$11.284\,\text{M}\Omega$** |
| **$L_m$** | Induttanza equivalente motionale | **$10.69\,\text{kH}$** |
| **$C_m$** | Capacità equivalente motionale | **$13.578\,\text{aF}$** |

---

## 4. Script di Analisi e Riproduzione

Lo script Python completo per l'estrazione dati, calcolo fasoriale, fit BVD e de-embedding è:
- **[`analizza_sfasamento.py`](file:///c:/Users/lucaa/Downloads/ESM2/ES2M/sfasamento/analizza_sfasamento.py)**
- **[`plot_calcolo_cp.py`](file:///c:/Users/lucaa/Downloads/ESM2/ES2M/sfasamento/plot_calcolo_cp.py)** (script dedicato per plottare i segnali temporali $V_{\text{in}}$ e $V_{\text{out}}$ di `scope_70` e `scope_69`)

### Modalità d'uso:
```bash
# Esecuzione rapida istantanea (sfrutta i dati precalcolati in tabella_sweep_completo.csv):
py -3 analizza_sfasamento.py

# Ricalcolo completo dai file scope grezzi:
py -3 analizza_sfasamento.py --recompute

# Generazione immediata del solo grafico 'Calcolo Cp' (50 kHz e 417.8 kHz):
py -3 plot_calcolo_cp.py
```

---

## 5. Galleria dei Grafici Generati

1. **[`calcolo_Cp.png`](file:///c:/Users/lucaa/Downloads/ESM2/ES2M/sfasamento/calcolo_Cp.png)**:
   - Titolo: *"Calcolo Cp"*
   - Mostra il confronto diretto delle forme d'onda temporali $V_{\text{in}}$ e $V_{\text{out}}$:
     - Riquadro superiore: $50\,\text{kHz}$ off-resonance (`scope_70.csv`), sfasamento di $+87.4^\circ$ puramente capacitivo da cui si calcola $C_p = 0.8989\,\text{pF}$.
     - Riquadro inferiore: $417.79\,\text{kHz}$ in prossimità della risonanza/antirisonanza (`scope_69.csv`).
2. **[`bode_ampiezza_fase.png`](file:///c:/Users/lucaa/Downloads/ESM2/ES2M/sfasamento/bode_ampiezza_fase.png)** e **[`bode_ampiezza_fase_compensato.png`](file:///c:/Users/lucaa/Downloads/ESM2/ES2M/sfasamento/bode_ampiezza_fase_compensato.png)**:
   - Titolo: *"Risposta compensata da Cp"*
   - Asse verticale: *"Guadagno senza Cp (compensata)"* e *"Sfasamento"*
   - Curve: Dati (37 punti coerenti Serie 1) e Fit lorentziano puro con transizione di fase RLC.
3. **[`bode_ampiezza_fase_grezzo.png`](file:///c:/Users/lucaa/Downloads/ESM2/ES2M/sfasamento/bode_ampiezza_fase_grezzo.png)**:
   - Titolo: *"Risposta in frequenza"*
   - Curve: Dati (esclusi gli scope 139..143 affetti da deriva termica) e Fit BVD analitico (risonanza di Fano).
4. **[`bode_ampiezza_fase_compensato_zoom.png`](file:///c:/Users/lucaa/Downloads/ESM2/ES2M/sfasamento/bode_ampiezza_fase_compensato_zoom.png)**:
   - Dettaglio ad alta risoluzione nella banda di risonanza ($417.4 \div 418.1\,\text{kHz}$) pulito e coerente.
5. **[`bode_confronto_completo.png`](file:///c:/Users/lucaa/Downloads/ESM2/ES2M/sfasamento/bode_confronto_completo.png)**:
   - Pannello di confronto $2\times 2$ completo (Risposta Grezza vs Risposta Compensata).
6. **[`deembedding_confronto.png`](file:///c:/Users/lucaa/Downloads/ESM2/ES2M/sfasamento/deembedding_confronto.png)**:
   - Confronto orizzontale Before & After sui moduli.
7. **[`piano_complesso_nyquist.png`](file:///c:/Users/lucaa/Downloads/ESM2/ES2M/sfasamento/piano_complesso_nyquist.png)**:
   - Diagramma nel piano complesso di Nyquist con il cerchio di risonanza isolato e centrato sull'asse reale.


