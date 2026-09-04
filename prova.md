Listed directory ES2M
Listed directory Paper
Searched for "burst"
Listed directory Modellizzazione
Searched for "burst"
Searched for "cicl"
Searched for "burst"
Viewed Appunti_PMUT_Equazioni_Ringdown.tex:1-100
Searched for "ringdown"
Viewed Appunti_PMUT_Equazioni_Ringdown.tex:101-250
Viewed Appunti_PMUT_Equazioni_Ringdown.tex:251-450
Viewed Appunti_PMUT_Equazioni_Ringdown.tex:451-530
Listed directory Chat%20Ai%20e%20appunti
Listed directory Misure
Viewed scope_10.csv:1-30
Listed directory Effetto%20strano
Ran command: `python -c "import pypdf; print('pypdf installed')" 2>$null || python -c "import fitz; print('PyMuPDF installed')" 2>$null || python -c "print('python works')"`
Ran command: `python -c "print('python works')"`
Ran command: `py --version`
Ran command: `py -m pip list`
Ran command: `py -c "
import fitz, glob, os

for pdf_path in glob.glob('Paper/*.pdf'):
    doc = fitz.open(pdf_path)
    print('===', os.path.basename(pdf_path), 'pages:', len(doc), '===')
    for i, page in enumerate(doc):
        txt = page.get_text()
        for kw in ['burst', 'cycle', 'ringdown', 'ring-down', 'decay', 'excitation', 'period']:
            if kw in txt.lower():
                # print matches
                lines = [l for l in txt.split('\n') if any(k in l.lower() for k in ['burst', 'cycle', 'ringdown', 'ring-down', 'period', 'f0', 'khz', 'q1', 'tau'])]
                if lines:
                    print(f'Page {i+1} mentions {kw}:')
                    print('   ', '\n    '.join(lines[:10]))
                break
"`
Ran command: `py -c "
import pymupdf, sys

def search_doc(path):
    doc = pymupdf.open(path)
    print(f'*** {path} ***')
    for i, p in enumerate(doc):
        t = p.get_text()
        for term in ['burst', 'cycle', 'gate', 'period', 'ring-down', 'ringdown', 'excitation']:
            if term in t.lower():
                for line in t.split('\n'):
                    if any(k in line.lower() for k in ['burst', 'duty', 'tg', 'cycle', 'period', 'number of cycles', 'n_c', 'pulses', 'sinusoid']):
                        # filter ascii
                        safe = line.encode('ascii', errors='replace').decode('ascii')
                        print(f'P{i+1}: {safe}')

search_doc('Paper/sensors-21-06414.pdf')
"`
Ran command: `py -c "
import pymupdf

doc = pymupdf.open('Paper/A15_2026_IEEE_Sensors_Letters.pdf')
for i, page in enumerate(doc):
    txt = page.get_text()
    if 'burst' in txt.lower() or 'gate' in txt.lower() or 'period' in txt.lower():
        print(f'=== Page {i+1} ===')
        for par in txt.split('\n\n'):
            if any(k in par.lower() for k in ['burst', 'gate', 'period', 'ring-down', 'decay', '12 ms']):
                safe = par.encode('ascii', errors='replace').decode('ascii')
                print('---')
                print(safe)
"`
Ran command: `py -c "
import pymupdf

doc = pymupdf.open('Paper/2026_02_20_UniBSMeasurements_Report.pptx.pdf')
for p in [5, 6, 7, 8, 21, 22]:
    if p < len(doc):
        print(f'=== Slide {p+1} ===')
        txt = doc[p].get_text()
        print(txt.encode('ascii', errors='replace').decode('ascii'))
"`
Ran command: `py -c "
import pandas as pd
import numpy as np

df = pd.read_csv('Misure/scope_10.csv', skiprows=2)
print('Columns:', df.columns)
print('Shape:', df.shape)
print('Time min, max, dt:', df.iloc[:,0].min(), df.iloc[:,0].max(), df.iloc[1,0]-df.iloc[0,0])
for col in df.columns[1:]:
    valid = df[col].dropna()
    if len(valid) > 0:
        print(f'{col}: min={valid.min():.4f}, max={valid.max():.4f}, count={len(valid)}')
"`
Ran command: `py -c "
with open('Misure/scope_10.csv') as f:
    lines = [f.readline() for _ in range(15)]
for l in lines:
    print(l.strip())
"`
Ran command: `py -c "
import numpy as np

data = []
with open('Misure/scope_10.csv') as f:
    for i, line in enumerate(f):
        if i < 2: continue
        parts = line.strip().split(',')
        if len(parts) >= 4 and parts[1] != '':
            try:
                data.append([float(parts[0]), float(parts[1]), float(parts[2]), float(parts[3])])
            except:
                pass
arr = np.array(data)
print('Shape:', arr.shape)
print(f'Time: from {arr[0,0]*1e3:.3f} ms to {arr[-1,0]*1e3:.3f} ms (duration = {(arr[-1,0]-arr[0,0])*1e3:.3f} ms)')
print(f'dt = {(arr[1,0]-arr[0,0])*1e6:.4f} us (fs = {1/(arr[1,0]-arr[0,0])/1e6:.2f} MHz)')
for ch in range(1, 4):
    print(f'Ch {ch}: min = {arr[:, ch].min():.3f} V, max = {arr[:, ch].max():.3f} V')
"`
Ran command: `py -c "
import numpy as np

data = []
with open('Misure/scope_10.csv') as f:
    for i, line in enumerate(f):
        if i < 2: continue
        parts = line.strip().split(',')
        if len(parts) >= 4 and parts[1] != '':
            try:
                data.append([float(parts[0]), float(parts[1]), float(parts[2]), float(parts[3])])
            except:
                pass
arr = np.array(data)
t = arr[:, 0]
gate = arr[:, 2]
high = gate > 1.5
transitions = np.where(np.diff(high.astype(int)) != 0)[0]
print('Transitions at indices:', transitions)
for tr in transitions:
    print(f'Transition at t = {t[tr]*1e3:.4f} ms, from gate={gate[tr]:.2f} to {gate[tr+1]:.2f}')
"`
Ran command: `py -c "
import numpy as np

data = []
with open('Misure/scope_10.csv') as f:
    for i, line in enumerate(f):
        if i < 2: continue
        parts = line.strip().split(',')
        if len(parts) >= 4 and parts[1] != '':
            try:
                data.append([float(parts[0]), float(parts[1]), float(parts[2]), float(parts[3])])
            except:
                pass
arr = np.array(data)
t = arr[:, 0]
ch1 = arr[:, 1]
ch3 = arr[:, 3]

print('Before t=4.818ms:')
print('  Ch1 std:', np.std(ch1[t < 4.818e-3]), 'Ch3 std:', np.std(ch3[t < 4.818e-3]))
print('After t=4.818ms:')
print('  Ch1 std (first 1ms):', np.std(ch1[(t >= 4.818e-3) & (t < 5.818e-3)]), 'Ch3 std:', np.std(ch3[(t >= 4.818e-3) & (t < 5.818e-3)]))
print('  Ch1 std (last 1ms):', np.std(ch1[t >= 8.465e-3]), 'Ch3 std:', np.std(ch3[t >= 8.465e-3]))
"`
Ran command: `Get-ChildItem -Recurse -Filter *.py`

