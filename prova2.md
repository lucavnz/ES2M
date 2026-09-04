Questa misura è **fondamentale e affascinante**: è esattamente il modo in cui nella ricerca d'avanguardia sui MEMS si caratterizza la **non-linearità di Duffing** sfruttando il ringdown!

Ecco una spiegazione chiara, fisica e intuitiva di **cosa succede**, di **cosa vedremo** e di **tutti i grafici spettacolari che potremo estrarre dai file scope**.

---

### 1. La Fisica: Cosa succede aumentando $V_{\mathrm{in}}$ da $40\,\mathrm{mV}$ a $1000\,\mathrm{mV}$?

Nel regime lineare (quello che abbiamo visto finora a $100\,\mathrm{mV}$), la molla del risonatore rispetta la legge di Hooke ($F = -k x$). La frequenza di risonanza non dipende dall'ampiezza dell'oscillazione.

Quando aumenti la tensione di eccitazione ($V_{\mathrm{in}} \ge 200 \div 300\,\mathrm{mV}$ fino a $1\,\mathrm{V}$):
1. **Grandi Spostamenti Meccanici**: la trave vibra con ampiezze di deformazione non più trascurabili rispetto al gap capacitivo $g_0$.
2. **Forza Cubica di Duffing**: la forza di richiamo diventa non lineare:
   $$F(x) = - k_1 x - k_3 x^3$$
   Nei MEMS capacitivi con $V_{\mathrm{DC}} = 5\,\mathrm{V}$, l'elettrostatica produce una non-linearità cubica negativa (**Softening**, $k_3 < 0$).
3. **Piegamento della Risonanza**: la curva di risonanza si "piega" verso sinistra (verso frequenze più basse). Più l'ampiezza è grande, più la frequenza a cui il risonatore vorrebbe vibrare scende:
   $$f_{\mathrm{res}}(A) \approx f_s(0) + \beta \cdot A^2 \quad (\text{con } \beta < 0 \text{ in caso di softening})$$

---

### 2. Perché la relazione Ampiezza Ringdown vs $V_{\mathrm{in}}$ NON sarà più lineare?

Se tieni **fissa** la frequenza del generatore a $f_{\mathrm{in}} = 417850\,\mathrm{Hz}$ (che è la risonanza a piccolo segnale) e aumenti $V_{\mathrm{in}}$:

- **A basse tensioni ($40 \div 150\,\mathrm{mV}$)**: la risonanza è simmetrica e non si è ancora spostata. Il sistema risponde linearmente: raddoppiando $V_{\mathrm{in}}$, l'ampiezza iniziale del ringdown $A_0$ raddoppia ($A_0 \propto V_{\mathrm{in}}$).
- **Ad alte tensioni ($250 \div 1000\,\mathrm{mV}$)**: man mano che la trave si muove di più, la sua frequenza di risonanza effettiva si sposta verso il basso (es. scende a $417.80\,\mathrm{kHz}$ o $417.75\,\mathrm{kHz}$).
  Di conseguenza, alla frequenza fissa del generatore ($417850\,\mathrm{Hz}$), il generatore **non si trova più sul vertice della campana**, ma si trova sul fianco destro!
- **Effetto Sperimentale**: l'ampiezza $A_0$ **satura / comprime** (*Gain Compression*). Invece di continuare a salire su una retta, la curva $A_0$ vs $V_{\mathrm{in}}$ devia verso il basso e si appiattisce.

```
A0 [mV]
  ^
  |          /  Retta ideale lineare (piccolo segnale)
  |         /
  |        /  . - - - Curva reale con Duffing (Compressione di guadagno)
  |       /. '
  |      /'
  |     /
  |    /
  |   /
  +------------------------> Vin [mV]
     40   150   300   600   1000
```

---

### 3. La Magia del Ringdown: Estrarre la "Backbone Curve" in un colpo solo!

Questa è la parte più elegante del metodo. Normalmente, per tracciare la non-linearità di Duffing bisognerebbe fare sweep in frequenza avanti e indietro a ogni ampiezza per vedere l'isteresi e il piegamento.

**Con il ringdown è molto più facile**:
Durante il ringdown, il generatore esterno è **SPENTO** ($V_{\mathrm{in}} = 0$). Il risonatore è lasciato libero di oscillare da solo:
- All'istante iniziale ($t = 0$), l'ampiezza $A(t) = A_0$ è massima, quindi la frequenza naturale istantanea è abbassata al massimo: $f_{\mathrm{inst}}(0) = f_s(0) - |\Delta f_{\mathrm{Duffing}}|$.
- Man mano che l'oscillazione decade per attrito ($A(t) = A_0 e^{-t/\tau} \to 0$), l'ampiezza diminuisce.
- Diminuendo l'ampiezza, l'effetto non lineare svanisce progressivamente e la frequenza istantanea **risale verso la frequenza lineare $f_s(0)$**!

