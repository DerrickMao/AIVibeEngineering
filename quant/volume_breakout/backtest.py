"""
放量突破策略 —— 日频回测

信号（第 T 日收盘后计算）：
    1. 收盘价 > 前 N 日（默认 20）最高收盘价            —— 价格突破
    2. 成交量 >= 前 M 日（默认 5）平均成交量 × K（默认 2） —— 放量
    3. 成交额 >= 下限（默认 1 亿元）                    —— 流动性过滤
交易：
    - T+1 日开盘买入；开盘一字/涨停买不进则放弃
    - 最多同时持有 max_pos 只，每只约 总资产/max_pos；信号多于空位时按量比从大到小取
    - 卖出：收盘跌破 MA10 → 次日开盘卖；盘中触及止损（成本 -8%）→ 按止损价（低开则按开盘价）卖
    - 遵守 T+1：买入当天不能卖；跌停封板卖不出则顺延
费用：佣金万 2.5（最低 5 元）、过户费十万分之 1、卖出印花税千分之 0.5、单边滑点 0.1%

数据源（--source）：
    xtdata     在装了 QMT 的 Windows 上跑，用 miniQMT 的行情（推荐，和实盘同源）
    akshare    pip install akshare，走东方财富公开接口
    csv        自备数据：目录下每只股票一个 600519.SH.csv，列 date,open,high,low,close,volume,amount
    synthetic  随机生成的假数据，只用于检查程序能跑通，结果没有任何意义
"""

from __future__ import annotations

import argparse
import math
import os
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

FIELDS = ["open", "high", "low", "close", "volume", "amount"]
INDEX_NAMES = {"000300": "沪深300", "000905": "中证500", "000852": "中证1000"}


# --------------------------------------------------------------------------- 参数


@dataclass
class Params:
    breakout_days: int = 20
    vol_ma_days: int = 5
    vol_mult: float = 2.0
    min_amount: float = 1e8
    max_price: float = 0.0  # 0 = 不限
    exit_ma_days: int = 10
    stop_loss: float = 0.08
    max_hold_days: int = 0  # 0 = 不限
    max_pos: int = 5
    init_cash: float = 200_000.0
    commission: float = 0.00025
    min_commission: float = 5.0
    transfer_fee: float = 0.00001
    stamp_duty: float = 0.0005
    slippage: float = 0.001


# --------------------------------------------------------------------------- 数据


def _to_qmt_code(code: str) -> str:
    code = code.strip()
    if "." in code:
        return code.upper()
    if code.startswith(("6", "9")):
        return f"{code}.SH"
    if code.startswith(("4", "8")):
        return f"{code}.BJ"
    return f"{code}.SZ"


def load_xtdata(index: str, start: str, end: str):
    from xtquant import xtdata

    codes = xtdata.get_stock_list_in_sector(INDEX_NAMES.get(index, index))
    names = {c: (xtdata.get_instrument_detail(c) or {}).get("InstrumentName", "") for c in codes}
    codes = [c for c in codes if "ST" not in names[c]]
    for c in codes:
        xtdata.download_history_data(c, period="1d", start_time=start, end_time=end)
    raw = xtdata.get_market_data_ex(FIELDS, codes, period="1d", start_time=start, end_time=end,
                                    dividend_type="front")
    data = {}
    for c, df in raw.items():
        if df is None or df.empty:
            continue
        df = df[FIELDS].copy()
        df.index = pd.to_datetime(df.index.astype(str))
        data[c] = df
    bench_code = f"{index}.SH"
    xtdata.download_history_data(bench_code, period="1d", start_time=start, end_time=end)
    b = xtdata.get_market_data_ex(["close"], [bench_code], period="1d", start_time=start, end_time=end)
    bench = None
    if bench_code in b and not b[bench_code].empty:
        bench = b[bench_code]["close"]
        bench.index = pd.to_datetime(bench.index.astype(str))
    return data, bench


def load_akshare(index: str, start: str, end: str, cache_dir: str):
    import akshare as ak

    os.makedirs(cache_dir, exist_ok=True)
    cons = ak.index_stock_cons_csindex(symbol=index)
    cons = cons[~cons["成分券名称"].str.contains("ST")]
    data = {}
    for i, sym in enumerate(cons["成分券代码"].astype(str).str.zfill(6), 1):
        code = _to_qmt_code(sym)
        path = os.path.join(cache_dir, f"{code}.csv")
        if os.path.exists(path):
            df = pd.read_csv(path, index_col=0, parse_dates=True)
        else:
            try:
                h = ak.stock_zh_a_hist(symbol=sym, period="daily", start_date=start, end_date=end, adjust="qfq")
            except Exception as e:  # 个别股票拉取失败不影响整体
                print(f"  跳过 {code}: {e}")
                continue
            if h is None or h.empty:
                continue
            df = pd.DataFrame({
                "open": h["开盘"], "high": h["最高"], "low": h["最低"], "close": h["收盘"],
                "volume": h["成交量"], "amount": h["成交额"],
            })
            df.index = pd.to_datetime(h["日期"])
            df.to_csv(path)
        data[code] = df
        if i % 50 == 0:
            print(f"  已加载 {i}/{len(cons)}")
    bench = None
    try:
        b = ak.stock_zh_index_daily(symbol=f"sh{index}")
        bench = pd.Series(b["close"].values, index=pd.to_datetime(b["date"]))
    except Exception as e:
        print(f"  基准指数拉取失败: {e}")
    return data, bench


