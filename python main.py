import os
import pandas as pd
import numpy as np
import datetime

# 引入专业可视化库
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
import plotly.graph_objects as go

# 设置绘图样式
plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']  # 正常显示中文
plt.rcParams['axes.unicode_minus'] = False  # 正常显示负号

# ==========================================
# 1. 数据清洗与预处理模块
# ==========================================
def load_and_clean_tianchi_data(file_path: str, chunk_size: int = 1000000) -> pd.DataFrame:
    """
    分块读取阿里天池日志数据，执行去重、时间过滤与特征衍生
    """
    print(f"[Step 1] 开始加载并清洗天池数据集: {file_path} ...")
    chunks = []
    col_names = ['user_id', 'item_id', 'category_id', 'behavior_type', 'timestamp']
    
    for chunk in pd.read_csv(file_path, names=col_names, header=None, chunksize=chunk_size):
        chunk = chunk.drop_duplicates()
        chunk['datetime'] = pd.to_datetime(chunk['timestamp'], unit='s')
        
        # 过滤业务有效时间段 (2017-11-25 至 2017-12-03)
        valid_mask = (chunk['datetime'] >= '2017-11-25 00:00:00') & (chunk['datetime'] <= '2017-12-03 23:59:59')
        chunk = chunk[valid_mask]
        
        chunk['date'] = chunk['datetime'].dt.date
        chunk['hour'] = chunk['datetime'].dt.hour
        chunk['day_of_week'] = chunk['datetime'].dt.dayofweek
        
        chunks.append(chunk)
        
    df = pd.concat(chunks, ignore_index=True)
    print(f"清洗完成！有效日志总行数: {len(df):,}")
    return df

