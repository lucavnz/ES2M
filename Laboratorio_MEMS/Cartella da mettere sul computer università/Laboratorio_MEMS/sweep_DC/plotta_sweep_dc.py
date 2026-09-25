"""
Visualizzatore e Analisi Multi-Curva per Sweep DC MEMS (Agilent E3646A)
Funziona su qualsiasi PC:
  1. Con Python Minimale/Portatile (zero librerie esterne):
     - Estrae tutti gli sweep al variare di VDC (0V, 2V, ..., 20V)
     - Calcola la sintonia elettrostatica: Spring Softening f0 vs VDC^2
     - Genera un report interattivo HTML moderno con grafici Chart.js:
       * Bode Modulo Multi-Curva [dB e V/V]
       * Bode Fase Multi-Curva [deg]
       * Andamento Frequenza di Risonanza vs VDC e vs VDC^2
       * Guadagno di Picco vs VDC
       * Tabella interattiva dei parametri estratti
     - Apre automaticamente il report nel browser
  2. Con Python Completo (matplotlib / numpy se disponibili):
     - Genera anche l'immagine PNG multi-quadrante ad alta risoluzione
"""

import os
import sys
import glob
import csv
import math


def genera_colori_gradiente(n):
    """Genera n colori sfumati dal ciano al magenta/arancio per distinguere le curve di VDC."""
    colori = []
    for i in range(n):
        ratio = i / max(1, n - 1)
        # Transizione HSL da blu (210) a rosso/magenta (0 o 350)
        hue = int(220 - ratio * 220)
        sat = 85
        lum = 55
        colori.append(f"hsl({hue}, {sat}%, {lum}%)")
    return colori


