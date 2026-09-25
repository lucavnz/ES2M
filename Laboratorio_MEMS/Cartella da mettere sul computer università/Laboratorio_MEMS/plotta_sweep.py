"""
Visualizzatore e Fit per Dati Sweep MEMS
Funziona su qualsiasi computer:
  1. Su Python Minimale/Portatile (senza librerie esterne):
     - Estrae istantaneamente tutti i punti da qualsiasi CSV
     - Calcola picco di risonanza e minimo di antirisonanza
     - Genera un visualizzatore HTML interattivo moderno (apribile offline su Edge/Chrome)
     - Apre automaticamente il grafico nel browser
  2. Su Python Completo (con numpy, scipy, matplotlib):
     - Esegue anche il de-embedding analitico BVD (campana lorentziana pura + transizione 180 deg)
     - Genera e apre l'immagine PNG a 4 quadranti per la relazione
"""

import os
import sys
import glob
import csv
import math

def elabora_file(filepath):
    filepath = os.path.abspath(filepath)
    if not os.path.exists(filepath):
        print(f"[ERRORE] File non trovato: {filepath}")
        return

    print("=" * 75)
    print(f" CARICAMENTO ED ELABORAZIONE: {os.path.basename(filepath)}")
    print("=" * 75)

    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        rows = [r for r in reader if r and not r[0].startswith('#')]

    if len(rows) < 2:
        print("[ERRORE] File CSV vuoto o contenente solo intestazione.")
        return

    data_rows = rows[1:]

    freqs = []
    vins = []
    vouts = []
    gains = []
    phases = []

    for r in data_rows:
        try:
            f_val = float(r[1])
            vin_val = float(r[3])
            vout_val = float(r[4])
            g_val = float(r[5])
            p_val = float(r[7])
            if not math.isnan(f_val) and not math.isnan(g_val) and not math.isnan(p_val):
                freqs.append(f_val)
                vins.append(vin_val)
                vouts.append(vout_val)
                gains.append(g_val)
                phases.append(p_val)
        except (ValueError, IndexError):
            continue

    n_pts = len(freqs)
    if n_pts < 5:
        print("[ERRORE] Punti validi insufficienti per tracciare il grafico.")
        return

    f_min, f_max = freqs[0], freqs[-1]
    g_min, g_max = min(gains), max(gains)
    p_min, p_max = min(phases), max(phases)
    vin_mean = sum(vins) / n_pts

    idx_peak = gains.index(g_max)
    idx_dip = gains.index(g_min)
    f_peak = freqs[idx_peak]
    f_dip = freqs[idx_dip]

    print(f"  * Punti Acquisiti    : {n_pts}")
    print(f"  * Intervallo Freq   : da {f_min/1e3:.3f} kHz a {f_max/1e3:.3f} kHz")
    print(f"  * Tensione Vin media: {vin_mean*1e3:.1f} mVpp")
    print(f"  * Range Guadagno    : min={g_min:.3f} V/V ({20*math.log10(max(1e-6, g_min)):.2f} dB), max={g_max:.3f} V/V ({20*math.log10(max(1e-6, g_max)):.2f} dB)")
    print(f"  * Range Sfasamento  : min={p_min:.2f} deg, max={p_max:.2f} deg")
    print(f"\n  --> Picco Risonanza (fs):    f = {f_peak:,.1f} Hz (Gain = {g_max:.3f} V/V)")
    print(f"  --> Minimo Antirisonanza (fp): f = {f_dip:,.1f} Hz (Gain = {g_min:.3f} V/V)")
    print(f"  --> Separazione Delta f:     {abs(f_dip - f_peak):.1f} Hz")

    # 1. Generazione Report Interattivo HTML (Funziona ovunque al 100%, zero librerie esterne)
    out_html = os.path.splitext(filepath)[0] + "_bode_interattivo.html"
    try:
        pts_json = []
        for fi, vi, vo, gi, pi in zip(freqs, vins, vouts, gains, phases):
            gdb = 20.0 * math.log10(max(1e-9, gi))
            pts_json.append(f'{{"f":{fi:.2f},"fk":{fi/1e3:.3f},"vin":{vi*1e3:.1f},"vout":{vo*1e3:.1f},"g":{gi:.4f},"gdb":{gdb:.2f},"p":{pi:.2f}}}')

        html_code = f"""<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Bode MEMS - {os.path.basename(filepath)}</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
  * {{ box-sizing: border-box; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background: #0b1120; color: #f1f5f9; margin: 0; padding: 24px; }}
  .container {{ max-width: 1250px; margin: 0 auto; }}
  .header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #1e293b; padding-bottom: 16px; margin-bottom: 24px; }}
  h1 {{ font-size: 22px; font-weight: 700; color: #38bdf8; margin: 0 0 6px 0; }}
  .file-badge {{ font-family: monospace; font-size: 13px; color: #94a3b8; }}
  .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 14px; margin-bottom: 24px; }}
  .card {{ background: #1e293b; border-radius: 8px; padding: 14px 18px; border: 1px solid #334155; }}
  .card-label {{ font-size: 12px; font-weight: 600; text-transform: uppercase; color: #64748b; margin-bottom: 4px; }}
  .card-val {{ font-size: 18px; font-weight: 700; color: #f8fafc; }}
  .card-val.cyan {{ color: #38bdf8; }}
  .card-val.orange {{ color: #fb923c; }}
  .card-val.green {{ color: #4ade80; }}
  .chart-box {{ background: #1e293b; border-radius: 10px; padding: 20px; border: 1px solid #334155; margin-bottom: 22px; }}
  .chart-title {{ font-size: 15px; font-weight: 600; color: #e2e8f0; margin-bottom: 12px; }}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <div>
      <h1>Diagramma di Bode Sperimentale - Risonatore MEMS</h1>
      <div class="file-badge">File: {os.path.basename(filepath)}</div>
    </div>
    <div style="text-align: right; color: #94a3b8; font-size: 13px;">
      Acquisizione Coerente (Lock-In Software)<br><b>{n_pts} punti misurati</b>
    </div>
  </div>

  <div class="stats-grid">
    <div class="card">
      <div class="card-label">Picco Risonanza (fs)</div>
      <div class="card-val cyan">{f_peak:,.1f} Hz</div>
      <div style="font-size: 12px; color: #94a3b8; margin-top: 2px;">Gain: {g_max:.3f} V/V ({20*math.log10(max(1e-6, g_max)):.2f} dB)</div>
    </div>
    <div class="card">
      <div class="card-label">Minimo Antirisonanza (fp)</div>
      <div class="card-val orange">{f_dip:,.1f} Hz</div>
      <div style="font-size: 12px; color: #94a3b8; margin-top: 2px;">Gain: {g_min:.3f} V/V ({20*math.log10(max(1e-6, g_min)):.2f} dB)</div>
    </div>
    <div class="card">
      <div class="card-label">Separazione Picco-Buca</div>
      <div class="card-val green">{abs(f_dip - f_peak):.1f} Hz</div>
      <div style="font-size: 12px; color: #94a3b8; margin-top: 2px;">Range Frequenza: +/-{(f_max-f_min)/2:,.0f} Hz</div>
    </div>
    <div class="card">
      <div class="card-label">Escursione di Fase</div>
      <div class="card-val" style="color: #c084fc;">{abs(p_max - p_min):.2f}&deg;</div>
      <div style="font-size: 12px; color: #94a3b8; margin-top: 2px;">da {p_min:.1f}&deg; a {p_max:.1f}&deg;</div>
    </div>
  </div>

  <div class="chart-box">
    <div class="chart-title">Modulo del Guadagno |Vout / Vin| [V/V]</div>
    <canvas id="chartGainLin" height="75"></canvas>
  </div>

  <div class="chart-box">
    <div class="chart-title">Sfasamento &Delta;&phi; [gradi]</div>
    <canvas id="chartPhase" height="75"></canvas>
  </div>
</div>

<script>
const data = [{','.join(pts_json)}];
const labels = data.map(d => d.fk.toFixed(3));
const gains = data.map(d => d.g);
const phases = data.map(d => d.p);

const commonOpts = {{
  responsive: true,
  interaction: {{ mode: 'index', intersect: false }},
  plugins: {{
    legend: {{ display: false }},
    tooltip: {{
      backgroundColor: '#0f172a',
      borderColor: '#475569',
      borderWidth: 1,
      titleColor: '#38bdf8',
      bodyColor: '#f1f5f9',
      callbacks: {{
        title: (items) => `${{data[items[0].dataIndex].f.toLocaleString('it-IT')}} Hz (${{items[0].label}} kHz)`,
        label: (item) => item.dataset.label + ': ' + item.formattedValue
      }}
    }}
  }},
  scales: {{
    x: {{
      title: {{ display: true, text: 'Frequenza [kHz]', color: '#94a3b8', font: {{ weight: 'bold' }} }},
      grid: {{ color: '#334155' }},
      ticks: {{ color: '#94a3b8' }}
    }},
    y: {{
      grid: {{ color: '#334155' }},
      ticks: {{ color: '#94a3b8' }}
    }}
  }}
}};

new Chart(document.getElementById('chartGainLin'), {{
  type: 'line',
  data: {{
    labels: labels,
    datasets: [{{
      label: 'Guadagno [V/V]',
      data: gains,
      borderColor: '#38bdf8',
      backgroundColor: 'rgba(56,189,248,0.12)',
      fill: true,
      borderWidth: 2.2,
      pointRadius: 2.5,
      pointHoverRadius: 5,
      tension: 0.15
    }}]
  }},
  options: {{
    ...commonOpts,
    scales: {{
      ...commonOpts.scales,
      y: {{
        ...commonOpts.scales.y,
        title: {{ display: true, text: 'Guadagno |Vout/Vin| [V/V]', color: '#38bdf8', font: {{ weight: 'bold' }} }}
      }}
    }}
  }}
}});

new Chart(document.getElementById('chartPhase'), {{
  type: 'line',
  data: {{
    labels: labels,
    datasets: [{{
      label: 'Sfasamento [deg]',
      data: phases,
      borderColor: '#fb923c',
      backgroundColor: 'rgba(251,146,60,0.12)',
      fill: true,
      borderWidth: 2.2,
      pointRadius: 2.5,
      pointHoverRadius: 5,
      tension: 0.15
    }}]
  }},
  options: {{
    ...commonOpts,
    scales: {{
      ...commonOpts.scales,
      y: {{
        ...commonOpts.scales.y,
        title: {{ display: true, text: 'Fase [deg]', color: '#fb923c', font: {{ weight: 'bold' }} }}
      }}
    }}
  }}
}});
</script>
</body>
</html>"""
        with open(out_html, 'w', encoding='utf-8') as fh:
            fh.write(html_code)
        print(f"\n  [OK] Report HTML interattivo generato:")
        print(f"       {out_html}")
    except Exception as eh:
        print(f"  (Generazione HTML saltata: {eh})")

    # 2. Generazione Grafico PNG ad Alta Risoluzione con Matplotlib e Fit BVD (se disponibili)
    png_generated = False
    out_png = os.path.splitext(filepath)[0] + "_bode.png"
    try:
        import numpy as np
        import matplotlib.pyplot as plt
        from scipy.optimize import curve_fit

        freqs_np = np.array(freqs)
        gains_np = np.array(gains)
        phases_np = np.array(phases)

        phase_rad = np.radians(phases_np)
        re_arr = gains_np * np.cos(phase_rad)
        im_arr = gains_np * np.sin(phase_rad)
        H_exp = re_arr + 1j * im_arr

        # Stima basamento parassita
        n_edge = max(3, len(freqs_np) // 10)
        base_idx = list(range(n_edge)) + list(range(len(freqs_np) - n_edge, len(freqs_np)))
        p_re = np.polyfit(freqs_np[base_idx], re_arr[base_idx], 1)
        p_im = np.polyfit(freqs_np[base_idx], im_arr[base_idx], 1)

        def bvd_model(f, f0, Q, A0, theta, r0, r1, i0, i1):
            f_norm = (f - freqs_np[0]) / (freqs_np[-1] - freqs_np[0])
            base = (r0 + r1 * f_norm) + 1j * (i0 + i1 * f_norm)
            mot = (A0 * np.exp(1j * theta)) / (1.0 + 2j * Q * (f - f0) / f0)
            return base + mot

        def model_flat(f, f0, Q, A0, theta, r0, r1, i0, i1):
            H = bvd_model(f, f0, Q, A0, theta, r0, r1, i0, i1)
            return np.concatenate([np.real(H), np.imag(H)])

        r0_init = p_re[1] + p_re[0] * freqs_np[0]
        r1_init = p_re[0] * (freqs_np[-1] - freqs_np[0])
        i0_init = p_im[1] + p_im[0] * freqs_np[0]
        i1_init = p_im[0] * (freqs_np[-1] - freqs_np[0])

        p0 = [f_peak, 2500.0, 0.4, -0.7, r0_init, r1_init, i0_init, i1_init]
        bounds = (
            [freqs_np[0], 200, 0.001, -np.pi, -100, -50, -100, -50],
            [freqs_np[-1], 25000, 10.0, np.pi, 100, 50, 100, 50]
        )

        has_fit = False
        try:
            popt, _ = curve_fit(model_flat, freqs_np, np.concatenate([re_arr, im_arr]), p0=p0, bounds=bounds, maxfev=10000)
            f0_opt, Q_opt, A0_opt, theta_opt, r0_opt, r1_opt, i0_opt, i1_opt = popt
            has_fit = True

            print("\n" + "=" * 75)
            print(" PARAMETRI ELETTROMECCANICI ESTRATTI DAL FIT BVD (DE-EMBEDDING):")
            print("=" * 75)
            print(f"  -> Frequenza Risonanza Meccanica (f0) : {f0_opt:.2f} Hz ({f0_opt/1e3:.4f} kHz)")
            print(f"  -> Fattore di Merito Meccanico (Q)   : {Q_opt:.1f}")
            print(f"  -> Guadagno Motionale Puro (A0)      : {A0_opt:.4f} V/V")
            print(f"  -> Sfasamento Intrinseco (theta)     : {np.degrees(theta_opt):.1f} deg")

            f_norm_pts = (freqs_np - freqs_np[0]) / (freqs_np[-1] - freqs_np[0])
            H_base_pts = (r0_opt + r1_opt * f_norm_pts) + 1j * (i0_opt + i1_opt * f_norm_pts)
            H_mot = (H_exp - H_base_pts) * np.exp(-1j * theta_opt)
            gain_mot = np.abs(H_mot)
            phase_mot = np.degrees(np.angle(H_mot))

            f_fine = np.linspace(freqs_np[0], freqs_np[-1], 2000)
            H_fit_fine = bvd_model(f_fine, *popt)
            f_norm_fine = (f_fine - freqs_np[0]) / (freqs_np[-1] - freqs_np[0])
            H_base_fine = (r0_opt + r1_opt * f_norm_fine) + 1j * (i0_opt + i1_opt * f_norm_fine)
            H_mot_fine = (H_fit_fine - H_base_fine) * np.exp(-1j * theta_opt)
        except Exception:
            has_fit = False

        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(14, 9), sharex=True)

        ax1.plot(freqs_np / 1e3, gains_np, 'o-', color='#1e88e5', markersize=3.5, lw=1.2, alpha=0.9, label='Dati Sperimentali')
        if has_fit:
            ax1.plot(f_fine / 1e3, np.abs(H_fit_fine), '-', color='#0d47a1', lw=2.2, label='Fit BVD')
        ax1.set_ylabel('Guadagno Totale |Vout/Vin| [V/V]', fontsize=10.5)
        ax1.set_title('(a) Risposta Totale Grezza (Risonanza + Basamento Cp)', fontweight='bold', fontsize=11)
        ax1.grid(True, linestyle='--', alpha=0.5)
        ax1.legend(fontsize=9, loc='best')

        if has_fit:
            ax2.plot(freqs_np / 1e3, gain_mot, 'ro', markersize=3.5, alpha=0.85, label='Dati senza Cp')
            ax2.plot(f_fine / 1e3, np.abs(H_mot_fine), 'r-', lw=2.2, label=f'Campana ($Q={Q_opt:.0f}$, $f_0={f0_opt/1e3:.3f}$ kHz)')
        else:
            ax2.plot(freqs_np / 1e3, gains_np, 'r.-', alpha=0.7)
        ax2.set_ylabel('Guadagno Motionale [V/V]', fontsize=10.5)
        ax2.set_title('(b) Ramo Motionale Puro (Cp Sottratto)', fontweight='bold', fontsize=11)
        ax2.grid(True, linestyle='--', alpha=0.5)
        ax2.legend(fontsize=9, loc='upper right')

        ax3.plot(freqs_np / 1e3, phases_np, 's-', color='#fb8c00', markersize=3.5, lw=1.2, alpha=0.9, label='Dati Sperimentali')
        if has_fit:
            ax3.plot(f_fine / 1e3, np.degrees(np.angle(H_fit_fine)), '-', color='#e65100', lw=2.2, label='Fit Fase Fano')
        ax3.set_xlabel('Frequenza [kHz]', fontsize=10.5)
        ax3.set_ylabel('Sfasamento Grezzo [deg]', fontsize=10.5)
        ax3.set_title('(c) Sfasamento Totale Grezzo (Dip di Fano)', fontweight='bold', fontsize=11)
        ax3.grid(True, linestyle='--', alpha=0.5)
        ax3.legend(fontsize=9, loc='best')

        if has_fit:
            ax4.plot(freqs_np / 1e3, phase_mot, 'mo', markersize=3.5, alpha=0.85, label='Fase senza Cp')
            ax4.plot(f_fine / 1e3, np.degrees(np.angle(H_mot_fine)), 'm-', lw=2.2, label=r'Transizione RLC $+90^\circ \to 0^\circ \to -90^\circ$')
        else:
            ax4.plot(freqs_np / 1e3, phases_np, 'm.-', alpha=0.7)
        ax4.axhline(0, color='gray', linestyle=':', alpha=0.7)
        ax4.set_xlabel('Frequenza [kHz]', fontsize=10.5)
        ax4.set_ylabel('Fase Motionale [deg]', fontsize=10.5)
        ax4.set_title('(d) Sfasamento Ramo Motionale (Salto 180° RLC)', fontweight='bold', fontsize=11)
        ax4.grid(True, linestyle='--', alpha=0.5)
        ax4.legend(fontsize=9, loc='lower left')

        plt.tight_layout()
        plt.savefig(out_png, dpi=220)
        plt.close(fig)
        png_generated = True

        print(f"\n  [OK] Immagine PNG ad alta risoluzione salvata:")
        print(f"       {out_png}")
    except Exception:
        pass

    # Apertura automatica su Windows: se c'è il PNG apre il PNG, altrimenti apre il file HTML nel browser!
    try:
        if png_generated and os.path.exists(out_png):
            os.startfile(out_png)
        elif os.path.exists(out_html):
            os.startfile(out_html)
    except Exception:
        pass


if __name__ == '__main__':
    if len(sys.argv) > 1:
        target = sys.argv[1]
    else:
        folder = os.path.dirname(os.path.abspath(__file__))
        cands = sorted(glob.glob(os.path.join(folder, "sweep_*.csv")), key=os.path.getmtime)
        if not cands:
            print("[AVVISO] Nessun file sweep_*.csv trovato nella cartella.")
            sys.exit(1)
        target = cands[-1]

    elabora_file(target)
