Viewed Guida_Completa_Misure_MEMS.md:1-100
Listed directory ES2M
Listed directory Modellizzazione
Searched for "Cp"
Viewed Appunti_PMUT_Equazioni_Ringdown.tex:260-380
Listed directory Misure
Viewed prova2.md:1-100
Viewed Analisi%20Paper%20Qwen.md:560-620
Viewed Analisi%20Paper%20Qwen.md:620-680
Searched for "R_F"

Hai centrato in pieno **tutti i punti chiave** della caratterizzazione sperimentale di un risonatore MEMS! 

Quello che stai affrontando è il classico problema di **de-embedding del modello Butterworth-Van Dyke (BVD)**: il tuo segnale misurato è la somma di due contributi in parallelo:
1. Il **ramo parassita/feedthrough ($C_p$)**: accoppiamento elettrostatico diretto tra ingresso e uscita (pad, piste, armature a riposo).
2. Il **ramo motionale ($R_m - L_m - C_m$)**: corrente generata dall'effettivo movimento meccanico della trave.

All'uscita del TIA (con guadagno di transimpedenza $G_e = R_F \frac{R_2}{R_1} = 10^6\,\Omega = 1\,\text{M}\Omega$), la corrente totale che leggi è:
$$\vec{I}_{\text{tot}}(\omega) = \vec{I}_p(\omega) + \vec{I}_m(\omega) = \underbrace{j\omega C_p \vec{V}_{\text{in}}}_{\text{Parassita } C_p} + \underbrace{\frac{\vec{V}_{\text{in}}}{R_m + j\left(\omega L_m - \frac{1}{\omega C_m}\right)}}_{\text{Ramo Motionale}}$$

Ecco una **guida completa, passo per passo**, su cosa fare sperimentalmente, quali valori fissare, come gestire fase e fasori, e il metodo migliore da presentare nella relazione.

---

### 1. Come Misurare Sperimentalmente $C_p$

Ci sono due modi sperimentali pulitissimi. Il primo è una vera "chicca" per la relazione:

#### Metodo A (Il più elegante e inconfutabile): Misura a $V_{\text{DC}} = 0\,\text{V}$
Nel MEMS capacitivo, la trasduzione elettromeccanica (la forza e la corrente motionale) esiste **solo se c'è polarizzazione DC** ($\alpha \propto V_{\text{DC}}$).
- Se imposti sull'alimentatore **$V_{\text{DC}} = 0\,\text{V}$**, il ramo motionale $R_m-L_m-C_m$ è **completamente spento** (la trave non si muove, $R_m \to \infty$).
- Anche eccitando alla frequenza di risonanza ($f \approx 417.8\,\text{kHz}$), **non ci sarà alcuna risonanza meccanica**.
- Tutta la corrente che attraversa il dispositivo è **al 100% la corrente parassita $I_p$ che scorre in $C_p$**!

**Formula diretta per ricavare $C_p$:**
Poiché $|I_p| = \omega C_p V_{\text{in}} = 2\pi f C_p V_{\text{in}}$ e la tensione in uscita al TIA è $V_{\text{out}} = G_e |I_p|$:
$$\boxed{C_p = \frac{|V_{\text{out}}|}{2\pi f \cdot G_e \cdot |V_{\text{in}}|}}$$

*Verifica dello sfasamento:* Poiché è una pura capacità, la corrente anticipa la tensione di $+90^\circ$. Se il front-end è invertente, vedrai un salto di fase netto di $-90^\circ$ (o $+90^\circ$ a seconda dei segni degli stadi), costante su tutta la banda.

#### Metodo B: Misura Fuori Risonanza (Off-Resonance)
Se tieni $V_{\text{DC}} = 5\,\text{V}$, ma ti metti a una frequenza lontana (es. $f = 100\,\text{kHz}$ o $f = 800\,\text{kHz}$):
- Essendo $Q \approx 3000$, la banda della risonanza meccanica è strettissima ($\Delta f \approx 140\,\text{Hz}$).
- A $100\,\text{kHz}$ il risonatore meccanico è immobile ($I_m \approx 0$).
- Misuri $|V_{\text{out}}|$ e applichi la stessa formula inversa: $C_p = \frac{|V_{\text{out}}|}{2\pi f G_e V_{\text{in}}}$.

> **Tip per la relazione:** Nei MEMS con package PLCC e TIA su PCB, $C_p$ si aggira tipicamente tra **$0.2\,\text{pF}$ e $2\,\text{pF}$** (somma di capacità di gap, pad chip, bondwire e capacità parassite dei pin).

---

### 2. Comportamento Induttivo, Capacitivo e lo Sfasamento: Cosa succede?

Nel ramo motionale $Z_m(j\omega) = R_m + j\left(\omega L_m - \frac{1}{\omega C_m}\right)$:

