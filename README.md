# 🛒 基于亿级淘宝日志的用户行为分析与 RF 精细化运营项目

![Python](https://img.shields.io/badge/Python-3.13-blue.svg)
![Pandas](https://img.shields.io/badge/Pandas-2.3-green.svg)
![Data](https://img.shields.io/badge/Data-Tianchi_UserBehavior-orange.svg)

##  项目背景
本项目基于阿里天池 **98,914,484 条（约 1 亿条）** 真实电商用户行为日志，使用 **Python (Pandas, Plotly, Seaborn)** 进行全链路转化漏斗分析、路径归因研究、Cohort 留存率计算及 RF 用户价值分层，旨在为电商运营提供落地、可干预的决策方案。

---
## Quick Start

### 1. 克隆项目

```bash
git clone https://github.com/your-username/taobao-user-behavior-analysis.git
cd taobao-user-behavior-analysis
```

### 2. 下载数据集

从阿里天池下载 **UserBehavior.csv** 数据集，并将文件放置在项目根目录。

项目目录结构如下：

```text
taobao-user-behavior-analysis/
├── UserBehavior.csv
├── main.py
├── README.md
└── reports/
```

### 3. 安装依赖

建议使用 Python 3.13 或以上版本。

```bash
pip install pandas numpy matplotlib seaborn plotly
```

### 4. 运行项目

```bash
python main.py
```

程序运行完成后，将自动在 `reports/` 目录生成分析结果，包括：

```text
reports/
├── interactive_funnel.html
├── cohort_retention_heatmap.png
├── daily_kpi_trend.csv
└── rfm_segmentation.csv
```

---
##  核心业务洞察 (Key Business Insights)

### 1. 用户决策耗时归因
- **数据发现**：**70.12%** 的用户转化需要**跨天决策 (>24h)**，仅有 **2.06%** 的用户能在 5 分钟内极速下单。
- **运营动作**：针对加购/收藏后超过 12h 未结算的用户，触发消息推送与限时优惠唤醒。

### 2. 路径归因（购物车 vs 收藏夹）
- **数据发现**：购物车路径转化率为 **71.68%**，收藏夹路径转化率为 **70.93%**，但购物车覆盖独立用户数是收藏夹的 **1.9 倍**。
- **产品动作**：确定购物车为绝对转化主阵地，优化结算页“自动计算凑单免邮”体验。

### 3. Cohort 留存率表现
- **数据发现**：大促预热期前期的用户在 **12 月 2日 - 3 日** 出现了强劲的**大促回流潮**（Day 7 活跃留存率回升至 **95.91%**）。

---

##  RFM 精细化运营策略矩阵

| 用户分层群体 | 用户规模 | 业务特征 | 落地运营策略 |
| :--- | :--- | :--- | :--- |
| **重要价值客户** | 204,478 | 高频近购 | VIP 专线与身份认同、优先发货、新品体验官邀请 |
| **重要发展客户** | 175,516 | 低频近购 | 交叉销售（Cross-selling）、满减凑单激励 |
| **重要保持客户** | 79,678 | 高频远购 | 流失预警召回、推送大额无门槛唤醒券、复购提醒 |
| **低价值/流失客户**| 210,698 | 低频远购 | 低成本通道推送全站 TOP 爆款，控制营销预算 |

---

##  项目产出与交付物

```text
reports/
├── interactive_funnel.html       # Plotly 动态交互式转化漏斗图
├── cohort_retention_heatmap.png  # Seaborn Cohort 留存率分析热力图
├── daily_kpi_trend.csv           # 导出至 Tableau 的日度 KPI 趋势数据
└── rfm_segmentation.csv          # 用户分层与打分表