def load_csv_dir(path: str):
    data = {}
    for f in sorted(os.listdir(path)):
        if f.endswith(".csv") and f != "benchmark.csv":
            df = pd.read_csv(os.path.join(path, f), index_col=0, parse_dates=True)
            data[f[:-4]] = df[FIELDS]
    bench = None
    bp = os.path.join(path, "benchmark.csv")
    if os.path.exists(bp):
        bench = pd.read_csv(bp, index_col=0, parse_dates=True)["close"]
    return data, bench


def make_synthetic(n_stocks: int = 60, start: str = "20200101", end: str = "20251231", seed: int = 7):
    """随机游走 + 偶发放量事件。仅用于测试程序，不代表任何真实市场。"""
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range(start, end)
    data = {}
    for k in range(n_stocks):
        n = len(dates)
        ret = rng.normal(0.0002, 0.022, n)
        vol = rng.lognormal(16, 0.35, n)
        for t in rng.choice(np.arange(30, n - 30), size=8, replace=False):
            vol[t] *= rng.uniform(2.0, 4.0)
            ret[t] += 0.04
            ret[t + 1:t + 10] += rng.normal(0.002, 0.003)
        ret = np.clip(ret, -0.0995, 0.0995)
        close = 10 * np.exp(np.cumsum(np.log1p(ret)))
        prev = np.r_[close[0], close[:-1]]
        opn = prev * (1 + np.clip(rng.normal(0, 0.006, n), -0.09, 0.09))
        high = np.maximum(opn, close) * (1 + np.abs(rng.normal(0, 0.008, n)))
        low = np.minimum(opn, close) * (1 - np.abs(rng.normal(0, 0.008, n)))
        code = f"{600000 + k}.SH"
        data[code] = pd.DataFrame({"open": opn, "high": high, "low": low, "close": close,
                                   "volume": vol / 100, "amount": vol * close}, index=dates)
    return data, None


# --------------------------------------------------------------------------- 回测


def limit_pct(code: str) -> float:
    if code.startswith(("300", "301", "688", "689")):
        return 0.20
    if code.endswith(".BJ"):
        return 0.30
    return 0.10


@dataclass
class Position:
    shares: int
    entry_price: float
    entry_cost: float  # 含买入费用
    entry_idx: int


@dataclass
class Broker:
    p: Params
    cash: float
    positions: dict = field(default_factory=dict)
    trades: list = field(default_factory=list)

    def fees(self, amount: float, sell: bool) -> float:
        f = max(amount * self.p.commission, self.p.min_commission) + amount * self.p.transfer_fee
        if sell:
            f += amount * self.p.stamp_duty
        return f

    def buy(self, code, price, budget, idx, date) -> bool:
        px = price * (1 + self.p.slippage)
        lots = math.floor(budget / (px * 100))
        while lots > 0 and lots * 100 * px + self.fees(lots * 100 * px, False) > self.cash:
            lots -= 1
        if lots <= 0:
            return False
        amt = lots * 100 * px
        fee = self.fees(amt, False)
        self.cash -= amt + fee
        self.positions[code] = Position(lots * 100, px, amt + fee, idx)
        return True

    def sell(self, code, price, idx, date, reason):
        pos = self.positions.pop(code)
        px = price * (1 - self.p.slippage)
        amt = pos.shares * px
        fee = self.fees(amt, True)
        self.cash += amt - fee
        self.trades.append({
            "code": code, "entry_date": None, "exit_date": date, "shares": pos.shares,
            "entry_price": round(pos.entry_price, 4), "exit_price": round(px, 4),
            "pnl": round(amt - fee - pos.entry_cost, 2),
            "ret": (amt - fee) / pos.entry_cost - 1,
            "hold_days": idx - pos.entry_idx, "reason": reason, "_entry_idx": pos.entry_idx,
        })


