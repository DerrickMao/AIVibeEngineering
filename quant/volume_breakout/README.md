# 放量突破策略回测

## 策略规则

| 项目 | 规则（默认值，均可用命令行参数修改） |
|---|---|
| 买入信号 | 收盘价 > 前 20 日最高收盘价，且成交量 ≥ 前 5 日均量 × 2，且成交额 ≥ 1 亿 |
| 买入时点 | 信号次日开盘；开盘涨停买不进就放弃 |
| 仓位 | 最多 5 只，每只约总资产的 1/5，按整手（100 股）买 |
| 信号太多时 | 按量比从大到小取 |
| 卖出 | 收盘跌破 10 日均线 → 次日开盘卖；盘中跌到成本 -8% → 止损 |
| 规则约束 | T+1（买入当天不卖）、一字跌停卖不出顺延、停牌跳过 |
| 费用 | 佣金万 2.5（最低 5 元）+ 过户费 + 卖出印花税 0.05% + 单边滑点 0.1% |

## 运行

```bash
pip install pandas numpy matplotlib
```

**方式一：在装了 QMT 的 Windows 上（推荐，和实盘同一个数据源）**

先打开 QMT，以极简模式登录，然后：

```bash
python backtest.py --source xtdata --index 000905 --start 20200101
```

**方式二：用 AKShare 免费数据（任何电脑）**

```bash
pip install akshare
python backtest.py --source akshare --index 000905 --start 20200101 --csv-dir data
```

第一次运行会把每只股票的数据缓存到 `data/` 目录，之后再跑就很快。

**方式三：自备 CSV**：`data/` 下每只股票放一个 `600519.SH.csv`，列为 `date,open,high,low,close,volume,amount`；可选 `benchmark.csv`（列 `date,close`）。

```bash
python backtest.py --source csv --csv-dir data
```

## 常用参数

```bash
--index 000300|000905|000852   # 股票池：沪深300 / 中证500 / 中证1000
--vol-mult 2.5                 # 放量倍数
--breakout-days 60             # 突破 N 日新高
--stop-loss 0.06               # 止损比例
--exit-ma-days 20              # 跌破几日均线离场
--max-pos 4                    # 最多持有几只
--max-hold-days 15             # 最长持有天数（0 = 不限）
--init-cash 200000
```

输出在 `output/`：`equity.csv`（每日净值）、`trades.csv`（每笔交易）、`equity.png`（净值和回撤图）。

## 结果要打折看

- **幸存者偏差**：股票池用的是指数**当前**成分股，历史上被剔除的股票不在里面，回测结果会偏乐观。
- **复权价**：用的是前复权价格，计算的股数和真实情况略有差别，对收益影响不大。
- **成交假设**：默认按次日开盘价加 0.1% 滑点成交，小盘股实际冲击成本可能更高。
- **别过度调参**：在一段历史上把参数调到最好，换一段时间往往就失效。至少分成两段，一段用来调参，另一段验证。
