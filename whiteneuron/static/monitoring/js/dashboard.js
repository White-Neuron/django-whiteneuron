// Server monitoring dashboard (whiteneuron.monitoring) — Chart.js 4 from django-unfold
(function () {
    "use strict";

    const root = document.getElementById("wn-monitoring");
    if (!root || !window.Chart) {
        return;
    }
    const T = JSON.parse(document.getElementById("wn-mon-i18n").textContent || "{}");
    const REFRESH_MS = { off: 0, "5s": 5000, "10s": 10000, "30s": 30000, "1m": 60000, "5m": 300000 };
    const ROWS_KEY = "wn-mon-rows";

    const state = {
        api: root.dataset.api,
        range: root.dataset.range,
        refresh: root.dataset.refresh,
        host: root.dataset.host,
        data: null,
        timer: null,
        controller: null,
        charts: {},
        sparks: {},
        gauges: {},
        misc: {},
        hoverX: null,
    };

    // ── formatting ───────────────────────────────────────────────────────
    const isNum = (v) => typeof v === "number" && isFinite(v);
    const fixed = (v, big) => v.toFixed(Math.abs(v) >= big ? 0 : Math.abs(v) >= 10 ? 1 : 2).replace(/\.0+$|(\.\d*?)0+$/, "$1");
    const fmt = {
        pct: (v) => (isNum(v) ? [fixed(v, 100), "%"] : ["—", ""]),
        bytes: (v, suffix) => {
            if (!isNum(v)) return ["—", ""];
            const units = ["B", "KiB", "MiB", "GiB", "TiB", "PiB"];
            let i = 0;
            while (Math.abs(v) >= 1024 && i < units.length - 1) {
                v /= 1024;
                i += 1;
            }
            return [fixed(v, 100), units[i] + (suffix || "")];
        },
        ms: (v) => {
            if (!isNum(v)) return ["—", ""];
            return v >= 1000 ? [fixed(v / 1000, 100), "s"] : [fixed(v, 100), "ms"];
        },
        num: (v) => {
            if (!isNum(v)) return ["—", ""];
            if (Math.abs(v) >= 1e6) return [fixed(v / 1e6, 100), "M"];
            if (Math.abs(v) >= 1e4) return [fixed(v / 1e3, 100), "k"];
            return [fixed(v, 1000), ""];
        },
        duration: (sec) => {
            if (!isNum(sec)) return ["—", ""];
            const d = Math.floor(sec / 86400);
            const h = Math.floor((sec % 86400) / 3600);
            const m = Math.floor((sec % 3600) / 60);
            if (d) return [`${d}${T.days} ${h}${T.hours}`, ""];
            if (h) return [`${h}${T.hours} ${m}${T.minutes}`, ""];
            return [`${m}${T.minutes}`, ""];
        },
    };
    const join = (pair) => (pair[1] ? `${pair[0]} ${pair[1]}` : pair[0]);
    const axis = {
        pct: (v) => `${v}%`,
        bytes: (v) => join(fmt.bytes(v)),
        rate: (v) => join(fmt.bytes(v, "/s")),
        ms: (v) => join(fmt.ms(v)),
        num: (v) => join(fmt.num(v)),
    };
    const lang = document.documentElement.lang || undefined;
    const timeFmt = (seconds) =>
        seconds <= 900
            ? new Intl.DateTimeFormat(lang, { hour: "2-digit", minute: "2-digit", second: "2-digit" })
            : seconds <= 86400
              ? new Intl.DateTimeFormat(lang, { hour: "2-digit", minute: "2-digit" })
              : new Intl.DateTimeFormat(lang, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
    const fullTime = new Intl.DateTimeFormat(lang, { dateStyle: "medium", timeStyle: "medium" });

    // ── thresholds (Grafana-like green / orange / red) ───────────────────
    const level = (v, warn, crit, inverse) => {
        if (!isNum(v)) return "";
        if (inverse) return v <= crit ? "crit" : v <= warn ? "warn" : "ok";
        return v >= crit ? "crit" : v >= warn ? "warn" : "ok";
    };

    // ── theme colors (resolved to rgb: Chart.js can't parse oklch) ───────
    const probe = document.createElement("canvas").getContext("2d", { willReadFrequently: true });
    function toRGB(color, alpha) {
        probe.clearRect(0, 0, 1, 1);
        probe.fillStyle = "#000";
        probe.fillStyle = color || "#888";
        probe.fillRect(0, 0, 1, 1);
        const [r, g, b] = probe.getImageData(0, 0, 1, 1).data;
        return `rgba(${r}, ${g}, ${b}, ${alpha === undefined ? 1 : alpha})`;
    }
    // computed color of a custom property defined with color-mix()/var() on the dashboard root
    function resolved(name) {
        const el = document.createElement("span");
        el.style.color = `var(${name})`;
        el.hidden = true;
        root.appendChild(el);
        const color = getComputedStyle(el).color;
        el.remove();
        // an unusable value (no color-mix() support, missing theme vars) inherits the root's text color
        return color && color !== getComputedStyle(root).color ? color : "";
    }
    function palette() {
        const html = getComputedStyle(document.documentElement);
        const mon = getComputedStyle(root);
        const v = (name, fallback) => html.getPropertyValue(name).trim() || fallback;
        const dark = document.documentElement.classList.contains("dark");
        return {
            dark,
            // theme accents mixed for contrast in dashboard.css (resolved through the DOM)
            primary: resolved("--mon-accent") || v("--color-primary-500", "#0ea5e9"),
            primaryLight: resolved("--mon-accent-soft") || v("--color-primary-300", "#7dd3fc"),
            accent: v("--color-accent", "#14b8a6"),
            secondary: v("--color-secondary", "#d946ef"),
            info: v("--color-info", "#38bdf8"),
            success: mon.getPropertyValue("--mon-ok").trim() || "#22c55e",
            warning: mon.getPropertyValue("--mon-warn").trim() || "#f59e0b",
            error: mon.getPropertyValue("--mon-crit").trim() || "#ef4444",
            grid: v(dark ? "--color-base-800" : "--color-base-200", "#e5e7eb"),
            text: v(dark ? "--color-base-400" : "--color-base-500", "#6b7280"),
            track: v(dark ? "--color-base-800" : "--color-base-100", "#f3f4f6"),
        };
    }
    let C = palette();
    const levelColor = (lvl) => (lvl === "crit" ? C.error : lvl === "warn" ? C.warning : C.success);

    // ── Chart.js plugins ─────────────────────────────────────────────────
    // dashed threshold lines: options.plugins.wnThresholds = [{value, color}]
    const thresholdsPlugin = {
        id: "wnThresholds",
        afterDatasetsDraw(chart, _args, opts) {
            const lines = (opts && opts.lines) || [];
            const { ctx, chartArea, scales } = chart;
            const y = scales.y;
            if (!y) return;
            ctx.save();
            for (const line of lines) {
                if (!isNum(line.value) || line.value > y.max || line.value < y.min) continue;
                const py = y.getPixelForValue(line.value);
                ctx.strokeStyle = toRGB(line.color, 0.8);
                ctx.setLineDash([4, 4]);
                ctx.lineWidth = 1;
                ctx.beginPath();
                ctx.moveTo(chartArea.left, py);
                ctx.lineTo(chartArea.right, py);
                ctx.stroke();
            }
            ctx.restore();
        },
    };
    // shared crosshair across all time-series panels (Grafana "shared tooltip")
    const crosshairPlugin = {
        id: "wnCrosshair",
        afterEvent(chart, args) {
            const e = args.event;
            if (e.type === "mouseout") {
                syncHover(null, chart);
            } else if (e.type === "mousemove" && args.inChartArea) {
                syncHover(chart.scales.x.getValueForPixel(e.x), chart);
            }
        },
        afterDraw(chart) {
            if (state.hoverX === null || !chart.scales.x) return;
            const x = chart.scales.x.getPixelForValue(state.hoverX);
            const { ctx, chartArea } = chart;
            if (x < chartArea.left || x > chartArea.right) return;
            ctx.save();
            ctx.strokeStyle = toRGB(C.text, 0.6);
            ctx.lineWidth = 1;
            ctx.beginPath();
            ctx.moveTo(x, chartArea.top);
            ctx.lineTo(x, chartArea.bottom);
            ctx.stroke();
            ctx.restore();
        },
    };

    function syncHover(x, source) {
        state.hoverX = x;
        for (const chart of Object.values(state.charts)) {
            if (chart === source || !chart.scales.x) continue;
            if (x === null || !chart.data.datasets.length) {
                chart.setActiveElements([]);
                chart.tooltip.setActiveElements([], { x: 0, y: 0 });
            } else {
                const index = nearestIndex(chart.data.datasets[0].data, x);
                if (index >= 0) {
                    const active = chart.data.datasets
                        .map((ds, datasetIndex) => ({ datasetIndex, index }))
                        .filter((a) => chart.isDatasetVisible(a.datasetIndex) && chart.data.datasets[a.datasetIndex].data[index]);
                    chart.setActiveElements(active);
                    chart.tooltip.setActiveElements(active, { x: chart.scales.x.getPixelForValue(x), y: chart.chartArea.top });
                }
            }
            chart.draw();
        }
    }

    function nearestIndex(points, x) {
        let lo = 0;
        let hi = points.length - 1;
        if (hi < 0) return -1;
        while (lo < hi) {
            const mid = (lo + hi) >> 1;
            if (points[mid].x < x) lo = mid + 1;
            else hi = mid;
        }
        if (lo > 0 && Math.abs(points[lo - 1].x - x) < Math.abs(points[lo].x - x)) lo -= 1;
        return lo;
    }

    // ── panel definitions ────────────────────────────────────────────────
    // each returns [{label, color, values, fill, axis, dash}] from the API payload
    const TIME_PANELS = {
        cpu: {
            y: { max: 100, format: axis.pct },
            thresholds: () => [{ value: 70, color: C.warning }, { value: 90, color: C.error }],
            series: (d) => [{ label: T.cpu, color: C.primary, values: d.system.cpu_percent, fill: true }],
        },
        load: {
            y: { format: axis.num },
            thresholds: (d) => [{ value: d.live && d.live.cpu_count, color: C.error }],
            series: (d) => [
                { label: T.load1, color: C.primary, values: d.system.load_1 },
                { label: T.load5, color: C.accent, values: d.system.load_5 },
                { label: T.load15, color: C.secondary, values: d.system.load_15 },
            ],
        },
        mem: {
            y: { format: axis.bytes, max: (d) => d.live && d.live.mem_total },
            y1: { format: axis.pct, max: 100 },
            series: (d) => [
                { label: T.memUsed, color: C.primary, values: d.system.mem_used, fill: true },
                { label: T.swap, color: C.warning, values: d.system.swap_percent, axis: "y1", dash: true },
            ],
        },
        disk_io: {
            y: { format: axis.rate },
            series: (d) => [
                { label: T.read, color: C.accent, values: d.system.disk_read_bytes, fill: true },
                { label: T.write, color: C.secondary, values: d.system.disk_write_bytes, fill: true },
            ],
        },
        net: {
            y: { format: axis.rate },
            series: (d) => [
                { label: T.recv, color: C.primary, values: d.system.net_recv_bytes, fill: true },
                { label: T.sent, color: C.accent, values: d.system.net_sent_bytes, fill: true },
            ],
        },
        disk_pct: {
            y: { max: 100, format: axis.pct },
            thresholds: () => [{ value: 80, color: C.warning }, { value: 90, color: C.error }],
            series: (d) => [{ label: T.disk, color: C.primary, values: d.system.disk_percent, fill: true }],
        },
        throughput: {
            requests: true,
            stacked: true,
            y: { format: axis.num },
            series: (d) => [
                { label: T.ok, color: C.success, values: d.requests.series.ok, fill: true },
                { label: T.c4xx, color: C.warning, values: d.requests.series["4xx"], fill: true },
                { label: T.c5xx, color: C.error, values: d.requests.series["5xx"], fill: true },
            ],
        },
        latency: {
            requests: true,
            y: { format: axis.ms },
            thresholds: () => [{ value: 1000, color: C.error }],
            series: (d) => [
                { label: T.p50, color: C.primaryLight, values: d.requests.series.p50 },
                { label: T.p95, color: C.primary, values: d.requests.series.p95, fill: true },
                { label: T.p99, color: C.secondary, values: d.requests.series.p99, dash: true },
            ],
        },
        deps: {
            y: { format: axis.ms },
            series: (d) => [
                { label: T.db, color: C.primary, values: d.system.db_latency_ms },
                { label: T.cache, color: C.accent, values: d.system.cache_latency_ms },
            ],
        },
        proc: {
            y: { format: axis.bytes },
            y1: { format: axis.num },
            series: (d) => [
                { label: T.rss, color: C.primary, values: d.system.proc_rss, fill: true },
                { label: T.threads, color: C.secondary, values: d.system.proc_threads, axis: "y1", dash: true },
            ],
        },
    };

    function points(t, values) {
        const out = [];
        for (let i = 0; i < t.length; i += 1) {
            out.push({ x: t[i], y: values && isNum(values[i]) ? values[i] : null });
        }
        return out;
    }

    function gradient(chart, color) {
        const { ctx, chartArea } = chart;
        if (!chartArea) return toRGB(color, 0.15);
        const g = ctx.createLinearGradient(0, chartArea.top, 0, chartArea.bottom);
        g.addColorStop(0, toRGB(color, 0.32));
        g.addColorStop(1, toRGB(color, 0.02));
        return g;
    }

    function scaleOptions(def, d, key) {
        const cfg = def[key];
        if (!cfg) return undefined;
        const max = typeof cfg.max === "function" ? cfg.max(d) : cfg.max;
        return {
            position: key === "y1" ? "right" : "left",
            beginAtZero: true,
            max: isNum(max) ? max : undefined,
            stacked: !!def.stacked,
            grid: { color: toRGB(C.grid), drawOnChartArea: key !== "y1" },
            border: { display: false },
            ticks: { color: toRGB(C.text), callback: cfg.format, maxTicksLimit: 5, font: { size: 11 } },
        };
    }

    function buildTimeChart(key, d) {
        const canvas = root.querySelector(`canvas[data-chart="${key}"]`);
        const def = TIME_PANELS[key];
        const src = def.requests ? d.requests.series : d.system;
        const series = def.series(d);
        const scales = {
            x: {
                type: "linear",
                grid: { color: toRGB(C.grid) },
                border: { display: false },
                ticks: {
                    color: toRGB(C.text),
                    maxTicksLimit: 7,
                    maxRotation: 0,
                    font: { size: 11 },
                    callback: (v) => timeFmt(d.seconds).format(new Date(v)),
                },
            },
            y: scaleOptions(def, d, "y"),
        };
        if (def.y1) scales.y1 = scaleOptions(def, d, "y1");

        const chart = new Chart(canvas, {
            type: "line",
            data: {
                datasets: series.map((s) => ({
                    label: s.label,
                    data: points(src.t, s.values),
                    yAxisID: s.axis || "y",
                    borderColor: toRGB(s.color),
                    backgroundColor: s.fill ? (ctx) => gradient(ctx.chart, s.color) : toRGB(s.color, 0.2),
                    fill: s.fill ? (def.stacked ? "stack" : "origin") : false,
                    borderDash: s.dash ? [5, 4] : undefined,
                    borderWidth: 1.6,
                    pointRadius: 0,
                    pointHoverRadius: 3,
                    tension: 0.25,
                    spanGaps: false,
                    stack: def.stacked ? "s" : undefined,
                })),
            },
            options: {
                maintainAspectRatio: false,
                animation: false,
                parsing: false,
                normalized: true,
                interaction: { mode: "index", intersect: false },
                scales,
                plugins: {
                    legend: {
                        position: "bottom",
                        align: "start",
                        labels: { color: toRGB(C.text), boxWidth: 10, boxHeight: 2, font: { size: 11 } },
                    },
                    tooltip: {
                        backgroundColor: C.dark ? "rgba(17,24,39,0.95)" : "rgba(255,255,255,0.97)",
                        titleColor: C.dark ? "#f3f4f6" : "#111827",
                        bodyColor: C.dark ? "#d1d5db" : "#374151",
                        borderColor: toRGB(C.grid),
                        borderWidth: 1,
                        padding: 10,
                        boxWidth: 8,
                        boxHeight: 8,
                        usePointStyle: true,
                        callbacks: {
                            title: (items) => (items.length ? fullTime.format(new Date(items[0].parsed.x)) : ""),
                            label: (item) => {
                                const cfg = item.dataset.yAxisID === "y1" ? def.y1 : def.y;
                                return ` ${item.dataset.label}: ${isNum(item.parsed.y) ? cfg.format(item.parsed.y) : "—"}`;
                            },
                        },
                    },
                    wnThresholds: { lines: def.thresholds ? def.thresholds(d) : [] },
                },
            },
            plugins: [thresholdsPlugin, crosshairPlugin],
        });
        state.charts[key] = chart;
        return chart;
    }

    function updateTimeChart(key, d) {
        const def = TIME_PANELS[key];
        let chart = state.charts[key];
        if (!chart) chart = buildTimeChart(key, d);
        const src = def.requests ? d.requests.series : d.system;
        def.series(d).forEach((s, i) => {
            chart.data.datasets[i].data = points(src.t, s.values);
        });
        const now = Date.parse(d.server_time);
        chart.options.scales.x.min = now - d.seconds * 1000;
        chart.options.scales.x.max = now;
        chart.options.scales.x.ticks.callback = (v) => timeFmt(d.seconds).format(new Date(v));
        for (const k of ["y", "y1"]) {
            if (def[k] && typeof def[k].max === "function") {
                const max = def[k].max(d);
                chart.options.scales[k].max = isNum(max) ? max : undefined;
            }
        }
        chart.options.plugins.wnThresholds.lines = def.thresholds ? def.thresholds(d) : [];
        chart.update("none");

        const empty = !src.t.length;
        const nodata = root.querySelector(`[data-nodata="${key}"]`);
        nodata.textContent = T.noData;
        nodata.hidden = !empty;
        const meta = root.querySelector(`[data-meta="${key}"]`);
        if (meta) meta.textContent = src.bucket ? `${src.bucket}s` : "";
    }

    // ── stat panels with sparklines ──────────────────────────────────────
    function setStat(key, value, sub, lvl, sparkValues, sparkT) {
        const panel = root.querySelector(`[data-stat="${key}"]`);
        if (!panel) return;
        panel.querySelector("[data-value]").textContent = value[0];
        panel.querySelector("[data-unit]").textContent = value[1] || "";
        panel.querySelector("[data-sub]").textContent = sub || " ";
        panel.dataset.level = lvl || "";
        const canvas = panel.querySelector("canvas");
        if (!sparkValues) {
            canvas.hidden = true;
            return;
        }
        const color = lvl ? levelColor(lvl) : C.primary;
        let chart = state.sparks[key];
        const data = points(sparkT, sparkValues);
        if (!chart) {
            chart = state.sparks[key] = new Chart(canvas, {
                type: "line",
                data: { datasets: [{ data, borderWidth: 1.5, pointRadius: 0, tension: 0.3, fill: "origin" }] },
                options: {
                    maintainAspectRatio: false,
                    animation: false,
                    parsing: false,
                    events: [],
                    plugins: { legend: { display: false }, tooltip: { enabled: false } },
                    scales: { x: { type: "linear", display: false }, y: { display: false, beginAtZero: true } },
                },
            });
        }
        const ds = chart.data.datasets[0];
        ds.data = data;
        ds.borderColor = toRGB(color, 0.9);
        ds.backgroundColor = (ctx) => {
            const area = ctx.chart.chartArea;
            if (!area) return toRGB(color, 0.15);
            const g = ctx.chart.ctx.createLinearGradient(0, area.top, 0, area.bottom);
            g.addColorStop(0, toRGB(color, 0.28));
            g.addColorStop(1, toRGB(color, 0));
            return g;
        };
        chart.update("none");
    }

    function sumSeries(...lists) {
        const n = Math.max(0, ...lists.map((l) => (l ? l.length : 0)));
        const out = [];
        for (let i = 0; i < n; i += 1) {
            out.push(lists.reduce((acc, l) => acc + (l && isNum(l[i]) ? l[i] : 0), 0));
        }
        return out;
    }

    function renderStats(d) {
        const live = d.live || {};
        const sys = d.system;
        const req = d.requests;
        const sum = req.summary;
        const rs = req.series;
        const cores = live.cpu_count || 1;

        setStat("uptime", fmt.duration(live.uptime), live.boot_time ? fullTime.format(new Date(live.boot_time)) : "", "");
        setStat("cpu", fmt.pct(live.cpu_percent), `${cores} ${T.cores}`, level(live.cpu_percent, 70, 90), sys.cpu_percent, sys.t);
        setStat(
            "mem",
            fmt.pct(live.mem_percent),
            `${join(fmt.bytes(live.mem_used))} ${T.of} ${join(fmt.bytes(live.mem_total))}`,
            level(live.mem_percent, 80, 90),
            sys.mem_percent,
            sys.t,
        );
        setStat(
            "disk",
            fmt.pct(live.disk_percent),
            `${join(fmt.bytes(live.disk_used))} ${T.of} ${join(fmt.bytes(live.disk_total))}`,
            level(live.disk_percent, 80, 90),
            sys.disk_percent,
            sys.t,
        );
        setStat(
            "load",
            fmt.num(live.load_1),
            isNum(live.load_5) ? `${T.load5} ${fixed(live.load_5, 100)} · ${T.load15} ${fixed(live.load_15, 100)} · ${cores} ${T.cores}` : "",
            isNum(live.load_1) ? level(live.load_1 / cores, 0.7, 1) : "",
            sys.load_1,
            sys.t,
        );
        const total = sumSeries(rs.ok, rs["4xx"], rs["5xx"]);
        setStat("rpm", fmt.num(sum.rpm), `${T.perMin} · ${sum.total.toLocaleString()} ${T.requests}`, "", total, rs.t);
        const errSeries = total.map((v, i) => (v ? ((rs["5xx"][i] || 0) * 100) / v : 0));
        setStat(
            "errors",
            fmt.pct(sum.error_rate),
            `${(req.status_classes["5xx"] || 0).toLocaleString()} 5xx · ${(req.status_classes["4xx"] || 0).toLocaleString()} 4xx`,
            sum.total ? level(sum.error_rate, 1, 5) : "",
            errSeries,
            rs.t,
        );
        setStat(
            "p95",
            fmt.ms(sum.p95),
            isNum(sum.p50) ? `${T.p50} ${join(fmt.ms(sum.p50))} · ${T.p99} ${join(fmt.ms(sum.p99))}` : "",
            isNum(sum.p95) ? level(sum.p95, 300, 1000) : "",
            rs.p95,
            rs.t,
        );
    }

    // ── gauges, cores, responses, table ──────────────────────────────────
    function renderGauge(key, value) {
        const box = root.querySelector(`[data-gauge="${key}"]`);
        const lvl = level(value, key === "cpu" ? 70 : 80, 90);
        const v = isNum(value) ? Math.min(100, Math.max(0, value)) : 0;
        let chart = state.gauges[key];
        if (!chart) {
            chart = state.gauges[key] = new Chart(box.querySelector("canvas"), {
                type: "doughnut",
                data: { datasets: [{ data: [0, 100], borderWidth: 0, borderRadius: 4 }] },
                options: {
                    maintainAspectRatio: false,
                    animation: { duration: 400 },
                    rotation: -90,
                    circumference: 180,
                    cutout: "78%",
                    events: [],
                    plugins: { legend: { display: false }, tooltip: { enabled: false } },
                },
            });
        }
        chart.data.datasets[0].data = [v, 100 - v];
        chart.data.datasets[0].backgroundColor = [toRGB(levelColor(lvl)), toRGB(C.track)];
        chart.update();
        box.querySelector("strong").textContent = join(fmt.pct(value));
    }

    function renderCores(perCore) {
        const box = root.querySelector("[data-cores]");
        if (!perCore || !perCore.length) {
            box.replaceChildren();
            return;
        }
        if (box.children.length !== perCore.length) {
            box.replaceChildren(
                ...perCore.map((_, i) => {
                    const el = document.createElement("div");
                    el.className = "wn-core";
                    el.title = `CPU ${i}`;
                    el.append(document.createElement("i"), document.createElement("b"));
                    return el;
                }),
            );
        }
        perCore.forEach((v, i) => {
            const el = box.children[i];
            el.style.setProperty("--mon-core", levelColor(level(v, 70, 90)));
            el.querySelector("i").style.height = `${Math.min(100, v)}%`;
            el.querySelector("b").textContent = `${Math.round(v)}%`;
        });
    }

    function renderResponses(d) {
        const classes = d.requests.status_classes || {};
        const labels = ["2xx", "3xx", "4xx", "5xx"];
        const colors = [C.success, C.info, C.warning, C.error];
        let chart = state.misc.status;
        const values = labels.map((l) => classes[l] || 0);
        if (!chart) {
            chart = state.misc.status = new Chart(root.querySelector('canvas[data-chart="status"]'), {
                type: "doughnut",
                data: { labels, datasets: [{ data: values, borderWidth: 0, spacing: 2 }] },
                options: {
                    maintainAspectRatio: false,
                    cutout: "68%",
                    animation: { duration: 300 },
                    plugins: {
                        legend: { position: "right", labels: { color: toRGB(C.text), boxWidth: 10, font: { size: 11 } } },
                        tooltip: {
                            callbacks: {
                                label: (item) => {
                                    const total = item.dataset.data.reduce((a, b) => a + b, 0) || 1;
                                    return ` ${item.label}: ${item.raw.toLocaleString()} (${((item.raw * 100) / total).toFixed(1)}%)`;
                                },
                            },
                        },
                    },
                },
            });
        }
        chart.data.datasets[0].data = values;
        chart.data.datasets[0].backgroundColor = colors.map((c) => toRGB(c));
        chart.update();

        const apdex = root.querySelector("[data-apdex]");
        const score = d.requests.summary.apdex;
        apdex.querySelector("strong").textContent = isNum(score) ? score.toFixed(2) : "—";
        apdex.dataset.level = isNum(score) ? level(score, 0.94, 0.85, true) : "";
        apdex.title = !isNum(score) ? "" : score >= 0.94 ? T.satisfied : score >= 0.85 ? T.good : score >= 0.7 ? T.fair : T.poor;
    }

    // solid badges (soft ones use the status color as text: unreadable in some themes);
    // full class names so Tailwind's scanner keeps them in styles.css
    const METHOD_BADGE = {
        GET: "ui-badge-info", HEAD: "ui-badge-info", OPTIONS: "ui-badge-info",
        POST: "ui-badge-warning", PUT: "ui-badge-warning", PATCH: "ui-badge-warning",
        DELETE: "ui-badge-error",
    };

    function renderEndpoints(d) {
        const body = root.querySelector("[data-endpoints]");
        const rows = d.requests.top_endpoints || [];
        if (!rows.length) {
            const tr = document.createElement("tr");
            const td = document.createElement("td");
            td.colSpan = 7;
            td.className = "wn-empty";
            td.textContent = T.noData;
            tr.append(td);
            body.replaceChildren(tr);
            return;
        }
        const maxTotal = Math.max(...rows.map((r) => r.total || 0)) || 1;
        const grandTotal = rows.reduce((a, r) => a + (r.total || 0), 0) || 1;
        const cell = (text, cls) => {
            const td = document.createElement("td");
            if (cls) td.className = cls;
            td.textContent = text;
            return td;
        };
        body.replaceChildren(
            ...rows.map((r) => {
                const tr = document.createElement("tr");
                const ep = document.createElement("td");
                ep.className = "path";
                const method = document.createElement("span");
                method.className = `wn-method ui-badge ui-badge-sm ${METHOD_BADGE[r.method] || "ui-badge-neutral"}`;
                method.textContent = r.method || "—";
                ep.title = r.path;
                ep.append(method, document.createTextNode(r.path)); // textContent only: paths are user-controlled
                const p95 = cell(join(fmt.ms(r.p95)), `num wn-level-${level(r.p95, 300, 1000) || "ok"}`);
                const err = cell(`${fixed(r.error_rate, 100)}%`, `num ${r.error_rate ? `wn-level-${level(r.error_rate, 1, 5)}` : ""}`);
                const share = document.createElement("td");
                share.innerHTML = '<div class="wn-share"><progress class="ui-progress" max="100" aria-hidden="true"></progress><span></span></div>';
                share.querySelector("progress").value = ((r.total || 0) * 100) / maxTotal;
                share.querySelector("span").textContent = `${(((r.total || 0) * 100) / grandTotal).toFixed(1)}%`;
                tr.append(ep, cell(r.count.toLocaleString(), "num"), cell(join(fmt.ms(r.avg)), "num"), p95, cell(join(fmt.ms(r.max)), "num"), err, share);
                return tr;
            }),
        );
    }

    // ── banner, toolbar ──────────────────────────────────────────────────
    function banner(message, isError) {
        const el = root.querySelector("[data-banner]");
        el.hidden = !message;
        el.classList.toggle("ui-alert-error", !!isError);
        el.classList.toggle("ui-alert-warning", !isError);
        // role=status: rewriting the same text would be announced again on every refresh
        if (el.textContent !== (message || "")) el.textContent = message || "";
    }

    function renderToolbar(d) {
        const select = root.querySelector("[data-host-select]");
        const hosts = d.hosts || [d.host];
        if (select.options.length !== hosts.length || [...select.options].some((o, i) => o.value !== hosts[i])) {
            select.replaceChildren(
                ...hosts.map((h) => {
                    const o = document.createElement("option");
                    o.value = h;
                    o.textContent = h === d.local_host ? `${h} ★` : h;
                    return o;
                }),
            );
        }
        select.value = d.host;
        root.querySelector("[data-updated]").textContent = `${T.updated} ${new Intl.DateTimeFormat(lang, { timeStyle: "medium" }).format(new Date())}`;
        root.querySelector("[data-live]").hidden = !REFRESH_MS[state.refresh];
        root.querySelectorAll("[data-range-btn]").forEach((b) => {
            const on = b.dataset.rangeBtn === state.range;
            b.setAttribute("aria-pressed", String(on));
            b.classList.toggle("ui-btn-primary", on);
        });

        const notes = [];
        if (d.host !== d.local_host) notes.push(T.remoteHost);
        else if (d.collector.stale) notes.push(T.staleCollector);
        if (d.requests.summary.truncated) notes.push(T.truncated);
        banner(notes.join(" "), false);
    }

    function render(d) {
        renderToolbar(d);
        renderStats(d);
        const live = d.live || {};
        renderGauge("cpu", live.cpu_percent);
        renderGauge("mem", live.mem_percent);
        renderGauge("disk", live.disk_percent);
        renderCores(live.per_core);
        for (const key of Object.keys(TIME_PANELS)) updateTimeChart(key, d);
        renderResponses(d);
        renderEndpoints(d);
    }

    // ── data loading & refresh loop ──────────────────────────────────────
    async function load() {
        clearTimeout(state.timer);
        if (state.controller) state.controller.abort();
        const controller = (state.controller = new AbortController());
        const btn = root.querySelector("[data-refresh-now]");
        btn.classList.add("is-loading");
        try {
            const params = new URLSearchParams({ range: state.range, host: state.host });
            const res = await fetch(`${state.api}?${params}`, {
                headers: { Accept: "application/json" },
                credentials: "same-origin",
                signal: controller.signal,
            });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const data = await res.json();
            if (controller !== state.controller) return; // superseded while parsing
            state.data = data;
            state.host = data.host;
            render(data);
        } catch (err) {
            if (err.name === "AbortError" || controller !== state.controller) return;
            banner(`${T.fetchError}: ${err.message}`, true);
        } finally {
            // only the latest request owns the spinner and the refresh timer
            if (controller === state.controller) {
                btn.classList.remove("is-loading");
                root.classList.remove("is-loading");
                schedule();
            }
        }
    }

    function schedule() {
        clearTimeout(state.timer);
        const ms = REFRESH_MS[state.refresh];
        if (ms && !document.hidden) state.timer = setTimeout(load, ms);
    }

    function syncUrl() {
        const url = new URL(window.location.href);
        url.searchParams.set("range", state.range);
        url.searchParams.set("refresh", state.refresh);
        url.searchParams.set("host", state.host);
        window.history.replaceState(null, "", url);
    }

    // ── events ───────────────────────────────────────────────────────────
    root.querySelectorAll("[data-range-btn]").forEach((btn) =>
        btn.addEventListener("click", () => {
            state.range = btn.dataset.rangeBtn;
            syncUrl();
            load();
        }),
    );
    root.querySelector("[data-refresh-select]").addEventListener("change", (e) => {
        state.refresh = e.target.value;
        syncUrl();
        root.querySelector("[data-live]").hidden = !REFRESH_MS[state.refresh];
        schedule();
    });
    root.querySelector("[data-refresh-now]").addEventListener("click", load);
    root.querySelector("[data-host-select]").addEventListener("change", (e) => {
        state.host = e.target.value;
        syncUrl();
        load();
    });
    document.addEventListener("visibilitychange", () => {
        if (document.hidden) clearTimeout(state.timer);
        else if (REFRESH_MS[state.refresh]) load(); // catch up after being in the background
    });

    // collapsible rows, remembered per browser
    let collapsed = {};
    try {
        collapsed = JSON.parse(localStorage.getItem(ROWS_KEY) || "{}");
    } catch (e) {}
    root.querySelectorAll(".wn-row").forEach((row) => {
        const key = row.dataset.row;
        const head = row.querySelector(".wn-row-head");
        const apply = () => {
            row.classList.toggle("is-collapsed", !!collapsed[key]);
            head.setAttribute("aria-expanded", String(!collapsed[key]));
        };
        apply();
        head.addEventListener("click", () => {
            collapsed[key] = !collapsed[key];
            apply();
            try {
                localStorage.setItem(ROWS_KEY, JSON.stringify(collapsed));
            } catch (e) {}
            if (!collapsed[key]) Object.values(state.charts).forEach((c) => c.resize());
        });
    });

    // re-color everything when the admin theme / dark mode changes
    new MutationObserver(() => {
        C = palette();
        for (const group of [state.charts, state.sparks, state.gauges, state.misc]) {
            for (const key of Object.keys(group)) {
                group[key].destroy();
                delete group[key];
            }
        }
        if (state.data) render(state.data);
    }).observe(document.documentElement, { attributes: true, attributeFilter: ["class", "data-theme"] });

    Chart.defaults.font.family = getComputedStyle(document.body).fontFamily || "Inter";
    root.classList.add("is-loading");
    load();
})();