# ==========================================
# 2. 深度转化分析：全链路漏斗、路径归因与转化时延
# ==========================================
def perform_advanced_funnel_and_path_analysis(df: pd.DataFrame, output_dir: str):
    """
    1. 全链路漏斗与 Plotly 动态可视化
    2. 路径归因：对比 'PV -> Cart -> Buy' 与 'PV -> Fav -> Buy'
    3. 转化时延：分析 PV 到 Buy 的耗时分布
    """
    print("\n[Step 2] 执行漏斗分析、路径归因与转化时延计算...")
    
    # ---------------- 2.1 全链路漏斗 ----------------
    funnel_summary = df.groupby('behavior_type').agg(
        total_actions=('user_id', 'count'),
        unique_users=('user_id', 'nunique')
    ).reset_index()
    
    stage_map = {'pv': 1, 'cart': 2, 'fav': 3, 'buy': 4}
    funnel_summary['stage'] = funnel_summary['behavior_type'].map(stage_map)
    funnel_summary = funnel_summary.sort_values('stage').reset_index(drop=True)
    
    funnel_summary['prev_action_cnt'] = funnel_summary['total_actions'].shift(1)
    funnel_summary['conversion_rate'] = (funnel_summary['total_actions'] / funnel_summary['prev_action_cnt']).fillna(1.0)
    pv_total = funnel_summary.loc[funnel_summary['behavior_type'] == 'pv', 'total_actions'].values[0]
    funnel_summary['overall_conversion_rate'] = funnel_summary['total_actions'] / pv_total
    funnel_summary['drop_off_rate'] = 1.0 - funnel_summary['conversion_rate']
    
    print("\n--- 全链路漏斗转化表 ---")
    print(funnel_summary[['behavior_type', 'total_actions', 'unique_users', 'conversion_rate', 'drop_off_rate']].to_string(index=False))
    
    # 生成 Plotly 动态漏斗图
    fig_funnel = go.Figure(go.Funnel(
        y=funnel_summary['behavior_type'].str.upper(),
        x=funnel_summary['total_actions'],
        textinfo="value+percent initial+percent previous"
    ))
    fig_funnel.update_layout(title_text="电商全链路行为转化漏斗图 (Plotly)")
    funnel_html_path = os.path.join(output_dir, "interactive_funnel.html")
    fig_funnel.write_html(funnel_html_path)
    print(f"-> 动态漏斗图已保存至: {funnel_html_path}")

    # ---------------- 2.2 路径归因对比：购物车 vs 收藏夹 ----------------
    user_cart_users = set(df[df['behavior_type'] == 'cart']['user_id'])
    user_fav_users = set(df[df['behavior_type'] == 'fav']['user_id'])
    user_buy_users = set(df[df['behavior_type'] == 'buy']['user_id'])
    
    cart_to_buy_users = user_cart_users.intersection(user_buy_users)
    fav_to_buy_users = user_fav_users.intersection(user_buy_users)
    
    cart_conversion = len(cart_to_buy_users) / len(user_cart_users) if user_cart_users else 0
    fav_conversion = len(fav_to_buy_users) / len(user_fav_users) if user_fav_users else 0
    
    print("\n--- 路径归因分析结果 ---")
    print(f"【购物车路径】加购独立用户数: {len(user_cart_users):,}, 最终购买用户数: {len(cart_to_buy_users):,}, 用户转化率: {cart_conversion:.2%}")
    print(f"【收藏夹路径】收藏独立用户数: {len(user_fav_users):,}, 最终购买用户数: {len(fav_to_buy_users):,}, 用户转化率: {fav_conversion:.2%}")
    
    # ---------------- 2.3 转化耗时分析 (PV 到 Buy) ----------------
    # 抽样提取购买用户首次 PV 与首次 Buy 的时间差
    first_pv = df[df['behavior_type'] == 'pv'].groupby('user_id')['datetime'].min().reset_index()
    first_buy = df[df['behavior_type'] == 'buy'].groupby('user_id')['datetime'].min().reset_index()
    
    time_diff_df = pd.merge(first_pv, first_buy, on='user_id', suffixes=('_pv', '_buy'))
    time_diff_df['time_cost_minutes'] = (time_diff_df['datetime_buy'] - time_diff_df['datetime_pv']).dt.total_seconds() / 60.0
    
    # 过滤异常负值，并划分耗时区间
    time_diff_df = time_diff_df[time_diff_df['time_cost_minutes'] >= 0]
    
    bins = [-np.inf, 5, 30, 120, 1440, np.inf]
    labels = ['极速购买(<=5min)', '快速决策(5-30min)', '中期犹豫(30min-2h)', '跨半天决策(2-24h)', '跨天决策(>24h)']
    time_diff_df['time_segment'] = pd.cut(time_diff_df['time_cost_minutes'], bins=bins, labels=labels)
    
    time_stat = time_diff_df['time_segment'].value_counts(normalize=True).reset_index()
    time_stat.columns = ['time_segment', 'percentage']
    time_stat['percentage_str'] = time_stat['percentage'].apply(lambda x: f"{x:.2%}")
    
    print("\n--- 用户转化耗时分布 ---")
    print(time_stat[['time_segment', 'percentage_str']].to_string(index=False))