def run_backtest(data: dict, p: Params, start: str | None = None):
    panel = {f: pd.DataFrame({c: d[f] for c, d in data.items()}).sort_index() for f in FIELDS}
    O, H, L, C, V, A = (panel[f] for f in FIELDS)
    traded = V.fillna(0) > 0
    C_ff = C.ffill()
    prev_close = C_ff.shift(1)

    # ---- 信号（只用 T 日及以前的数据）
    hh = C.shift(1).rolling(p.breakout_days, min_periods=p.breakout_days).max()
    vol_ma = V.shift(1).rolling(p.vol_ma_days, min_periods=p.vol_ma_days).mean()
    vol_ratio = V / vol_ma
    sig = (C > hh) & (vol_ratio >= p.vol_mult) & (A >= p.min_amount) & traded
    if p.max_price > 0:
        sig &= C <= p.max_price
    exit_ma = C.rolling(p.exit_ma_days, min_periods=p.exit_ma_days).mean()

    lim = pd.Series({c: limit_pct(c) for c in C.columns})
    up_limit = (prev_close * (1 + lim)).round(2)
    down_limit = (prev_close * (1 - lim)).round(2)

    dates = C.index
    first = 0 if start is None else int(dates.searchsorted(pd.Timestamp(start)))
    br = Broker(p, p.init_cash)
    pending_buy: list[str] = []
    pending_sell: dict[str, str] = {}
    equity = []

    for i in range(first, len(dates)):
        d = dates[i]
        o, h, l, c = O.iloc[i], H.iloc[i], L.iloc[i], C.iloc[i]
        tr = traded.iloc[i]
        cff = C_ff.iloc[i]
        dl, ul = down_limit.iloc[i], up_limit.iloc[i]

        # 1) 开盘：先卖后买
        for code, reason in list(pending_sell.items()):
            if code not in br.positions:
                pending_sell.pop(code)
                continue
            if not tr[code] or (h[code] == l[code] and l[code] <= dl[code]):
                continue  # 停牌或一字跌停，顺延
            br.sell(code, o[code], i, d, reason)
            pending_sell.pop(code)

        if pending_buy:
            prev_equity = equity[-1][1] if equity else br.cash
            slots = p.max_pos - len(br.positions)
            for code in pending_buy:
                if slots <= 0:
                    break
                if code in br.positions or not tr[code] or o[code] >= ul[code] - 0.005:
                    continue  # 停牌或开盘涨停买不进
                if br.buy(code, o[code], min(prev_equity / p.max_pos, br.cash), i, d):
                    slots -= 1
            pending_buy = []

        # 2) 盘中止损（T+1：当天买的不能卖）
        for code, pos in list(br.positions.items()):
            if pos.entry_idx >= i or not tr[code] or code in pending_sell:
                continue
            stop = pos.entry_price * (1 - p.stop_loss)
            if l[code] <= stop and not (h[code] == l[code] and l[code] <= dl[code]):
                br.sell(code, min(o[code], stop), i, d, "stop")

        # 3) 收盘：记净值、生成次日指令
        mv = sum(pos.shares * cff[code] for code, pos in br.positions.items())
        equity.append((d, br.cash + mv, len(br.positions)))

        for code, pos in br.positions.items():
            if not tr[code]:
                continue
            if c[code] < exit_ma.iloc[i][code]:
                pending_sell[code] = "below_ma"
            elif p.max_hold_days and i - pos.entry_idx >= p.max_hold_days:
                pending_sell[code] = "max_hold"

        today = sig.iloc[i]
        cands = today[today].index.difference(list(br.positions))
        if len(cands):
            pending_buy = list(vol_ratio.iloc[i][cands].sort_values(ascending=False).index)

    eq = pd.DataFrame(equity, columns=["date", "equity", "n_pos"]).set_index("date")
    trades = pd.DataFrame(br.trades)
    if not trades.empty:
        trades["entry_date"] = dates[trades.pop("_entry_idx").values]
    return eq, trades


# --------------------------------------------------------------------------- 统计