| Frequenza | Comportamento del Ramo Motionale | Sfasamento Corrente $\vec{I}_m$ vs $\vec{V}_{\text{in}}$ |
| :--- | :--- | :--- |
| **$f < f_0$ (Bassa frequenza)** | **Capacitivo** (domina $\frac{1}{\omega C_m}$) | Corrente in **anticipo** ($+90^\circ$) |
| **$f = f_0$ (Risonanza serie)** | **Puramente Resistivo** ($Z_m = R_m$) | Corrente **in fase** ($0^\circ$) $\implies$ Picco massimo di corrente |
| **$f > f_0$ (Alta frequenza)** | **Induttivo** (domina $\omega L_m$) | Corrente in **ritardo** ($-90^\circ$) |

#### Perché c'è una "buca" subito dopo il picco? (L'Antirisonanza $f_p$)
Appena superi $f_0$, il ramo motionale diventa **induttivo**. 
Questo induttore equivalente si trova in parallelo alla capacità $C_p$! 
A una frequenza leggermente superiore $f_p$:
- La corrente induttiva motionale e la corrente capacitiva parassita hanno ampiezza identica ma **fase opposta ($180^\circ$)**.
- Esse si **cancellano a vicenda** ($\vec{I}_{\text{tot}} \to 0$): si forma una profonda buca (*antirisonanza parallelo*).
- Ecco perché la curva reale non è una campana simmetrica, ma una forma asimmetrica (forma di Fano) con un picco a $f_s$ seguito da un minimo a $f_p$.

```
 Guadagno |Vout/Vin|
      ^
      |         /\  <- Picco Risonanza Serie (fs)
      |        /  \
 Baseline Cp->/    \      /--- Baseline Cp (cresce con w*Cp)
      |      /      \    /
      |     /        \  /
      |____/          \/ <- Minimo Antirisonanza Parallelo (fp)
      +------------------------------------> Frequenza f
```

---

### 3. Che Valori Fissare sul Banco di Misura?

Per estrarre i parametri lineari $R_m, L_m, C_m$, **devi lavorare in regime rigorosamente lineare**:
1. **$V_{\text{DC}} = 5\,\text{V}$**: valore nominale (i parametri $R_m, L_m, C_m$ dipendono da $V_{\text{DC}}$!).
2. **$V_{\text{in}} = 50\,\text{mV} \div 100\,\text{mV}$**: **NON usare $500\,\text{mV}$ o $1\,\text{V}$**, altrimenti il MEMS entra nel regime non lineare di Duffing (softening elettrostatico), la campana si piega a sinistra e i valori di $Q$ e $R_m$ risultano falsati.

---

### 4. Come Calcolare Sperimentalmente $R_m, L_m, C_m$

Hai a disposizione **due approcci eccezionali**:

---

#### APPROCCIO 1: Sottrazione da Fasori (De-embedding su Sweep in Frequenza)
È il metodo più rigoroso della letteratura scientifica:

1. **Esegui uno sweep fine attorno alla risonanza** (ad es. da $416.5\,\text{kHz}$ a $418.5\,\text{kHz}$, a passi di $20\,\text{Hz}$):
   - Per ogni frequenza $f$, registri l'ampiezza $|V_{\text{out}}(f)|$ e lo sfasamento $\phi(f)$ rispetto a $V_{\text{in}}$.
   - Costruisci il fasore della corrente totale:
     $$\vec{I}_{\text{tot}}(f) = \frac{|V_{\text{out}}(f)| e^{j\phi(f)}}{G_e}$$