La confusione tra questi parametri è molto comune quando si passa dalla teoria del risonatore al banco di misura con il generatore di funzioni (come l'Agilent 33220A citato nei vostri report).

Vediamo in dettaglio **cosa significano fisicamente**, **perché vanno impostati entrambi**, e **i valori esatti da impostare ricavati direttamente dai paper nella cartella [Paper](file:///c:/Users/lucaa/Downloads/ESM2/ES2M/Paper)**.

---

### 1. Il quadro fisico: come si genera un Ringdown

Per osservare il decadimento libero (*ringdown*), devi fare due cose in sequenza:
1. **Fase ON (Carica/Eccitazione):** Fai oscillare il risonatore applicando una sinusoide alla sua frequenza di risonanza $f_0$.
2. **Fase OFF (Decadimento/Ascolto):** Spegni istantaneamente l'eccitazione ($V_{\text{in}} = 0$) e lasci che il risonatore vibri liberamente dissipando l'energia accumulata con la sua costante di tempo $\tau$:
   $$q(t) = Q_0 e^{-t/\tau} \cos(\omega_0 t)$$

Poiché per vedere bene il segnale sull'oscilloscopio (fare le medie a 500 tracce, agganciare il trigger) l'esperimento deve ripetersi periodicamente, si usa la modalità **Burst**.

---

### 2. Differenza tra "Numero di Cicli" e "Periodo del Burst"

Immagina tre diverse scale temporali:

```
|--- 1 ciclo ---| (T_sin = 1/f0 ≈ 2.39 µs)
 ~~~ ~~~ ~~~ ~~~
|___________________________|__________________________________|
        T_ON (N cicli)                 T_OFF (Ringdown)
|                                                              |
|<---------------------- T_burst (12 ms) --------------------->|
 (Inizio Burst 1)                                               (Inizio Burst 2)
```

1. **Periodo della Sinusoide ($T_{\text{sin}} = 1/f_0$):**
   È la durata di una singola oscillazione. A $f_0 = 418\text{ kHz}$, ciascun ciclo dura:
   $$T_{\text{sin}} = \frac{1}{418\text{ kHz}} \approx 2.39\,\mu\text{s}$$

2. **Numero di Cicli ($N$ o *Burst Count*):**
   È **quante sinusoidi consecutive** il generatore spara prima di tacere. Determina la durata dell'eccitazione ($T_{\text{ON}}$):
   $$T_{\text{ON}} = N \times T_{\text{sin}} = \frac{N}{f_0}$$
   - Se metti $N = 20$ cicli: l'eccitazione dura solo $48\,\mu\text{s}$.
   - Se metti $N = 2500$ cicli: l'eccitazione dura circa $6\text{ ms}$.

3. **Periodo del Burst ($T_{\text{burst}}$ o $T_g$):**
   È il **tempo totale tra l'inizio di un pacchetto e l'inizio di quello successivo**. Fissa il rate di ripetizione dell'intero esperimento ($f_{\text{rep}} = 1/T_{\text{burst}}$).
   $$T_{\text{burst}} = T_{\text{ON}} + T_{\text{OFF}}$$

#### Perché serve impostarli ENTRAMBI?
Se dicessi al generatore solo *"il periodo del burst è 12 ms"*, il generatore **non saprebbe quando smettere di eccitare e iniziare a tacere**:
- Potrebbe eccitare per $1\,\mu\text{s}$ e tacere per $11.999\text{ ms}$ (il risonatore non farebbe nemmeno in tempo a muoversi);
- Oppure potrebbe eccitare per $11.9\text{ ms}$ e tacere per $0.1\text{ ms}$ (il ringdown verrebbe troncato sul nascere dal burst successivo).

Impostando entrambi, definisci:
- **$N$ (o $T_{\text{ON}}$):** quanto a lungo carichi il risonatore;
- **$T_{\text{burst}} - T_{\text{ON}} = T_{\text{OFF}}$:** quanto tempo lasci all'oscilloscopio per registrare tutto il decadimento libero prima che riparta la nuova eccitazione.

---

### 3. Cosa c'è scritto nei Paper di riferimento

Nella cartella `Paper` ci sono due tipologie di studio con esigenze diverse:

#### Caso A: Il vostro Risonatore MEMS ad Arco ([Nastro et al. 2026](file:///c:/Users/lucaa/Downloads/ESM2/ES2M/Paper/A15_2026_IEEE_Sensors_Letters.pdf) e [Report Sperimentale UniBS 2026](file:///c:/Users/lucaa/Downloads/ESM2/ES2M/Paper/2026_02_20_UniBSMeasurements_Report.pptx.pdf))
Il dispositivo ad arco lavora in vuoto parziale ($70\text{ mbar}$) con un fattore di qualità molto elevato ($Q \approx 2800 \div 3300$) a $f_0 \approx 418\text{ kHz}$.
- **Costante di tempo naturale:**
  $$\tau = \frac{2Q}{\omega_0} = \frac{Q}{\pi f_0} \approx \frac{2800}{\pi \cdot 418\text{ kHz}} \approx 2.14\text{ ms}$$
- **Tempo per raggiungere il regime:** Un risonatore ha bisogno di circa $3\tau \approx 6.4\text{ ms}$ per raggiungere il 95% dell'ampiezza massima di oscillazione a regime stazionario.
- **Tempo per spegnersi:** Ha bisogno di altri $3\tau \div 4\tau \approx 6 \div 8\text{ ms}$ per far decadere le oscillazioni sotto il rumore.

Nel **Report Sperimentale UniBS** (Slide 7 e 22) e nell'articolo **IEEE Sensors Letters** (Sezione III), l'impostazione usata è:
> *"Gate signal $v_g(t)$, Burst mode: Period $T_g = 12\text{ ms}$, Duty Cycle $50\%$, $f_s = 418\text{ kHz}$"*

Poiché il Duty Cycle è al 50%:
- **Tempo di eccitazione ($T_{\text{ON}}$):** $50\% \times 12\text{ ms} = \mathbf{6\text{ ms}}$
- **Tempo di ringdown ($T_{\text{OFF}}$):** $50\% \times 12\text{ ms} = \mathbf{6\text{ ms}}$

Se convertiamo quei $6\text{ ms}$ di eccitazione in **numero di cicli**:
$$N = f_0 \times T_{\text{ON}} = 418\text{ kHz} \times 6\text{ ms} = 418{,}000 \times 0.006 \approx \mathbf{2500\text{ cicli}}$$

*(Questo trova riscontro diretto nei vostri file CSV in `Misure/scope_10.csv`: il canale 2 è il Gate che scende a $4.8\text{ ms}$, il canale 3 dell'eccitazione si azzera, e il canale 1 mostra circa $4.6\text{ ms}$ di puro ringdown che decade).*

---

#### Caso B: Il PMUT per Ultrasuoni ([Wu et al. 2021, Sensors](file:///c:/Users/lucaa/Downloads/ESM2/ES2M/Paper/sensors-21-06414.pdf))
Nel paper di Wu et al. il dispositivo è una membrana ultrasonica a $115\text{ kHz}$ usata per telemetria sonar (*pulse-echo*).
- Qui **non** si vogliono $2500$ cicli, perché un impulso di $6\text{ ms}$ continuerebbe a trasmettere mentre l'eco del bersaglio sta già tornando indietro, creando un'enorme zona cieca (*blind area*).
- Per questo, a pagina 8 e 11 di Wu et al., viene impostato un pacchetto brevissimo:
  > *"The input excitation signal is a 115-kHz sine signal of **20 cycles** with an amplitude of 1Vpp"*
  $$T_{\text{ON}} = \frac{20}{115\text{ kHz}} \approx 174\,\mu\text{s}$$

---

### 4. Cosa devi impostare tu (Guida Pratica al Generatore)

Se stai caratterizzando il **risonatore MEMS ad arco** (per studiare Duffing, risonanza 1:2 o il ringdown naturale):

| Parametro sul Generatore | Valore consigliato dai Paper | Perché |
| :--- | :--- | :--- |
| **Carrier Frequency ($f_c$)** | **$416.6 \div 418\text{ kHz}$** | Frequenza di risonanza del 1° modo flessionale. |
| **Burst Mode** | **Triggered (N-Cycle)** oppure **Gated** | Dipende se usi il trigger interno o un gate esterno. |
| **# of Cycles ($N$, Burst Count)** | **$2500$ cicli** (oppure Duty Cycle $50\%$) | Dura $\approx 6\text{ ms}$: porta il MEMS a regime stazionario completo ($> 95\%$). |
| **Burst Period ($T_{\text{burst}}$)** | **$12\text{ ms}$** (o $15\text{ ms}$) | Lascia $6 \div 9\text{ ms}$ di buio ($T_{\text{OFF}}$), sufficienti per osservare l'intero ringdown fino a zero prima della misura successiva. |

> [!TIP]
> Se il generatore (es. Agilent 33220A) ti chiede **"Burst Period"** e **"# of Cycles"**:
> 1. Imposta **# Cycles = 2500**
> 2. Imposta **Burst Period = 12 ms** (o 15 ms).
> In questo modo avrai esattamente 6 ms di eccitazione e 6 ms (o 9 ms) di ringdown libero da acquisire con l'oscilloscopio.