def summarize(eq: pd.DataFrame, trades: pd.DataFrame, bench: pd.Series | None, init_cash: float) -> dict:
    s = eq["equity"]
    rets = s.pct_change().dropna()
    years = max((s.index[-1] - s.index[0]).days / 365.25, 1e-9)
    dd = s / s.cummax() - 1
    out = {
        "区间": f"{s.index[0]:%Y-%m-%d} ~ {s.index[-1]:%Y-%m-%d}",
        "期末资产": round(s.iloc[-1], 2),
        "总收益": s.iloc[-1] / init_cash - 1,
        "年化收益": (s.iloc[-1] / init_cash) ** (1 / years) - 1,
        "年化波动": rets.std() * math.sqrt(252),
        "夏普(无风险=0)": rets.mean() / rets.std() * math.sqrt(252) if rets.std() > 0 else float("nan"),
        "最大回撤": dd.min(),
        "平均持仓数": eq["n_pos"].mean(),
    }
    out["卡玛比率"] = out["年化收益"] / abs(out["最大回撤"]) if out["最大回撤"] < 0 else float("nan")
    if not trades.empty:
        win = trades[trades["pnl"] > 0]
        loss = trades[trades["pnl"] <= 0]
        out.update({
            "交易笔数": len(trades),
            "胜率": len(win) / len(trades),
            "平均盈利": win["ret"].mean() if len(win) else 0.0,
            "平均亏损": loss["ret"].mean() if len(loss) else 0.0,
            "盈亏比(总盈利/总亏损)": win["pnl"].sum() / -loss["pnl"].sum() if loss["pnl"].sum() < 0 else float("inf"),
            "平均持有天数": trades["hold_days"].mean(),
            "离场原因": trades["reason"].value_counts().to_dict(),
        })
    if bench is not None:
        b = bench.reindex(s.index).ffill().dropna()
        if len(b) > 1:
            out["基准总收益"] = b.iloc[-1] / b.iloc[0] - 1
            out["基准最大回撤"] = (b / b.cummax() - 1).min()
    return out


def print_summary(summary: dict):
    pct_keys = {"总收益", "年化收益", "年化波动", "最大回撤", "胜率", "平均盈利", "平均亏损", "基准总收益", "基准最大回撤"}
    for k, v in summary.items():
        if k in pct_keys:
            print(f"  {k:<14} {v:>10.2%}")
        elif isinstance(v, float):
            print(f"  {k:<14} {v:>10.2f}")
        else:
            print(f"  {k:<14} {v}")


def plot(eq: pd.DataFrame, bench: pd.Series | None, path: str, init_cash: float):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 6.5), sharex=True, gridspec_kw={"height_ratios": [3, 1]})
    nav = eq["equity"] / init_cash
    ax1.plot(nav.index, nav, label="Strategy", color="#c0392b", lw=1.4)
    if bench is not None:
        b = bench.reindex(nav.index).ffill().dropna()
        if len(b):
            ax1.plot(b.index, b / b.iloc[0], label="Benchmark", color="#7f8c8d", lw=1.1)
    ax1.set_ylabel("NAV")
    ax1.legend(loc="upper left")
    ax1.grid(alpha=0.3)
    dd = eq["equity"] / eq["equity"].cummax() - 1
    ax2.fill_between(dd.index, dd, 0, color="#c0392b", alpha=0.35)
    ax2.set_ylabel("Drawdown")
    ax2.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


# --------------------------------------------------------------------------- 入口


def main():
    ap = argparse.ArgumentParser(description="放量突破策略回测")
    ap.add_argument("--source", choices=["xtdata", "akshare", "csv", "synthetic"], default="xtdata")
    ap.add_argument("--index", default="000905", help="股票池指数：000300 沪深300 / 000905 中证500 / 000852 中证1000")
    ap.add_argument("--csv-dir", default="data")
    ap.add_argument("--start", default="20200101", help="回测开始日（会自动多取 60 天数据预热指标）")
    ap.add_argument("--end", default=pd.Timestamp.today().strftime("%Y%m%d"))
    ap.add_argument("--out", default="output")
    for f_ in Params.__dataclass_fields__.values():
        ap.add_argument(f"--{f_.name.replace('_', '-')}", type=type(f_.default), default=f_.default)
    args = ap.parse_args()
    p = Params(**{k: getattr(args, k) for k in Params.__dataclass_fields__})

    warm_start = (pd.Timestamp(args.start) - pd.Timedelta(days=100)).strftime("%Y%m%d")
    print(f"加载数据: source={args.source} index={args.index}")
    if args.source == "xtdata":
        data, bench = load_xtdata(args.index, warm_start, args.end)
    elif args.source == "akshare":
        data, bench = load_akshare(args.index, warm_start, args.end, args.csv_dir)
    elif args.source == "csv":
        data, bench = load_csv_dir(args.csv_dir)
    else:
        print("  ⚠ synthetic 是随机假数据，只用来验证程序，结果没有参考价值")
        data, bench = make_synthetic(start=warm_start, end=args.end)
    print(f"  股票数: {len(data)}")

    eq, trades = run_backtest(data, p, start=args.start)
    summary = summarize(eq, trades, bench, p.init_cash)

    os.makedirs(args.out, exist_ok=True)
    eq.to_csv(os.path.join(args.out, "equity.csv"))
    trades.to_csv(os.path.join(args.out, "trades.csv"), index=False)
    plot(eq, bench, os.path.join(args.out, "equity.png"), p.init_cash)

    print("\n回测结果")
    print_summary(summary)
    print(f"\n明细已写入 {args.out}/ (equity.csv, trades.csv, equity.png)")


if __name__ == "__main__":
    main()
