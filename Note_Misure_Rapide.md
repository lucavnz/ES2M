# appunti rapidi misure mems - lista cose da fare

ecco la lista veloce e informale di tutte le misure e prove da fare al banco per la caratterizzazione del mems:

- **misura softening elettrostatico (f0 vs vdc):**
  - metto vin ac bassa (tipo 50mv) per stare lineare
  - vario vdc a passi (1v, 2v, 3v, 4v, 5v, 6v)
  - faccio sweep attorno a 416khz e prendo il picco di f0
  - f0 scende con vdc^2 perche la forza elettrostatica fa da molla negativa (non e il lato sinistro della campana ma e tutta la campana che trasla a sinistra)
  - plotto f0^2 vs vdc^2 e trovo la costante c1_DD

- **misura effetto duffing e non linearita (f0 e ampiezza vs vin ac):**
  - tengo vdc fissa (tipo 4v o 5v)
  - aumento vin ac (50mv, 100mv, 200mv, 500mv, 1v)
  - per ogni vin faccio due sweep: uno in salita (sweep-up) e uno in discesa (sweep-down)
  - a vin alto la campana si deforma e diventa a pinna di squalo, piegata a sinistra (softening) o destra (hardening)
  - vedo l'isteresi con i salti improvvisi di ampiezza (jump down quando salgo, jump up quando scendo)

- **misura ampiezza iniziale decadimento a0 a gate spento (vt=0):**
  - eccito con burst e poi stacco il gate mandando vin a 0
  - l'ampiezza iniziale del segnale letto in uscita scala come vdc^2 * vin (perche forza ~ vdc*vin e lettura corrente ~ vdc*velocita)
  - se eccito fuori risonanza e poi stacco il gate, appena stacco il mems se ne frega della frequenza forzata e salta istantaneamente a vibrare alla sua f0 naturale

- **misura effetto angolo di stacco phi (cutoff phase):**
  - cambio l'istante in cui stacco il gate rispetto alla sinusoide
  - a phi = 90 gradi stacco sul picco di velocita (energia tutta cinetica, corrente max)
  - a phi = 0 o 180 gradi stacco sul picco di spostamento (energia elastica, ma gradino di tensione che da un picco capacitivo di feedthrough sui fili)
  - il tau del ringdown resta uguale, ma cambia la fase iniziale e il disturbo sui fili

- **misura della capacita parassita Cp (feedthrough dei cavi/pad):**
  - metto vdc = 0v (il mems e fermo, niente moto)
  - inietto sinusoide a frequenza bassa (tipo 50khz) con ampiezza nota (es 1v)
  - misuro l'uscita del tia: la corrente e tutta e solo Ip = w * Cp * Vin con fase +90 gradi
  - calcolo Cp = Vout / (w * Ge * Vin)

- **misura resistenza motionale Rm a risonanza:**
  - metto vdc = 4v e vin = 100mv
  - mi metto preciso su f0 (416.6khz) dove lo sfasamento tra vin e vout e 0 gradi (i_m e in fase)
  - l'induttanza Lm e la capacita Cm si annullano a vicenda
  - Rm = Vin / Ires = (Vin * Ge) / Vout

- **misura fattore di qualita Q e tau dal ringdown:**
  - faccio burst a f0 e poi stacco a 0v
  - registro il decadimento su oscilloscopio
  - inviluppo esponenziale A(t) = A0 * exp(-t/tau)
  - ricavo tau (~2.14ms) e calcolo Q = pi * f0 * tau (~2800)

- **misura DIRETTA di Lm (frequenza sopra risonanza):**
  - mi sposto a f0 + 300hz (es 416.9khz) dove vince l'inerzia/induttanza del silicio
  - la corrente va in ritardo rispetto alla tensione
  - misuro modulo e fase con vdc=0 (solo Cp) e con vdc=4v (totale)
  - sottraggo vettorialmente Cp per avere la corrente motionale pura Im
  - calcolo la reattanza induttiva XL = |Zm| * sin(theta) e trovo Lm = XL / (2*pi*f) (~37 kH)

- **misura DIRETTA di Cm (frequenza sotto risonanza):**
  - mi sposto a f0 - 300hz (es 416.3khz) dove vince l'elasticita/capacita del silicio
  - la corrente va in anticipo rispetto alla tensione
  - sottraggo vettorialmente la Cp
  - calcolo la reattanza capacitiva XC e trovo Cm = 1 / (2*pi*f*XC) (~0.0038 fF)

- **misura avanzata 1: risonanza interna 1:2 e pettini di frequenza (paper frangi/nastro):**
  - pompo vin ac forte a 416khz con vdc=5v
  - guardo su fft o analizzatore di spettro
  - sopra una soglia di vin parte il secondo modo a 834khz e nascono i frequency combs con righe fitte attorno al picco

- **misura avanzata 2: soppressione attiva del ringdown con contropolso (paper wu):**
  - da awg creo burst di eccitazione + subito dopo un impulso di frenata sfasato di 180 gradi
  - regolo la durata del contropolso
  - vedo il ringdown crollare da 4.9ms a meno di 0.3ms (elimino la blind area)

- **misura avanzata 3: spettrogramma STFT durante il decadimento:**
  - prendo il ringdown raw e faccio la stft in python
  - vedo che all'inizio quando l'ampiezza e alta la frequenza e leggermente shiftata per il duffing, poi scivola verso la f0 lineare man mano che il segnale si spegne

- **misura avanzata 4: diagramma di nyquist dell'ammettenza (G-B plot):**
  - plotto parte reale vs parte immaginaria dell'ammettenza al variare di f
  - viene un cerchio perfetto traslato verso l'alto di w*Cp
  - diametro del cerchio = 1/Rm
