import urllib.request
import re
from datetime import datetime

def generate_svg(username="hg5594176-source", output_path="commit-graph.svg"):
    url = f"https://github.com/users/{username}/contributions"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as resp:
        html = resp.read().decode("utf-8")

    # Extract total contributions
    total_match = re.search(r'([0-9,]+)\s+contributions?\s+in\s+the\s+last\s+year', html)
    total_contribs = total_match.group(1) if total_match else "1,400+"

    # Extract tooltips
    tooltips = dict(re.findall(r'for="(contribution-day-component-[^"]+)"[^>]*>(?:<span[^>]*>)?(.*?)(?:</span>)?</tool-tip>', html))

    # Extract days
    td_matches = re.findall(r'<td[^>]*data-date="(\d{4}-\d{2}-\d{2})"[^>]*id="([^"]+)"[^>]*>', html)
    if not td_matches:
        # try alternative order
        td_matches = re.findall(r'<td[^>]*id="([^"]+)"[^>]*data-date="(\d{4}-\d{2}-\d{2})"[^>]*>', html)
        td_matches = [(d, i) for i, d in td_matches]

    # Map dates to commit count
    daily_data = []
    for date_str, comp_id in td_matches:
        tip = tooltips.get(comp_id, "")
        cnt_match = re.search(r'(\d+)\s+contribution', tip)
        count = int(cnt_match.group(1)) if cnt_match else 0
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        daily_data.append((dt, count, date_str))

    daily_data.sort(key=lambda x: x[0])

    if not daily_data:
        print("Warning: No daily data found!")
        return

    # Aggregate weekly or 3-day rolling to create a beautifully smooth line
    # (365 daily points directly or rolling 7-day average/sum)
    # Let's do 7-day rolling sum or weekly aggregation for a clean, flowing graph!
    window = 5
    smoothed = []
    for i in range(len(daily_data)):
        start = max(0, i - window + 1)
        sub = daily_data[start:i+1]
        avg_val = sum(x[1] for x in sub) / len(sub)
        smoothed.append((daily_data[i][0], avg_val, daily_data[i][1]))

    # Chart dimensions
    width = 820
    height = 240
    padding_left = 50
    padding_right = 30
    padding_top = 70
    padding_bottom = 45

    plot_width = width - padding_left - padding_right
    plot_height = height - padding_top - padding_bottom

    max_val = max(x[1] for x in smoothed) if smoothed else 1
    if max_val == 0:
        max_val = 1
    # add headroom
    max_val = max_val * 1.15

    # Coordinates for smoothed line
    n_points = len(smoothed)
    points = []
    for i, (dt, val, raw_val) in enumerate(smoothed):
        x = padding_left + (i / (n_points - 1)) * plot_width
        y = padding_top + plot_height - (val / max_val) * plot_height
        points.append((x, y))

    # Build SVG smooth path (Catmull-Rom or cubic Bezier)
    def points_to_path(pts):
        if not pts:
            return ""
        d = [f"M {pts[0][0]:.1f},{pts[0][1]:.1f}"]
        for i in range(len(pts) - 1):
            p0 = pts[i - 1] if i > 0 else pts[i]
            p1 = pts[i]
            p2 = pts[i + 1]
            p3 = pts[i + 2] if i + 2 < len(pts) else p2
            # Catmull-Rom to cubic Bezier
            c1x = p1[0] + (p2[0] - p0[0]) / 6.0
            c1y = p1[1] + (p2[1] - p0[1]) / 6.0
            c2x = p2[0] - (p3[0] - p1[0]) / 6.0
            c2y = p2[1] - (p3[1] - p1[1]) / 6.0
            d.append(f"C {c1x:.1f},{c1y:.1f} {c2x:.1f},{c2y:.1f} {p2[0]:.1f},{p2[1]:.1f}")
        return " ".join(d)

    line_d = points_to_path(points)
    area_d = f"{line_d} L {points[-1][0]:.1f},{padding_top + plot_height:.1f} L {points[0][0]:.1f},{padding_top + plot_height:.1f} Z"

    # Month labels on X axis
    month_ticks = []
    last_month = None
    for i, (dt, _, _) in enumerate(daily_data):
        if dt.month != last_month and dt.day <= 10:
            last_month = dt.month
            x = padding_left + (i / (n_points - 1)) * plot_width
            month_name = dt.strftime("%b")
            month_ticks.append((x, month_name))

    # Grid lines (3 horizontal lines)
    grid_svg = []
    for frac in [0.25, 0.5, 0.75, 1.0]:
        gy = padding_top + plot_height - frac * plot_height
        grid_svg.append(f'<line x1="{padding_left}" y1="{gy:.1f}" x2="{width - padding_right}" y2="{gy:.1f}" stroke="#30363d" stroke-dasharray="3,3" stroke-width="1" />')

    month_svg = []
    for x, mname in month_ticks:
        month_svg.append(f'<text x="{x:.1f}" y="{height - 15}" fill="#8b949e" font-size="11" font-family="-apple-system,BlinkMacSystemFont,\'Segoe UI\',Helvetica,Arial,sans-serif" text-anchor="middle">{mname}</text>')

    # Find peak point
    max_pt = min(points, key=lambda p: p[1])
    last_pt = points[-1]

    svg_content = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="100%" height="auto" style="background: transparent;">
  <defs>
    <!-- Background Gradient -->
    <linearGradient id="bgGrad" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#0d1117"/>
      <stop offset="100%" stop-color="#161b22"/>
    </linearGradient>

    <!-- Bright Green Area Gradient -->
    <linearGradient id="brightGreenGlow" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#39d353" stop-opacity="0.38"/>
      <stop offset="60%" stop-color="#00ff88" stop-opacity="0.12"/>
      <stop offset="100%" stop-color="#00ff88" stop-opacity="0.0"/>
    </linearGradient>

    <!-- Neon Glow Filter -->
    <filter id="neonGlow" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="3" result="blur" />
      <feMerge>
        <feMergeNode in="blur" />
        <feMergeNode in="SourceGraphic" />
      </feMerge>
    </filter>
  </defs>

  <!-- Container Box -->
  <rect x="1" y="1" width="{width - 2}" height="{height - 2}" rx="10" fill="url(#bgGrad)" stroke="#30363d" stroke-width="1.2"/>

  <!-- Title & Info -->
  <g transform="translate({padding_left}, 32)">
    <!-- Git Branch / Activity Icon -->
    <circle cx="6" cy="6" r="4" fill="#39d353" />
    <circle cx="6" cy="6" r="8" fill="#39d353" opacity="0.25">
      <animate attributeName="r" values="6;10;6" dur="2.5s" repeatCount="indefinite" />
      <animate attributeName="opacity" values="0.3;0.05;0.3" dur="2.5s" repeatCount="indefinite" />
    </circle>
    <text x="24" y="10" fill="#f0f6fc" font-size="15" font-weight="600" font-family="-apple-system,BlinkMacSystemFont,\'Segoe UI\',Helvetica,Arial,sans-serif">Git Commit &amp; Contribution Activity</text>
    <text x="{width - padding_left - padding_right}" y="10" fill="#39d353" font-size="13" font-weight="600" font-family="-apple-system,BlinkMacSystemFont,\'Segoe UI\',Helvetica,Arial,sans-serif" text-anchor="end">⚡ {total_contribs} commits &amp; contributions this year</text>
  </g>

  <!-- Grid lines -->
  {''.join(grid_svg)}

  <!-- Under-curve Area Fill -->
  <path d="{area_d}" fill="url(#brightGreenGlow)" />

  <!-- The Bright Green Commit Line -->
  <!-- Ambient line glow -->
  <path d="{line_d}" fill="none" stroke="#00ff88" stroke-width="5" stroke-opacity="0.35" filter="url(#neonGlow)" />
  <!-- Sharp Bright Green Line -->
  <path d="{line_d}" fill="none" stroke="#39d353" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round" />

  <!-- Highlight Peak Point -->
  <circle cx="{max_pt[0]:.1f}" cy="{max_pt[1]:.1f}" r="4" fill="#39d353" stroke="#0d1117" stroke-width="2" />
  <circle cx="{max_pt[0]:.1f}" cy="{max_pt[1]:.1f}" r="8" fill="#39d353" opacity="0.3" />

  <!-- Highlight Current / Latest Point -->
  <circle cx="{last_pt[0]:.1f}" cy="{last_pt[1]:.1f}" r="4.5" fill="#00ff88" stroke="#0d1117" stroke-width="2" />
  <circle cx="{last_pt[0]:.1f}" cy="{last_pt[1]:.1f}" r="9" fill="#00ff88" opacity="0.4">
    <animate attributeName="r" values="6;11;6" dur="2s" repeatCount="indefinite" />
    <animate attributeName="opacity" values="0.4;0.1;0.4" dur="2s" repeatCount="indefinite" />
  </circle>

  <!-- Bottom Axis Line -->
  <line x1="{padding_left}" y1="{padding_top + plot_height}" x2="{width - padding_right}" y2="{padding_top + plot_height}" stroke="#30363d" stroke-width="1.2" />

  <!-- Month Ticks -->
  {''.join(month_svg)}
</svg>'''

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(svg_content)
    print(f"Generated commit graph SVG successfully at: {output_path}")

if __name__ == "__main__":
    generate_svg()
