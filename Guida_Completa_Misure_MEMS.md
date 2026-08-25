# Guida Completa e Rigorosa alla Caratterizzazione del Risonatore MEMS ad Arco

Questo documento raccoglie in dettaglio tutte le procedure sperimentali, la trattazione matematica, i modelli circuitali equivalenti e le considerazioni fisiche emerse durante la discussione per la caratterizzazione completa del risonatore capacitivo ad arco in polisilicio ($f_{r1} \approx 416.6\text{ kHz}$, $Q \approx 2800$).

---

# 1. Modello Fisico ed Elettromeccanico di Riferimento

Il risonatore è costituito da travi curve (*arch beams*) incapsulate in atmosfera di Argon a bassa pressione ($\approx 70\text{ mbar}$).
L'equazione dinamica linearizzata del primo modo attorno alla posizione di equilibrio vale:

$$\ddot{q}_1 + \frac{\omega_{01}}{Q_1}\dot{q}_1 + \left(c_{1,\beta}^{(1)} - c_{1,\text{DD}}^{(1)} V_{\text{DC}}^2\right) q_1 = 2 c_{0,\text{DA}}^{(1)} V_{\text{DC}} v_{\text{in}}(t)$$

Dove:
- $q_1(t)$ è la coordinata modale dello spostamento (in $\mu\text{m}$ o $\text{m}$).
- $c_{1,\beta}^{(1)}$ è la rigidezza elastica lineare del silicio ($\approx 6.85\,\mu\text{s}^{-2}$).
- $c_{1,\text{DD}}^{(1)} V_{\text{DC}}^2$ è il termine di **Electrostatic Softening** (molla negativa elettrostatica).
- $2 c_{0,\text{DA}}^{(1)} V_{\text{DC}}$ è il coefficiente di trasduzione elettromeccanica d'attuazione $\alpha_d$.
- La corrente di lettura al sensore vale $i_S(t) = c_{0,\text{DA}}^{(1)} V_{\text{DC}} \dot{q}_1(t) = \alpha_s \dot{q}_1(t)$.

---

# 2. Caratterizzazione in Frequenza: Softening vs Duffing

### 2.1 Softening Elettrostatico ($f_0$ vs $V_{\text{DC}}$)
* **Principio Fisico:** La forza elettrostatica capacitiva è attrattiva e aumenta al diminuire della distanza tra le armature ($F_e \propto \frac{V_{\text{DC}}^2}{(g_0 - x)^2}$). La derivata $\frac{\partial F_e}{\partial x} > 0$ agisce nello stesso verso dello spostamento, riducendo la rigidezza totale:
  $$k_{\text{eff}}(V_{\text{DC}}) = c_{1,\beta}^{(1)} - c_{1,\text{DD}}^{(1)} V_{\text{DC}}^2$$
* **Comportamento della Campana:** **Non è il lato sinistro della curva**, ma è l'**intera campana lorentziana** che trasla rigidamente a frequenze più basse mantenendo una forma simmetrica a basso segnale:
  $$f_0(V_{\text{DC}}) = \frac{1}{2\pi}\sqrt{c_{1,\beta}^{(1)} - c_{1,\text{DD}}^{(1)} V_{\text{DC}}^2} \approx f_{0,0} \left(1 - \frac{c_{1,\text{DD}}^{(1)}}{2 c_{1,\beta}^{(1)}} V_{\text{DC}}^2\right)$$
* **Procedura di Misura:**
  1. Fissa $V_{\text{in}} = 50\text{ mV}_{\text{rms}}$ (regime di piccolo segnale).
  2. Varia $V_{\text{DC}} \in [1\text{ V}, 6\text{ V}]$ a passi di $1\text{ V}$.
  3. Per ciascun valore, esegui uno sweep di frequenza attorno a $416\text{ kHz}$ e trova il picco $f_0$.
  4. Costruisci il grafico $f_0^2$ vs $V_{\text{DC}}^2$: la pendenza della retta fornisce direttamente il parametro $c_{1,\text{DD}}^{(1)}$.

---

### 2.2 Effetto Duffing e Non Linearità Geometriche ($f_0$ e Ampiezza vs $V_{\text{AC}}$)
* **Principio Fisico:** Quando l'ampiezza di vibrazione cresce a causa di un'elevata tensione alternata $V_{\text{in}}$, la forza di richiamo elastica include un termine cubico: $\beta(q_1) = c_1 q_1 + c_6 q_1^3$.
  - **Duffing Hardening ($c_6 > 0$):** Prevale lo stiramento assiale delle travi (*mid-plane stretching*); la struttura diventa più rigida con l'ampiezza e la campana si piega a **destra** (la frequenza di picco sale).
  - **Duffing Softening ($c_6 < 0$):** Prevale la curvatura iniziale dell'arco o l'attrazione elettrostatica; la campana si piega a **sinistra** (la frequenza di picco scende).