Questo fenomeno si chiama **Chirp intra-ringdown**:
Analizzando un singolo file ad alta tensione (es. $V_{\mathrm{in}} = 1000\,\mathrm{mV}$), tramite la fase analitica istantanea $\phi(t)$ tracciamo punto per punto la coppia:
$$\big(f_{\mathrm{inst}}(t),\, A(t)\big)$$
Questo traccia l'intera **Backbone Curve** (la "spina dorsale" della risonanza non lineare di Duffing) da un singolo file!

---

### 4. Cosa potremo plottare (I 4 Grafici che realizzeremo)

Quando farai la misura con i tuoi punti ($40, 60, 80, 100, 120, 150, 180, 210, 250, 300, 350, 400, 500, 600, 750, 1000\,\mathrm{mV}$), scriverò uno script dedicato per generare:

#### Grafico 1: Linearità vs Compressione ($A_0$ vs $V_{\mathrm{in}}$)
- **Asse X**: Tensione applicata $V_{\mathrm{in}}$ [mV].
- **Asse Y**: Ampiezza iniziale del ringdown $A_0$ [mV].
- Mostrerà:
  1. Il fit lineare a piccolo segnale ($40 \div 150\,\mathrm{mV}$) con calcolo della sensibilità / guadagno $\frac{\mathrm{d}A_0}{\mathrm{d}V_{\mathrm{in}}}$ [mV/mV].
  2. La deviazione non lineare ad alte tensioni.
  3. Il punto di compressione a $-1\,\mathrm{dB}$ (il punto in cui il risonatore perde linearità del 10%).

#### Grafico 2: Spostamento di Frequenza vs Ampiezza (Curva di Duffing)
- **Asse X**: Ampiezza iniziale $A_0$ (o $V_{\mathrm{in}}$).
- **Asse Y**: Frequenza di oscillazione iniziale $f_s(A_0)$.
- Mostrerà direttamente la parabola di Duffing:
  $$f_s(A_0) = f_0 + \beta A_0^2$$
  da cui ricaveremo direttamente il **coefficiente non lineare cubico $\alpha$ (o $\beta$)** del dispositivo.

#### Grafico 3: La "Backbone Curve" Universale
- Plottiamo su uno stesso grafico la traiettoria ampiezza istantanea vs frequenza istantanea $A(t)$ vs $f_{\mathrm{inst}}(t)$ estratta da tutti i file.
- Tutte le curve, partendo da altezze diverse ($40\,\mathrm{mV}, 100\,\mathrm{mV}, 500\,\mathrm{mV}, 1000\,\mathrm{mV}$), **collasseranno e scivoleranno lungo la medesima curva universale** (lo scheletro di risonanza).

#### Grafico 4: Spettrogrammi STFT a Cascata
- Visualizzazione tempo-frequenza a confronto: a $40\,\mathrm{mV}$ la riga spettrale è dritta come una lama; a $1000\,\mathrm{mV}$ la riga spettrale parte piegata a sinistra e si raddrizza man mano che il segnale decade!

#### Grafico 5: Stabilità del Fattore di Qualità $Q(V_{\mathrm{in}})$
- Verificheremo se lo smorzamento rimane lineare ($\tau$ costante) o se a grandi oscillazioni compare anche uno smorzamento non lineare (ad esempio per perdite viscose d'aria ad alta velocità).

---

### 5. Consigli Pratici Fondamentali PRIMA di fare la Misura all'Oscilloscopio

1. **Attenzione alla scala verticale (clipping durante il ringdown)**:
   - A $V_{\mathrm{in}} = 1000\,\mathrm{mV}$, l'uscita durante il burst sarà molto grande (potrebbe raggiungere $300 \div 500\,\mathrm{mV}$ o più).
   - Se l'oscilloscopio taglia durante il burst va benissimo (lo abbiamo già gestito col blanking).
   - **IMPORTANTE**: assicurati che **il ringdown non tagli**! Cioè appena stacca il gate, la parte sinusoidale del decadimento deve entrare completamente nello schermo verticale dell'oscilloscopio, altrimenti il fit dell'ampiezza iniziale $A_0$ verrebbe falsato.
2. **Saturazione del TIA**:
   - Assicurati che l'amplificatore a transimpedenza (TIA) o il buffer non vada a sbattere contro le tensioni di alimentazione (rail), altrimenti il tempo di recupero (*recovery time*) potrebbe allungare il transitorio iniziale. Se vedi che il TIA satura a lungo, basterà aumentare leggermente il nostro blanking.
3. **Frequenza del Generatore**:
   - Tieni fisso $f_{\mathrm{in}} = 417850\,\mathrm{Hz}$ esattamente come hai proposto. È la scelta perfetta.

Quando sei pronto con i file delle misure, dimmi i nomi dei file e la lista delle tensioni associate: prepareremo subito la nuova suite in una cartella dedicata (es. `Analisi_Duffing/`) con tutti questi grafici!