def elabora_sessione_dc(path_input):
    path_input = os.path.abspath(path_input)

    # Identifica cartella o file master
    if os.path.isdir(path_input):
        cartella = path_input
        # Cerca file master
        masters = glob.glob(os.path.join(cartella, "sweep_master_DC_*.csv"))
        if not masters:
            print(f"[ERRORE] Nessun file sweep_master_DC_*.csv trovato in {cartella}")
            return
        master_file = sorted(masters)[-1]
    else:
        master_file = path_input
        cartella = os.path.dirname(master_file)

    print("=" * 80)
    print(f" ELABORAZIONE SWEEP DC MEMS: {os.path.basename(master_file)}")
    print("=" * 80)

    # Lettura file master cumulativo
    data_by_vdc = {}
    with open(master_file, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        for r in reader:
            if not r or r[0].startswith('#') or r[0].lower().startswith('vdc'):
                continue
            try:
                vdc_t = float(r[0])
                vdc_m = float(r[1])
                idc_m = float(r[2])
                freq = float(r[4])
                vin = float(r[6])
                vout = float(r[7])
                gain_lin = float(r[8])
                gain_db = float(r[9])
                phase = float(r[10])

                if math.isnan(freq) or math.isnan(gain_lin) or math.isnan(phase):
                    continue

                if vdc_t not in data_by_vdc:
                    data_by_vdc[vdc_t] = {
                        "vdc_meas": vdc_m,
                        "idc_meas": idc_m,
                        "freqs": [],
                        "vins": [],
                        "vouts": [],
                        "gains_lin": [],
                        "gains_db": [],
                        "phases": []
                    }
                data_by_vdc[vdc_t]["freqs"].append(freq)
                data_by_vdc[vdc_t]["vins"].append(vin)
                data_by_vdc[vdc_t]["vouts"].append(vout)
                data_by_vdc[vdc_t]["gains_lin"].append(gain_lin)
                data_by_vdc[vdc_t]["gains_db"].append(gain_db)
                data_by_vdc[vdc_t]["phases"].append(phase)
            except (ValueError, IndexError):
                continue

    if not data_by_vdc:
        print("[ERRORE] Nessun dato valido estratto dal file master.")
        return

    vdc_sorted = sorted(data_by_vdc.keys())
    print(f"  * Curve VDC Rilevate ({len(vdc_sorted)}): {', '.join(f'{v:.1f}V' for v in vdc_sorted)}")

    # Analisi picchi per ciascun VDC
    stats = []
    for v in vdc_sorted:
        d = data_by_vdc[v]
        freqs = d["freqs"]
        g_lin = d["gains_lin"]
        g_db = d["gains_db"]
        phases = d["phases"]

        g_max = max(g_lin)
        g_min = min(g_lin)
        idx_max = g_lin.index(g_max)
        idx_min = g_lin.index(g_min)

        f_peak = freqs[idx_max]
        f_dip = freqs[idx_min]
        phase_peak = phases[idx_max]
        g_max_db = g_db[idx_max]

        stats.append({
            "vdc": v,
            "vdc_meas": d["vdc_meas"],
            "idc_meas": d["idc_meas"],
            "f_peak": f_peak,
            "f_dip": f_dip,
            "delta_f": abs(f_dip - f_peak),
            "g_max_lin": g_max,
            "g_max_db": g_max_db,
            "phase_peak": phase_peak
        })

    # Stampa riassunto a video
    print("\n" + "-" * 85)
    print(f"{'VDC [V]':>7} | {'fs Risonanza [Hz]':>17} | {'fp Antirisonanza [Hz]':>21} | {'Gmax [dB]':>10} | {'Fase fs [°]':>11}")
    print("-" * 85)
    for s in stats:
        print(f"{s['vdc']:7.1f} | {s['f_peak']:17,.1f} | {s['f_dip']:21,.1f} | {s['g_max_db']:+10.2f} | {s['phase_peak']:+11.1f}")
    print("-" * 85)

    # Spring Softening Delta f0
    f0_initial = stats[0]["f_peak"]
    f0_final = stats[-1]["f_peak"]
    delta_f_softening = f0_final - f0_initial
    print(f"\n  --> Spring Softening Totale (da {stats[0]['vdc']:.0f}V a {stats[-1]['vdc']:.0f}V): Delta f0 = {delta_f_softening:+,.1f} Hz")
    if stats[-1]['vdc'] > 0:
        c_softening = delta_f_softening / (stats[-1]['vdc'] ** 2)
        print(f"  --> Coefficiente Elettrostatico k_soft: ~{c_softening:.3f} Hz/V^2")

    # 1. Generazione Report HTML Interattivo
    out_html = os.path.join(cartella, f"report_sweep_DC_interattivo.html")
    palette = genera_colori_gradiente(len(vdc_sorted))

    # Prepara serie JSON per Chart.js
    datasets_gain_db = []
    datasets_gain_lin = []
    datasets_phase = []

    # Usa le frequenze del primo sweep come asse X comune
    common_freqs = data_by_vdc[vdc_sorted[0]]["freqs"]
    labels_f_khz = [f"{f/1e3:.3f}" for f in common_freqs]

    for idx_c, v in enumerate(vdc_sorted):
        col = palette[idx_c]
        d = data_by_vdc[v]
        gdb_str = ",".join(f"{g:.2f}" for g in d["gains_db"])
        glin_str = ",".join(f"{g:.4f}" for g in d["gains_lin"])
        phas_str = ",".join(f"{p:.2f}" for p in d["phases"])

        datasets_gain_db.append(f"""{{
            label: '{v:.1f} V',
            data: [{gdb_str}],
            borderColor: '{col}',
            backgroundColor: '{col}',
            borderWidth: 2,
            pointRadius: 1.5,
            fill: false,
            tension: 0.1
        }}""")

        datasets_gain_lin.append(f"""{{
            label: '{v:.1f} V',
            data: [{glin_str}],
            borderColor: '{col}',
            backgroundColor: '{col}',
            borderWidth: 2,
            pointRadius: 1.5,
            fill: false,
            tension: 0.1
        }}""")

        datasets_phase.append(f"""{{
            label: '{v:.1f} V',
            data: [{phas_str}],
            borderColor: '{col}',
            backgroundColor: '{col}',
            borderWidth: 2,
            pointRadius: 1.5,
            fill: false,
            tension: 0.1
        }}""")

    # Dati sintonia fs vs VDC
    vdc_labels = [f"{s['vdc']:.1f}" for s in stats]
    fs_vals = [f"{s['f_peak']:.1f}" for s in stats]
    vdc_sq_labels = [f"{s['vdc']**2:.0f}" for s in stats]
    gmax_vals = [f"{s['g_max_lin']:.4f}" for s in stats]

    html_code = f"""<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Report Sweep DC MEMS - {os.path.basename(master_file)}</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
  * {{ box-sizing: border-box; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0b1120; color: #f1f5f9; margin: 0; padding: 24px; }}
  .container {{ max-width: 1350px; margin: 0 auto; }}
  .header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #1e293b; padding-bottom: 18px; margin-bottom: 24px; }}
  h1 {{ font-size: 24px; font-weight: 700; color: #38bdf8; margin: 0 0 6px 0; }}
  .subtitle {{ color: #94a3b8; font-size: 14px; }}
  .badge {{ background: #1e293b; border: 1px solid #334155; padding: 6px 12px; border-radius: 6px; font-family: monospace; font-size: 13px; color: #38bdf8; }}
  .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 16px; margin-bottom: 26px; }}
  .card {{ background: #1e293b; border-radius: 10px; padding: 16px 20px; border: 1px solid #334155; }}
  .card-label {{ font-size: 12px; font-weight: 600; text-transform: uppercase; color: #64748b; margin-bottom: 6px; }}
  .card-val {{ font-size: 20px; font-weight: 700; color: #f8fafc; }}
  .cyan {{ color: #38bdf8; }}
  .orange {{ color: #fb923c; }}
  .green {{ color: #4ade80; }}
  .purple {{ color: #c084fc; }}
  .chart-box {{ background: #1e293b; border-radius: 12px; padding: 22px; border: 1px solid #334155; margin-bottom: 26px; }}
  .chart-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; }}
  .chart-title {{ font-size: 16px; font-weight: 600; color: #e2e8f0; }}
  .chart-hint {{ font-size: 12px; color: #64748b; }}
  .charts-duo {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 26px; }}
  table {{ width: 100%; border-collapse: collapse; margin-top: 14px; font-size: 13px; }}
  th, td {{ padding: 10px 14px; text-align: right; border-bottom: 1px solid #334155; }}
  th {{ background: #0f172a; color: #94a3b8; font-weight: 600; text-transform: uppercase; font-size: 11px; }}
  tr:hover {{ background: rgba(56, 189, 248, 0.05); }}
  td:first-child, th:first-child {{ text-align: left; }}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <div>
      <h1>Caratterizzazione Risonatore MEMS al variare di V<sub>DC</sub></h1>
      <div class="subtitle">Agilent E3646A (Output 1) + Agilent 33220A (GPIB) + Keysight MSO-X 3014A (USB)</div>
    </div>
    <div class="badge">
      Sessione: {os.path.basename(cartella)}<br>
      <b>{len(vdc_sorted)} Curve VDC ({vdc_sorted[0]:.0f}V &rarr; {vdc_sorted[-1]:.0f}V)</b>
    </div>
  </div>

  <div class="stats-grid">
    <div class="card">
      <div class="card-label">Intervallo Polarizzazione VDC</div>
      <div class="card-val cyan">{stats[0]['vdc']:.1f} V &rarr; {stats[-1]['vdc']:.1f} V</div>
      <div style="font-size: 12px; color: #94a3b8; margin-top: 4px;">Passo: {stats[1]['vdc'] - stats[0]['vdc']:.1f} V ({len(stats)} passi)</div>
    </div>
    <div class="card">
      <div class="card-label">Spring Softening (&Delta;f<sub>0</sub>)</div>
      <div class="card-val orange">{delta_f_softening:+,.1f} Hz</div>
      <div style="font-size: 12px; color: #94a3b8; margin-top: 4px;">fs: da {stats[0]['f_peak']:,.1f} a {stats[-1]['f_peak']:,.1f} Hz</div>
    </div>
    <div class="card">
      <div class="card-label">Crescita Picco Trasduzione</div>
      <div class="card-val green">da {stats[0]['g_max_db']:+.2f} dB a {stats[-1]['g_max_db']:+.2f} dB</div>
      <div style="font-size: 12px; color: #94a3b8; margin-top: 4px;">Guadagno max: {stats[-1]['g_max_lin']:.3f} V/V</div>
    </div>
    <div class="card">
      <div class="card-label">Separazione Picco-Buca (&Delta;f)</div>
      <div class="card-val purple">{stats[-1]['delta_f']:.1f} Hz a {stats[-1]['vdc']:.0f}V</div>
      <div style="font-size: 12px; color: #94a3b8; margin-top: 4px;">fp antirisonanza: {stats[-1]['f_dip']:,.1f} Hz</div>
    </div>
  </div>

  <!-- 1. Bode Modulo [dB] Multi-Curva -->
  <div class="chart-box">
    <div class="chart-header">
      <div class="chart-title">Diagramma di Bode: Guadagno |H(j&omega;)| in dB al variare di V<sub>DC</sub></div>
      <div class="chart-hint">Clicca sulla legenda per mostrare/nascondere singole tensioni</div>
    </div>
    <canvas id="chartGainDb" height="80"></canvas>
  </div>

  <!-- 2. Bode Fase Multi-Curva -->
  <div class="chart-box">
    <div class="chart-header">
      <div class="chart-title">Diagramma di Bode: Fase &ang;H(j&omega;) [&deg;] al variare di V<sub>DC</sub></div>
      <div class="chart-hint">Transizione di fase caratteristica della risonanza MEMS</div>
    </div>
    <canvas id="chartPhase" height="80"></canvas>
  </div>

  <!-- 3. Due grafici affiancati: Sintonia fs vs VDC e Guadagno Picco vs VDC -->
  <div class="charts-duo">
    <div class="chart-box">
      <div class="chart-header">
        <div class="chart-title">Spring Softening: f<sub>s</sub> vs V<sub>DC</sub><sup>2</sup> [V<sup>2</sup>]</div>
        <div class="chart-hint">Andamento lineare atteso: f<sub>s</sub>(V<sub>DC</sub>) &approx; f<sub>0</sub> - &alpha; V<sub>DC</sub><sup>2</sup></div>
      </div>
      <canvas id="chartSoftening" height="130"></canvas>
    </div>
    <div class="chart-box">
      <div class="chart-header">
        <div class="chart-title">Efficienza di Trasduzione: Guadagno di Picco vs V<sub>DC</sub></div>
        <div class="chart-hint">Crescita dell'accoppiamento elettromeccanico &eta; &prop; V<sub>DC</sub></div>
      </div>
      <canvas id="chartTransduction" height="130"></canvas>
    </div>
  </div>

  <!-- Tabella Dati Riassuntiva -->
  <div class="chart-box">
    <div class="chart-title">Tabella Parametri Estratti per ciascuna Tensione V<sub>DC</sub></div>
    <table>
      <thead>
        <tr>
          <th>V<sub>DC</sub> Target [V]</th>
          <th>V<sub>DC</sub> Reale [V]</th>
          <th>I<sub>DC</sub> [mA]</th>
          <th>f<sub>s</sub> Risonanza [Hz]</th>
          <th>f<sub>p</sub> Antirisonanza [Hz]</th>
          <th>&Delta;f [Hz]</th>
          <th>Guadagno Picco [V/V]</th>
          <th>Guadagno Picco [dB]</th>
          <th>Fase al Picco [&deg;]</th>
        </tr>
      </thead>
      <tbody>
"""

    for s in stats:
        html_code += f"""        <tr>
          <td style="color: #38bdf8; font-weight: bold;">{s['vdc']:.1f} V</td>
          <td>{s['vdc_meas']:.3f} V</td>
          <td>{s['idc_meas']*1e3:.2f}</td>
          <td style="font-weight: bold; color: #fb923c;">{s['f_peak']:,.1f}</td>
          <td>{s['f_dip']:,.1f}</td>
          <td>{s['delta_f']:.1f}</td>
          <td>{s['g_max_lin']:.4f}</td>
          <td style="font-weight: bold; color: #4ade80;">{s['g_max_db']:+.2f}</td>
          <td>{s['phase_peak']:+.2f}</td>
        </tr>\n"""

    html_code += f"""      </tbody>
    </table>
  </div>
</div>

<script>
const labelsF = [{','.join(f"'{l}'" for l in labels_f_khz)}];

const baseOpts = {{
  responsive: true,
  interaction: {{ mode: 'index', intersect: false }},
  plugins: {{
    legend: {{
      position: 'top',
      labels: {{ color: '#cbd5e1', boxWidth: 12, padding: 10, font: {{ size: 11 }} }}
    }}
  }},
  scales: {{
    x: {{
      title: {{ display: true, text: 'Frequenza [kHz]', color: '#94a3b8', font: {{ weight: 'bold' }} }},
      grid: {{ color: 'rgba(51, 65, 85, 0.4)' }},
      ticks: {{ color: '#94a3b8' }}
    }},
    y: {{
      grid: {{ color: 'rgba(51, 65, 85, 0.4)' }},
      ticks: {{ color: '#94a3b8' }}
    }}
  }}
}};

// 1. Chart Gain dB
new Chart(document.getElementById('chartGainDb'), {{
  type: 'line',
  data: {{
    labels: labelsF,
    datasets: [{','.join(datasets_gain_db)}]
  }},
  options: {{
    ...baseOpts,
    scales: {{
      ...baseOpts.scales,
      y: {{
        ...baseOpts.scales.y,
        title: {{ display: true, text: 'Guadagno |H(j&omega;)| [dB]', color: '#38bdf8', font: {{ weight: 'bold' }} }}
      }}
    }}
  }}
}});

// 2. Chart Phase
new Chart(document.getElementById('chartPhase'), {{
  type: 'line',
  data: {{
    labels: labelsF,
    datasets: [{','.join(datasets_phase)}]
  }},
  options: {{
    ...baseOpts,
    scales: {{
      ...baseOpts.scales,
      y: {{
        ...baseOpts.scales.y,
        title: {{ display: true, text: 'Fase [deg]', color: '#fb923c', font: {{ weight: 'bold' }} }}
      }}
    }}
  }}
}});

// 3. Chart Softening (fs vs Vdc^2)
new Chart(document.getElementById('chartSoftening'), {{
  type: 'line',
  data: {{
    labels: [{','.join(f"'{l}'" for l in vdc_sq_labels)}],
    datasets: [{{
      label: 'fs Risonanza [Hz]',
      data: [{','.join(fs_vals)}],
      borderColor: '#fb923c',
      backgroundColor: 'rgba(251, 146, 60, 0.15)',
      borderWidth: 2.5,
      pointRadius: 5,
      pointHoverRadius: 7,
      fill: true,
      tension: 0.1
    }}]
  }},
  options: {{
    responsive: true,
    scales: {{
      x: {{
        title: {{ display: true, text: 'V_DC^2 [V^2]', color: '#94a3b8', font: {{ weight: 'bold' }} }},
        grid: {{ color: 'rgba(51, 65, 85, 0.4)' }},
        ticks: {{ color: '#94a3b8' }}
      }},
      y: {{
        title: {{ display: true, text: 'Frequenza fs [Hz]', color: '#fb923c', font: {{ weight: 'bold' }} }},
        grid: {{ color: 'rgba(51, 65, 85, 0.4)' }},
        ticks: {{ color: '#94a3b8' }}
      }}
    }}
  }}
}});

// 4. Chart Transduction Gain vs VDC
new Chart(document.getElementById('chartTransduction'), {{
  type: 'line',
  data: {{
    labels: [{','.join(f"'{l}'" for l in vdc_labels)}],
    datasets: [{{
      label: 'Guadagno di Picco [V/V]',
      data: [{','.join(gmax_vals)}],
      borderColor: '#4ade80',
      backgroundColor: 'rgba(74, 222, 128, 0.15)',
      borderWidth: 2.5,
      pointRadius: 5,
      pointHoverRadius: 7,
      fill: true,
      tension: 0.1
    }}]
  }},
  options: {{
    responsive: true,
    scales: {{
      x: {{
        title: {{ display: true, text: 'Tensione V_DC [V]', color: '#94a3b8', font: {{ weight: 'bold' }} }},
        grid: {{ color: 'rgba(51, 65, 85, 0.4)' }},
        ticks: {{ color: '#94a3b8' }}
      }},
      y: {{
        title: {{ display: true, text: 'Guadagno Max [V/V]', color: '#4ade80', font: {{ weight: 'bold' }} }},
        grid: {{ color: 'rgba(51, 65, 85, 0.4)' }},
        ticks: {{ color: '#94a3b8' }}
      }}
    }}
  }}
}});
</script>
</body>
</html>"""

    with open(out_html, 'w', encoding='utf-8') as fh:
        fh.write(html_code)

    print(f"\n  [OK] Report Interattivo HTML generato:")
    print(f"       {out_html}")

    # 2. Generazione Grafico PNG ad Alta Risoluzione con Matplotlib (se installato)
    try:
        import numpy as np
        import matplotlib.pyplot as plt

        plt.style.use('dark_background')
        fig, axs = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle(f"Caratterizzazione Risonatore MEMS al variare di VDC (Agilent E3646A)", fontsize=16, fontweight='bold', color='#38bdf8')

        cmap = plt.get_cmap('plasma')
        n_curves = len(vdc_sorted)

        # Q1: Bode Modulo [dB]
        ax1 = axs[0, 0]
        for idx, v in enumerate(vdc_sorted):
            d = data_by_vdc[v]
            color = cmap(idx / max(1, n_curves - 1))
            f_khz = [f / 1e3 for f in d["freqs"]]
            ax1.plot(f_khz, d["gains_db"], label=f"{v:.0f}V", color=color, lw=1.6)
        ax1.set_title("Guadagno |H(jw)| [dB]", fontweight='bold', color='#38bdf8')
        ax1.set_xlabel("Frequenza [kHz]")
        ax1.set_ylabel("Guadagno [dB]")
        ax1.grid(True, alpha=0.3)
        ax1.legend(loc='upper right', fontsize=8, ncol=2)

        # Q2: Bode Fase [deg]
        ax2 = axs[0, 1]
        for idx, v in enumerate(vdc_sorted):
            d = data_by_vdc[v]
            color = cmap(idx / max(1, n_curves - 1))
            f_khz = [f / 1e3 for f in d["freqs"]]
            ax2.plot(f_khz, d["phases"], label=f"{v:.0f}V", color=color, lw=1.6)
        ax2.set_title("Fase <H(jw) [deg]", fontweight='bold', color='#fb923c')
        ax2.set_xlabel("Frequenza [kHz]")
        ax2.set_ylabel("Fase [°]")
        ax2.grid(True, alpha=0.3)

        # Q3: Spring Softening fs vs Vdc^2
        ax3 = axs[1, 0]
        vdc_arr = np.array([s["vdc"] for s in stats])
        fs_arr = np.array([s["f_peak"] for s in stats])
        vdc_sq = vdc_arr ** 2
        ax3.plot(vdc_sq, fs_arr, 'o-', color='#fb923c', lw=2, markersize=6, label='Misura')
        if len(vdc_sq) > 1:
            p = np.polyfit(vdc_sq, fs_arr, 1)
            ax3.plot(vdc_sq, np.polyval(p, vdc_sq), '--', color='#f8fafc', alpha=0.8, label=f'Fit: slope = {p[0]:.2f} Hz/V^2')
        ax3.set_title("Spring Softening: fs vs VDC^2", fontweight='bold', color='#fb923c')
        ax3.set_xlabel("VDC^2 [V^2]")
        ax3.set_ylabel("Frequenza fs [Hz]")
        ax3.grid(True, alpha=0.3)
        ax3.legend()

        # Q4: Guadagno di Picco vs VDC
        ax4 = axs[1, 1]
        gpeak_arr = np.array([s["g_max_lin"] for s in stats])
        ax4.plot(vdc_arr, gpeak_arr, 's-', color='#4ade80', lw=2, markersize=6)
        ax4.set_title("Efficienza di Trasduzione: Guadagno Max vs VDC", fontweight='bold', color='#4ade80')
        ax4.set_xlabel("VDC [V]")
        ax4.set_ylabel("Guadagno Picco [V/V]")
        ax4.grid(True, alpha=0.3)

        plt.tight_layout()
        out_png = os.path.join(cartella, "grafico_sweep_DC_confronto.png")
        plt.savefig(out_png, dpi=200)
        plt.close()
        print(f"  [OK] Immagine PNG ad alta risoluzione salvata:")
        print(f"       {out_png}")
    except Exception as e_png:
        print(f"  (Generazione PNG matplotlib saltata: {e_png})")

    # Apertura automatica browser
    try:
        import webbrowser
        webbrowser.open(f"file:///{out_html}")
    except Exception:
        pass


def main():
    cartella_lavoro = os.path.dirname(os.path.abspath(__file__))
    target_path = None

    if len(sys.argv) > 1:
        target_path = sys.argv[1]
    else:
        # Cerca l'ultima sessione creata
        sessioni = glob.glob(os.path.join(cartella_lavoro, "sessione_DC_*"))
        if sessioni:
            target_path = sorted(sessioni)[-1]
        else:
            masters = glob.glob(os.path.join(cartella_lavoro, "sweep_master_DC_*.csv"))
            if masters:
                target_path = sorted(masters)[-1]

    if not target_path:
        print("[ERRORE] Nessuna sessione o file master sweep DC trovato.")
        input("\nPremi INVIO per uscire...")
        return

    elabora_sessione_dc(target_path)
    input("\nPremi INVIO per chiudere...")


if __name__ == "__main__":
    main()