* **Fenomeno dell'Isteresi e dei Salti (*Jump Phenomenon*):**
  A causa della piegatura della curva, per una data frequenza possono esistere due ampiezze stabili e una instabile.
  - **Sweep-Up (in salita):** Il sistema segue il ramo superiore fino al bordo estremo della curva, per poi crollare bruscamente verso il basso (*Jump-Down*).
  - **Sweep-Down (in discesa):** Il sistema risale da frequenze alte lungo il ramo basso e poi salta bruscamente verso l'alto (*Jump-Up*) a una frequenza diversa.
* **Procedura di Misura:**
  1. Fissa $V_{\text{DC}} = 4\text{ V}$.
  2. Imposta diversi livelli di $V_{\text{in}}$ (es. $50\text{ mV}, 100\text{ mV}, 250\text{ mV}, 500\text{ mV}, 1000\text{ mV}$).
  3. Per ciascuna ampiezza, effettua uno sweep in salita seguito da uno in discesa.
  4. Registra l'area di isteresi e l'evoluzione della *Backbone Curve*.

---

# 3. Dinamica del Decadimento Libero (Ringdown & Gate Cutoff)

### 3.1 Dipendenza dell'Ampiezza Iniziale $A_0$ da $V_{\text{DC}}$, $V_{\text{in}}$ e $f_{\text{ecc}}$
Allo spegnimento del gate ($v_{\text{in}} \to 0$), il moto libero obbedisce a:
$$q_1(t) = q_0 e^{-t/\tau} \cos(\omega_r t + \varphi_0), \qquad \tau = \frac{2 Q_1}{\omega_{01}} \approx 2.14\text{ ms}$$
- **Scalatura quadratica con $V_{\text{DC}}$:** Poiché la forza motrice vale $F \propto V_{\text{DC}} V_{\text{in}}$ e la corrente generata vale $i_S \propto V_{\text{DC}} \dot{q}$, la tensione letta all'oscilloscopio scala come:
  $$\mathbf{V_{\text{out}}(0) \propto V_{\text{DC}}^2 \cdot V_{\text{in}}}$$
- **Eccitazione fuori risonanza ($f_{\text{ecc}} \neq f_0$):** Se il gate viene staccato mentre il risonatore è forzato fuori risonanza, l'ampiezza iniziale $A_0$ è ridotta secondo la funzione di risposta in frequenza. Tuttavia, nell'istante in cui $v_{\text{in}} = 0$, il risonatore **cessa di oscillare a $f_{\text{ecc}}$ e vibra unicamente alla propria frequenza naturale $f_0$**.

---

### 3.2 Ruolo dell'Angolo di Fase di Stacco $\phi$ (Cutoff Phase)
L'istante di spegnimento $t_{\text{off}}$ corrisponde a una precisa fase dell'onda $\phi = \omega_{\text{ecc}} t_{\text{off}} \pmod{2\pi}$:
- **$\phi = 90^\circ$ (Picco di velocità, Spostamento nullo):** Tutta l'energia iniziale del ringdown è immagazzinata come energia cinetica; la corrente motrice parte dal valore massimo.
- **$\phi = 0^\circ$ o $180^\circ$ (Picco di spostamento, Velocità nulla):** Tutta l'energia è potenziale elastica; la corrente motrice attraversa lo zero. Tuttavia, la commutazione brusca della tensione applicata crea una discontinuità a gradino che inietta un transiente parassita attraverso la capacità di feedthrough $C_p$.
- **Costante di tempo $\tau$:** L'inviluppo del decadimento intrinseco $\tau = \frac{2Q}{\omega_0}$ è indipendente da $\phi$, ma la fase iniziale dell'oscillazione libera e la risposta del TIA dipendono da $\phi$.

---

# 4. Misura Sperimentale Diretta dei Parametri del Modello RLC (BVD)

Il circuito equivalente Butterworth-Van Dyke (BVD) è rappresentato da un ramo motionale in parallelo alla capacità statica/parassita $C_p$:

