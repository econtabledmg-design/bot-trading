import json, time, urllib.request
SYMS = ['BTC', 'ETH', 'SOL', 'XRP', 'SUI', 'BNB', 'DOGE', 'ADA']
DAY = 86400000; FEE = .0005; SLIP = .0002
HOSTS = ['https://data-api.binance.vision', 'https://api.binance.com']

def get(s):
    for h in HOSTS:
        try:
            rq = urllib.request.Request(f'{h}/api/v3/klines?symbol={s}USDT&interval=15m&limit=120', headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(rq, timeout=15) as r:
                return json.load(r)
        except Exception as e:
            print('error', h, s, e)
    return None

def ema(a, n):
    k = 2 / (n + 1); e = a[0]; o = []
    for v in a:
        e = v * k + e * (1 - k); o.append(e)
    return o

def rsi(c, n=14):
    g = l = 0
    for i in range(len(c) - n, len(c)):
        d = c[i] - c[i - 1]
        if d > 0: g += d
        else: l -= d
    return 100 if l == 0 else 100 - 100 / (1 + g / l)

def atr(h, l, c, n=14):
    return sum(max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1])) for i in range(len(c) - n, len(c))) / n

def main():
    now = int(time.time() * 1000)
    try:
        S = json.load(open('state.json'))
    except Exception:
        S = {'t0': now, 'cap': 1000, 'bal': 1000, 'pos': [], 'tr': [], 'eq': [], 'btc0': None, 'btcN': None, 'cool': {}}
    rows = []; px = {}
    for s in SYMS:
        k = get(s)
        if not k or len(k) < 60: continue
        c = [float(x[4]) for x in k]; h = [float(x[2]) for x in k]; l = [float(x[3]) for x in k]; v = [float(x[5]) for x in k]
        n = len(c); p = c[-1]; px[s] = p
        e20 = ema(c, 20)[-1]; e50 = ema(c, 50)[-1]
        tr = 1 if e20 > e50 and p > e20 else (-1 if e20 < e50 and p < e20 else 0)
        vr = v[n - 2] / (sum(v[n - 22:n - 2]) / 20); a = atr(h, l, c); vp = a / p * 100; r = rsi(c)
        sc = tr * 45 + max(-30, min(30, (r - 50) * 1.2)) + tr * (15 if vr > 1.2 else 0)
        ok = .1 <= vp <= 2.5 and vr >= .7
        dec = 1 if ok and sc >= 55 and r < 75 else (-1 if ok and sc <= -55 and r > 25 else 0)
        rows.append({'s': s, 'p': p, 'tr': tr, 'vr': vr, 'vp': vp, 'r': r, 'sc': sc, 'pass': ok, 'dec': dec, 'a': a})
    S['upd'] = now; S['ok'] = len(rows); S['rows'] = rows
    if not rows:
        json.dump(S, open('state.json', 'w'), separators=(',', ':')); return
    if 'BTC' in px:
        if not S['btc0']: S['btc0'] = px['BTC']
        S['btcN'] = px['BTC']
    def unreal(): return sum(q['side'] * (px.get(q['s'], q.get('last', q['e'])) - q['e']) * q['q'] for q in S['pos'])
    for q in list(S['pos']):
        p = px.get(q['s'])
        if p is None: continue
        q['last'] = p; sd = q['side']; why = None
        if sd * (p - q['stop']) <= 0: why = 'stop'
        elif sd * (p - q['tp']) >= 0: why = 'objetivo'
        elif now - q['t'] > DAY: why = 'tiempo'
        if why:
            pnl = sd * (p - q['e']) * q['q'] - FEE * 2 * q['e'] * q['q']
            S['bal'] += pnl
            S['tr'].append({'s': q['s'], 'side': sd, 't0': q['t'], 't1': now, 'pnl': pnl, 'why': why})
            S['cool'][q['s']] = now; S['pos'].remove(q)
    eq = S['bal'] + unreal()
    d = (now - S['t0']) // DAY + 1; t = S['t0'] + (d - 1) * DAY; e0 = S['cap']
    for x in S['eq']:
        if x[0] < t: e0 = x[1]
        else: break
    S['block'] = eq - e0 < -.03 * e0
    if not S['block']:
        for r in sorted([x for x in rows if x['dec']], key=lambda x: -abs(x['sc'])):
            if len(S['pos']) >= 3 or any(q['s'] == r['s'] for q in S['pos']) or now - S['cool'].get(r['s'], 0) < 3600000: continue
            e = r['p'] * (1 + r['dec'] * SLIP); sd = 1.5 * r['a']; q = eq * .01 / sd
            if q * e > eq * .25: q = eq * .25 / e
            S['pos'].append({'s': r['s'], 'side': r['dec'], 'e': e, 'q': q, 'stop': e - r['dec'] * sd, 'tp': e + r['dec'] * 2.5 * r['a'], 't': now, 'last': r['p']})
    if not S['eq'] or now - S['eq'][-1][0] > 250000:
        S['eq'].append([now, S['bal'] + unreal()])
    S['eq'] = S['eq'][-20000:]; S['tr'] = S['tr'][-3000:]
    json.dump(S, open('state.json', 'w'), separators=(',', ':'))

if __name__ == '__main__':
    main()