# ==========================================
# 3. 留存率与 Cohort 同期群分析模块
# ==========================================
def perform_cohort_retention_analysis(df: pd.DataFrame, output_dir: str):
    """
    以用户首次出现日期构建 Cohort，计算 +1天、+3天、+7天 活跃留存率，并绘制 Heatmap
    """
    print("\n[Step 3] 执行 Cohort 留存率同期群分析...")
    
    # 1. 查找每个用户的首次活跃日期 (First Date)
    first_date_df = df.groupby('user_id')['date'].min().reset_index()
    first_date_df.columns = ['user_id', 'cohort_date']
    
    # 2. 合并回主表计算 Day N
    df_cohort = pd.merge(df, first_date_df, on='user_id')
    df_cohort['cohort_date'] = pd.to_datetime(df_cohort['cohort_date'])
    df_cohort['act_date'] = pd.to_datetime(df_cohort['date'])
    df_cohort['day_offset'] = (df_cohort['act_date'] - df_cohort['cohort_date']).dt.days
    
    # 3. 计算各 Cohort 的 Day N 留存人数
    cohort_group = df_cohort.groupby(['cohort_date', 'day_offset'])['user_id'].nunique().reset_index()
    cohort_pivot = cohort_group.pivot(index='cohort_date', columns='day_offset', values='user_id')
    
    # 4. 转化为百分比矩阵 (以 Day 0 人数为基准)
    cohort_size = cohort_pivot.iloc[:, 0]
    retention_matrix = cohort_pivot.divide(cohort_size, axis=0)
    
    # 只展示 0 到 7 天的留存
    cols_to_show = [c for c in range(8) if c in retention_matrix.columns]
    retention_matrix_show = retention_matrix[cols_to_show]
    
    print("\n--- Cohort 留存率矩阵 (%) ---")
    print((retention_matrix_show * 100).round(2).to_string())
    
    # 5. 绘制并保存 Seaborn 热力图
    plt.figure(figsize=(10, 6))
    sns.heatmap(retention_matrix_show, annot=True, fmt='.1%', cmap='Blues', vmin=0.0, vmax=0.5)
    plt.title('淘宝用户 Cohort 留存率热力图 (2017/11/25 - 2017/12/03)')
    plt.xlabel('活跃相隔天数 (Day N)')
    plt.ylabel('首次进入日期 (Cohort Date)')
    
    heatmap_path = os.path.join(output_dir, "cohort_retention_heatmap.png")
    plt.tight_layout()
    plt.savefig(heatmap_path, dpi=300)
    plt.close()
    print(f"-> 留存热力图已导出保存至: {heatmap_path}")

# ==========================================
# 4. RF 用户价值分层与精准运营决策
# ==========================================
def build_rfm_with_actionable_insights(df: pd.DataFrame, output_dir: str, analysis_date_str: str = '2017-12-04') -> pd.DataFrame:
    """
    计算 RF 指标分层，并针对各画像输出结构化运营 Actionable Insights
    """
    print("\n[Step 4] 启动用户价值分层与精细化运营决策生成...")
    
    buy_df = df[df['behavior_type'] == 'buy'].copy()
    ref_date = pd.to_datetime(analysis_date_str)
    
    rfm = buy_df.groupby('user_id').agg(
        last_purchase_time=('datetime', 'max'),
        frequency=('item_id', 'count')
    ).reset_index()
    
    rfm['recency'] = (ref_date - rfm['last_purchase_time']).dt.days
    
    # 业务区间打分
    r_bins = [-np.inf, 1, 2, 3, 5, np.inf]
    rfm['r_score'] = pd.cut(rfm['recency'], bins=r_bins, labels=[5, 4, 3, 2, 1]).astype(int)
    
    f_bins = [-np.inf, 1, 2, 3, 5, np.inf]
    rfm['f_score'] = pd.cut(rfm['frequency'], bins=f_bins, labels=[1, 2, 3, 4, 5]).astype(int)
    
    r_avg = rfm['r_score'].mean()
    f_avg = rfm['f_score'].mean()
    
    rfm['r_flag'] = (rfm['r_score'] > r_avg).astype(int)
    rfm['f_flag'] = (rfm['f_score'] > f_avg).astype(int)
    
    def classify_segment(row):
        code = f"{row['r_flag']}{row['f_flag']}"
        mapping = {
            '11': '重要价值客户 (高频近购)',
            '10': '重要发展客户 (低频近购)',
            '01': '重要保持客户 (高频远购)',
            '00': '低价值/流失客户 (低频远购)'
        }
        return mapping.get(code, '未定义')
        
    rfm['user_segment'] = rfm.apply(classify_segment, axis=1)
    
    # 输出业务策略映射
    print("\n========================================================")
    print("      🎯 核心用户群体分类与落地运营策略 (Actionable Insights)")
    print("========================================================")
    insights = {
        '重要价值客户 (高频近购)': "【策略：VIP倾斜与身份认同】提供专属客服、高阶会员权益、优先发货；引导参与新品体验测评。",
        '重要发展客户 (低频近购)': "【策略：交叉销售与提升客单】根据其浏览和历史购买推荐相关联的互补商品（Cross-selling）；发放满减券激励凑单。",
        '重要保持客户 (高频远购)': "【策略：流失预警与主动召回】触发自动化唤醒机制，通过 App Push/短信推送大额定向无门槛优惠券，推出到期复购提醒。",
        '低价值/流失客户 (低频远购)': "【策略：低成本触达与爆款爆破】采用低成本触达通道推送全站热销 TOP 爆款；若长期无响应可适当降低营销预算投放。"
    }
    
    segment_stat = rfm.groupby('user_segment').agg(user_cnt=('user_id', 'count')).reset_index()
    for _, row in segment_stat.iterrows():
        seg = row['user_segment']
        cnt = row['user_cnt']
        print(f"\n▶ 群体: {seg} (人数: {cnt:,})")
        print(f"  建议动作: {insights.get(seg, '暂无策略')}")
        
    print("\n--------------------------------------------------------")
    print("🎯 关键全链路转化瓶颈改善建议 (Conversion Optimization Insights)")
    print("--------------------------------------------------------")
    print("1. 【加购到下单高流失归因假设】: 加购到下单阶段流失显著，可能归因于：")
    print("   - 结算页费用透明度不足 (如运费/税费在最后一步才展示)；")
    print("   - 优惠券叠加规则复杂，用户因计算繁琐产生决策疲劳；")
    print("   - 缺乏快捷支付通道。")
    print("2. 【优化推荐动作】: 结算页增加‘凑单免运费’自动计算组件，并精简领券/扣减逻辑；引入限时降价倒计时增强紧迫感。")
    
    return rfm