```
                       +---[ Lm ]---[ Rm ]---[ Cm ]---+
                       |        (Ramo Motionale)      |
    Vin (Gen) o--------+                              +--------o I_tot (al TIA)
                       |        (Ramo Parassita)      |
                       +-------------[ Cp ]------------+
```

L'impedenza motionale è:
$$Z_m(f) = R_m + j \cdot X_m(f) = R_m + j \left(2\pi f L_m - \frac{1}{2\pi f C_m}\right)$$

```
     f < f0                    f = f0                   f > f0
(Effetto Capacitivo)        (Risonanza Serie)     (Effetto Induttivo)
1/(wC) >> wL                  wL = 1/(wC)             wL >> 1/(wC)
Reattanza Negativa          Reattanza = 0         Reattanza Positiva
Corrente in ANTICIPO (+90°)  Corrente in FASE (0°) Corrente in RITARDO (-90°)
```

Poiché $Q \approx 2800$, la banda passante è strettissima ($\Delta f = \frac{f_0}{Q} \approx \frac{416.600}{2800} \approx 150\text{ Hz}$):
- A **$+300\text{ Hz}$ sopra $f_0$** il ramo motionale si comporta come un'**induttanza pura $L_m$**.
- A **$-300\text{ Hz}$ sotto $f_0$** il ramo motionale si comporta come una **capacità pura $C_m$**.

---

### 4.1 La Sottrazione Vettoriale della Capacità Parassita $C_p$

La corrente totale misurata all'ingresso del TIA è la somma vettoriale di due contributi con fasi differenti:
$$\vec{I}_{\text{tot}} = \vec{I}_m + \vec{I}_p$$
- $\vec{I}_p = j \omega C_p \vec{V}_{\text{in}}$ è la corrente parassita, sempre in anticipo fisso di **$+90^\circ$**.
- $\vec{I}_m$ è la corrente motionale del silicio, che sopra risonanza è in ritardo (es. $-70^\circ$).

Per isolare il vero valore di $L_m$ o $C_m$ senza distorsioni da parte dei cavi:
1. Si misura $\vec{I}_p$ ponendo $V_{\text{DC}} = 0\text{ V}$ (silicio fermo $\implies \vec{I}_m = 0$).
2. Si misura $\vec{I}_{\text{tot}}$ con $V_{\text{DC}} = 4\text{ V}$.
3. Si esegue la sottrazione complessa: $\vec{I}_m = \vec{I}_{\text{tot}} - \vec{I}_p$.

---

### 4.2 Procedura Pratica di Misura Passo-Passo

#### Step 1: Misura di $C_p$
- Imposta $V_{\text{DC}} = 0\text{ V}$.
- Invia una sinusoide $V_{\text{in}} = 1\text{ V}_{\text{pk}}$ a $f = 50\text{ kHz}$ (lontano da risonanza).
- Misura la tensione in uscita dal TIA $V_{\text{out}, p}$ (sfasata di $+90^\circ$):
  $$C_p = \frac{V_{\text{out}, p}}{2\pi f \cdot G_e \cdot V_{\text{in}}}$$

#### Step 2: Misura di $R_m$ alla Risonanza Serie $f_0$
- Imposta $V_{\text{DC}} = 4\text{ V}$ e $V_{\text{in}} = 100\text{ mV}_{\text{pk}}$.
- Trova la frequenza $f_s \approx 416.6\text{ kHz}$ dove l'uscita $V_{\text{out}}$ è massima e in fase ($0^\circ$).
- Calcola:
  $$R_m = \frac{V_{\text{in}} \cdot G_e}{V_{\text{out, res}}}$$

#### Step 3: Misura Diretta di $L_m$ (Spostamento SOPRA risonanza)
- Imposta $f_2 = f_0 + 300\text{ Hz} = 416.900\text{ Hz}$.
- A $V_{\text{DC}} = 0\text{ V}$, leggi ampiezza e fase della parassita: $\vec{I}_p = I_{p0} e^{j 90^\circ}$.
- A $V_{\text{DC}} = 4\text{ V}$, leggi ampiezza e fase totale: $\vec{I}_{\text{tot}} = I_{\text{tot}0} e^{j \theta_{\text{tot}}}$.
- Calcola $\vec{I}_m = \vec{I}_{\text{tot}} - \vec{I}_p = |\vec{I}_m| e^{j \theta_m}$.
- Calcola la reattanza induttiva $X_L = \frac{V_{\text{in}}}{|\vec{I}_m|} \sin(-\theta_m)$.
- Ricava l'induttanza motionale:
  $$\mathbf{L_m = \frac{X_L}{2\pi f_2}}$$