2. **Sottrai il fasore parassita di $C_p$**:
   Sapendo che $\vec{I}_p(f) = j 2\pi f C_p V_{\text{in}}$ (dove $C_p$ l'hai ricavata al punto 1):
   $$\vec{I}_m(f) = \vec{I}_{\text{tot}}(f) - j 2\pi f C_p V_{\text{in}}$$

3. **Cosa ottieni?**
   Plottando il modulo $|\vec{I}_m(f)|$, la buca dell'antirisonanza scompare e ti ritrovi una **campana lorentziana simmetrica perfetta**!

4. **Calcolo dei parametri:**
   - **$f_0$**: frequenza del vertice della campana lorentziana pura.
   - **$R_m$**: al vertice, la reattanza si annulla ($Z_m = R_m$), quindi:
     $$R_m = \frac{V_{\text{in}}}{|\vec{I}_m(f_0)|} = \frac{G_e \cdot V_{\text{in}}}{|V_{\text{out,mot}}(f_0)|}$$
   - **$Q$**: calcolato dalla larghezza di banda a $-3\,\text{dB}$ della campana ($|\vec{I}_m| = \frac{|\vec{I}_{m,\max}|}{\sqrt{2}}$):
     $$Q = \frac{f_0}{\Delta f_{-3\text{dB}}}$$
   - **$L_m$ e $C_m$**:
     $$L_m = \frac{Q \cdot R_m}{2\pi f_0}, \qquad C_m = \frac{1}{(2\pi f_0)^2 L_m} = \frac{1}{2\pi f_0 \cdot Q \cdot R_m}$$

---

#### APPROCCIO 2: Il Metodo del Ringdown Temporale (Ideale per il tuo lavoro!)
Visto che stai studiando il ringdown, questo metodo è una bomba perché **il ringdown elimina fisicamente $C_p$ da solo**!

1. Quando spegni il burst ($V_{\text{in}} = 0$), la corrente capacitiva $I_p = C_p \frac{dV_{\text{in}}}{dt}$ **crolla a zero istantaneamente**.
2. Il segnale sinusoidale che vedi decadere sull'oscilloscopio è **100% puro moto meccanico**.
3. Dai file scope del ringdown a $V_{\text{in}} = 100\,\text{mV}$ estrai:
   - **$f_0$**: frequenza naturale dell'oscillazione libera.
   - **$\tau$**: costante di tempo dell'inviluppo esponenziale $e^{-t/\tau}$.
     $$Q = \frac{\omega_0 \tau}{2} = \pi f_0 \tau$$
   - **$R_m$**: sapendo l'ampiezza stazionaria a regime $A_0$ prima dello stacco:
     $$R_m = \frac{G_e \cdot V_{\text{in}}}{A_0}$$
   - **$L_m$ e $C_m$**: con le stesse formule universali:
     $$L_m = \frac{Q R_m}{\omega_0}, \qquad C_m = \frac{1}{\omega_0^2 L_m}$$

---

#### APPROCCIO 3: Metodo Diretto dell'Antirisonanza (Cross-Check da Paper)
Se nello sweep vedi chiaramente la frequenza del picco ($f_s$) e la frequenza del minimo ($f_p$), la teoria BVD fornisce una relazione diretta che lega la distanza tra picco e buca al rapporto delle capacità:
$$\frac{f_p^2 - f_s^2}{f_s^2} \approx \frac{2(f_p - f_s)}{f_s} = \frac{C_m}{C_p}$$

Conoscendo $C_p$ (misurata a $V_{\text{DC}}=0$), ricavi $C_m$ **senza nemmeno dover conoscere il guadagno del TIA**:
$$\boxed{C_m = C_p \cdot \frac{2(f_p - f_s)}{f_s}}$$
Poi calcoli $L_m = \frac{1}{(2\pi f_s)^2 C_m}$ e $R_m = \frac{2\pi f_s L_m}{Q}$.

---

### 5. Strategia Consigliata per la Relazione ("Best Practice")

Per impostare la relazione in modo scientificamente inattaccabile, ti consiglio questa scaletta:

1. **Sezione 1: Modello Circuitale BVD**
   - Disegna lo schema: ramo $R_m-L_m-C_m$ in parallelo a $C_p$, collegato al TIA con $G_e = 1\,\text{M}\Omega$.
   - Spiega che $C_p$ è la somma delle capacità parassite di layout, package e gap statico.

2. **Sezione 2: Misura e Isolamento di $C_p$**
   - Mostra la misura a $V_{\text{DC}} = 0\,\text{V}$ (o fuori risonanza).
   - Mostra che la risposta è piatta e anticipata di $+90^\circ$ (o $-90^\circ$), confermando la natura puramente capacitiva.
   - Calcola numericamente $C_p$.

3. **Sezione 3: Caratterizzazione a $V_{\text{DC}} = 5\,\text{V}$ e $V_{\text{in}} = 100\,\text{mV}$**
   - Mostra la curva di risposta in frequenza asimmetrica reale (con picco a $f_s$ e minimo a $f_p$).
   - Spiega fisicamente perché c'è l'antirisonanza (il ramo motionale diventa induttivo sopra $f_s$ e cancella $C_p$).

4. **Sezione 4: De-Embedding Fasoriale e Ricavo di $R_m, L_m, C_m$**
   - Mostra il grafico **"Before & After"**: la curva asimmetrica grezza vs la curva simmetrica lorentziana ottenuta dopo aver sottratto il fasore $j\omega C_p V_{\text{in}}$.
   - Da questa estrai $f_0, Q, R_m, L_m, C_m$.

5. **Sezione 5: Validazione Incrociata con il Ringdown**
   - Fai una tabella di confronto:
     | Parametro | Valore da Sweep (Fasori) | Valore da Ringdown Temporale | Scostamento % |
     | :--- | :--- | :--- | :--- |
     | $f_0$ | ... kHz | ... kHz | < 0.1% |
     | $Q$ | ... | ... | ... |
     | $R_m$ | ... $\text{k}\Omega$ | ... $\text{k}\Omega$ | ... |
     | $L_m$ | ... H | ... H | ... |
     | $C_m$ | ... fF | ... fF | ... |
   - Mostrare che i parametri ricavati nel dominio della frequenza (sweep) e nel dominio del tempo (ringdown) coincidono dimostra la completa solidità del tuo modello.