# ==========================================
# 5. 可视化数据集导出模块
# ==========================================
def export_visualization_tables(df: pd.DataFrame, rfm_df: pd.DataFrame, output_dir: str):
    """
    导出预聚合 CSV 供 Tableau 搭建仪表盘
    """
    print("\n[Step 5] 导出 Tableau 仪表盘数据集...")
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    daily_stats = df.groupby('date').agg(
        dau=('user_id', 'nunique'),
        pv=('item_id', 'count'),
        cart_users=('user_id', lambda x: x[df.loc[x.index, 'behavior_type'] == 'cart'].nunique()),
        buyers=('user_id', lambda x: x[df.loc[x.index, 'behavior_type'] == 'buy'].nunique())
    ).reset_index()
    
    daily_stats.to_csv(os.path.join(output_dir, "daily_kpi_trend.csv"), index=False, encoding='utf-8-sig')
    rfm_df.to_csv(os.path.join(output_dir, "rfm_segmentation.csv"), index=False, encoding='utf-8-sig')
    print(f"-> CSV 数据集已导出至目录: {output_dir}")

# ==========================================
# 主流程入口
# ==========================================
if __name__ == "__main__":
    data_path = "UserBehavior.csv"
    output_directory = "./reports"
    
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)
        
    if os.path.exists(data_path):
        clean_df = load_and_clean_tianchi_data(file_path=data_path)
        perform_advanced_funnel_and_path_analysis(df=clean_df, output_dir=output_directory)
        perform_cohort_retention_analysis(df=clean_df, output_dir=output_directory)
        rfm_result = build_rfm_with_actionable_insights(df=clean_df, output_dir=output_directory, analysis_date_str='2017-12-04')
        export_visualization_tables(df=clean_df, rfm_df=rfm_result, output_dir=output_directory)
        print("\n全套专业级分析流程执行完毕！")
    else:
        print(f"未找到文件 {data_path}，请检查该文件是否放在同级目录下。")