#### Step 4: Misura Diretta di $C_m$ (Spostamento SOTTO risonanza)
- Imposta $f_1 = f_0 - 300\text{ Hz} = 416.300\text{ Hz}$.
- Esegui la medesima sottrazione vettoriale per ottenere $\vec{I}_m$ (che avrà fase $\theta_m > 0$).
- Calcola la reattanza capacitiva $X_C = \frac{V_{\text{in}}}{|\vec{I}_m|} \sin(\theta_m)$.
- Ricava la capacità motionale:
  $$\mathbf{C_m = \frac{1}{2\pi f_1 X_C}}$$

---

### 4.3 Esempio Numerico e Script Python per l'Elaborazione Dati

```python
import numpy as np

# Parametri del setup
f_meas = 416900.0          # Frequenza a f0 + 300 Hz
Vin = 0.20                 # Tensione di eccitazione (200 mVpk)
Ge = 1.0e6                 # Guadagno TIA (1 MOhm = 1 V/uA)

# 1. Dati misurati all'oscilloscopio a Vdc = 0V
Vout_0 = 0.16e-3           # 0.16 mVpk
phase_0_deg = 90.0         # Corrente parassita pura a +90°
I_p = (Vout_0 / Ge) * np.exp(1j * np.deg2rad(phase_0_deg))

# 2. Dati misurati all'oscilloscopio a Vdc = 4V
Vout_4V = 1.79e-3          # 1.79 mVpk
phase_4V_deg = -68.1       # Corrente totale in ritardo di -68.1°
I_tot = (Vout_4V / Ge) * np.exp(1j * np.deg2rad(phase_4V_deg))

# 3. Sottrazione Vettoriale del Feedthrough
I_m = I_tot - I_p

# 4. Calcolo Impedenza, Reattanza e Induttanza Lm
Z_m = Vin / I_m
X_L = np.imag(Z_m)
L_m = X_L / (2 * np.pi * f_meas)
C_m = 1.0 / ((2 * np.pi * 416600)**2 * L_m)

print(f"Corrente Motionale Pura: |Im| = {np.abs(I_m)*1e9:.3f} nA, Fase = {np.angle(I_m, deg=True):.2f}°")
print(f"Reattanza Induttiva XL:  {X_L/1e6:.2f} MOhm")
print(f"Induttanza Lm misurata:  {L_m/1e3:.2f} kH")
print(f"Capacita Cm ricavata:    {C_m*1e18:.4f} aF  ({C_m*1e15:.4f} fF)")
```

---

# 5. Misure Avanzate ad Alto Impatto Scientifico

### 5.1 Risonanza Interna 1:2 e Frequency Combs (Frangi 2023, Nastro 2026)
- **Principio:** La frequenza del secondo modo è quasi il doppio del primo ($f_{r2} \approx 834\text{ kHz} \approx 2 f_{r1}$).
- **Metodo:** Si applica $V_{\text{DC}} = 5\text{ V}$ e si incrementa $V_{\text{AC}}$ a $f_{r1}$. Oltre una soglia critica, l'energia travasa nel secondo modo originando uno stato quasi-periodico e un pettine denso di righe spettrali (*frequency combs*), osservabile con FFT ad alta risoluzione.

### 5.2 Soppressione Attiva del Ringdown via Impulso di Coda (Wu et al. 2021)
- **Principio:** Il ringdown naturale dura circa $4.92\text{ ms}$. Generando tramite AWG un burst di eccitazione seguito immediatamente da un impulso di controtensione a fase invertita ($180^\circ$) e durata calibrata, si estrae l'energia cinetica residua, riducendo il tempo di estinzione a meno di $0.3\text{ ms}$.

### 5.3 STFT Spettrogramma Dinamico del Ringdown
- **Principio:** Durante il decadimento libero, la non linearità geometrica fa variare la frequenza istantanea $f_{\text{inst}}(t)$ mentre l'ampiezza diminuisce. La Short-Time Fourier Transform permette di quantificare sperimentalmente la deriva di frequenza istantanea.

### 5.4 Diagramma di Nyquist dell'Ammettenza ($G-B$ Plot)
- **Principio:** Nel piano complesso $\text{Re}\{Y\}$ (conduttanza) vs $\text{Im}\{Y\}$ (suscettanza), il risonatore descrive una circonferenza perfetta con diametro $1/R_m$, traslata sull'asse verticale di $\omega_s C_p$.
