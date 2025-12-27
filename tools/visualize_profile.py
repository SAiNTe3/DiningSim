"""
生成 profile 可视化图表
需要:  pip install matplotlib pandas
"""
import pstats
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
import os

# 设置中文字体
matplotlib.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei']
matplotlib.rcParams['axes.unicode_minus'] = False

def load_profile_data(profile_file):
    """加载 profile 数据"""
    stats = pstats.Stats(profile_file)
    
    # 提取数据
    data = []
    for func, (cc, nc, tt, ct, callers) in stats.stats.items():
        # func: (filename, line, function_name)
        filename, line, func_name = func
        
        # 简化文件名
        if 'sim_core' in str(func):
            location = 'C++ (sim_core)'
        elif 'concurrent_test' in filename:
            location = 'Test Framework'
        elif 'built-in' in filename or filename == '~':
            location = 'Built-in'
        else: 
            location = 'Other'
        
        data.append({
            'function': func_name,
            'location': location,
            'ncalls': nc,
            'tottime': tt,
            'cumtime': ct,
            'percall_tot': tt/nc if nc > 0 else 0,
            'percall_cum': ct/nc if nc > 0 else 0,
        })
    
    df = pd.DataFrame(data)
    return df, stats

def plot_time_distribution(df, output_dir='../logs'):
    """绘制时间分布饼图"""
    # 按总时间排序，取前10
    top10 = df.nlargest(10, 'tottime')
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
    
    # 饼图1: 总时间分布
    colors = plt.cm.Set3(range(len(top10)))
    wedges, texts, autotexts = ax1.pie(
        top10['tottime'],
        labels=top10['function'],
        autopct='%1.1f%%',
        colors=colors,
        startangle=90
    )
    ax1.set_title('函数总时间分布 (Top 10)', fontsize=14, fontweight='bold')
    
    # 饼图2: 按位置分布
    location_time = df. groupby('location')['tottime'].sum().sort_values(ascending=False)
    colors2 = ['#ff9999', '#66b3ff', '#99ff99', '#ffcc99']
    wedges2, texts2, autotexts2 = ax2.pie(
        location_time.values,
        labels=location_time.index,
        autopct='%1.1f%%',
        colors=colors2,
        startangle=90
    )
    ax2.set_title('按模块时间分布', fontsize=14, fontweight='bold')
    
    plt.tight_layout()
    
    output_file = os.path.join(output_dir, 'profile_time_distribution.png')
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"✅ Saved:  {output_file}")
    plt.close()

def plot_top_functions_bar(df, output_dir='../logs'):
    """绘制前20个函数的条形图"""
    # 排除 sleep（因为太大了）
    df_filtered = df[~df['function'].str.contains('sleep', case=False)]
    top20 = df_filtered.nlargest(20, 'tottime')
    
    fig, ax = plt.subplots(figsize=(12, 8))
    
    bars = ax.barh(range(len(top20)), top20['tottime'], color='skyblue', edgecolor='navy')
    ax.set_yticks(range(len(top20)))
    ax.set_yticklabels(top20['function'], fontsize=9)
    ax.set_xlabel('总时间 (秒)', fontsize=12)
    ax.set_title('Top 20 耗时函数 (排除 sleep)', fontsize=14, fontweight='bold')
    ax.invert_yaxis()
    
    # 添加数值标签
    for i, (idx, row) in enumerate(top20.iterrows()):
        ax.text(row['tottime'], i, f" {row['tottime']:.3f}s", 
                va='center', fontsize=8)
    
    plt.tight_layout()
    
    output_file = os.path.join(output_dir, 'profile_top_functions.png')
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"✅ Saved: {output_file}")
    plt.close()

def plot_call_frequency(df, output_dir='../logs'):
    """绘制调用频率图"""
    top20_calls = df.nlargest(20, 'ncalls')
    
    fig, ax = plt.subplots(figsize=(12, 8))
    
    bars = ax.barh(range(len(top20_calls)), top20_calls['ncalls'], 
                   color='lightcoral', edgecolor='darkred')
    ax.set_yticks(range(len(top20_calls)))
    ax.set_yticklabels(top20_calls['function'], fontsize=9)
    ax.set_xlabel('调用次数', fontsize=12)
    ax.set_title('Top 20 高频调用函数', fontsize=14, fontweight='bold')
    ax.invert_yaxis()
    
    # 添加数值标签
    for i, (idx, row) in enumerate(top20_calls. iterrows()):
        ax.text(row['ncalls'], i, f" {row['ncalls']}", 
                va='center', fontsize=8)
    
    plt.tight_layout()
    
    output_file = os.path.join(output_dir, 'profile_call_frequency.png')
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"✅ Saved: {output_file}")
    plt.close()

def plot_cumulative_vs_total(df, output_dir='../logs'):
    """绘制累计时间 vs 自身时间散点图"""
    # 排除 sleep
    df_filtered = df[~df['function']. str.contains('sleep', case=False)]
    df_filtered = df_filtered[df_filtered['tottime'] > 0.0001]  # 过滤极小值
    
    fig, ax = plt.subplots(figsize=(10, 8))
    
    scatter = ax.scatter(df_filtered['tottime'], df_filtered['cumtime'], 
                        s=df_filtered['ncalls']*10, 
                        alpha=0.6, c=df_filtered['ncalls'], 
                        cmap='viridis', edgecolors='black', linewidth=0.5)
    
    # 添加对角线 (cumtime = tottime)
    max_val = max(df_filtered['cumtime'].max(), df_filtered['tottime'].max())
    ax.plot([0, max_val], [0, max_val], 'r--', alpha=0.5, label='cumtime = tottime')
    
    ax.set_xlabel('总时间 (tottime, 秒)', fontsize=12)
    ax.set_ylabel('累计时间 (cumtime, 秒)', fontsize=12)
    ax.set_title('累计时间 vs 自身时间\n(气泡大小 = 调用次数)', fontsize=14, fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # 颜色条
    cbar = plt.colorbar(scatter, ax=ax)
    cbar.set_label('调用次数', fontsize=10)
    
    # 标注重要函数
    for idx, row in df_filtered.nlargest(5, 'cumtime').iterrows():
        ax.annotate(row['function'], 
                   (row['tottime'], row['cumtime']),
                   xytext=(5, 5), textcoords='offset points',
                   fontsize=8, alpha=0.7)
    
    plt.tight_layout()
    
    output_file = os.path.join(output_dir, 'profile_cumtime_vs_tottime.png')
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"✅ Saved: {output_file}")
    plt.close()

def generate_summary_table(df, stats, output_dir='../logs'):
    """生成汇总表格图"""
    fig, ax = plt.subplots(figsize=(14, 6))
    ax.axis('tight')
    ax.axis('off')
    
    # 准备数据
    top10 = df.nlargest(10, 'tottime')
    table_data = []
    
    for idx, row in top10.iterrows():
        table_data.append([
            row['function'][:30],  # 截断长名称
            f"{row['ncalls']:.0f}",
            f"{row['tottime']:.4f}",
            f"{row['cumtime']:.4f}",
            f"{row['percall_tot']*1000:.2f}",
            row['location']
        ])
    
    # 创建表格
    table = ax.table(cellText=table_data,
                    colLabels=['函数', '调用次数', '总时间(s)', '累计时间(s)', '单次(ms)', '位置'],
                    cellLoc='left',
                    loc='center',
                    colWidths=[0.35, 0.1, 0.1, 0.1, 0.1, 0.15])
    
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1, 2)
    
    # 设置表头样式
    for i in range(6):
        table[(0, i)].set_facecolor('#4CAF50')
        table[(0, i)].set_text_props(weight='bold', color='white')
    
    # 设置行颜色
    for i in range(1, len(table_data) + 1):
        for j in range(6):
            if i % 2 == 0:
                table[(i, j)].set_facecolor('#f0f0f0')
    
    ax.set_title('Top 10 函数性能汇总', fontsize=16, fontweight='bold', pad=20)
    
    plt.tight_layout()
    
    output_file = os.path.join(output_dir, 'profile_summary_table.png')
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"✅ Saved: {output_file}")
    plt.close()

def main():
    profile_file = '../logs/python_profile.prof'
    
    if not os.path.exists(profile_file):
        print(f"❌ Profile file not found:  {profile_file}")
        print("Run:  python tools/profile_with_cprofile.py")
        return
    
    print("="*60)
    print("Generating Profile Visualizations")
    print("="*60)
    print()
    
    # 加载数据
    print("Loading profile data...")
    df, stats = load_profile_data(profile_file)
    print(f"Loaded {len(df)} functions")
    print()
    
    # 生成图表
    
    print("Generating charts...")
    plot_time_distribution(df)
    plot_top_functions_bar(df)
    plot_call_frequency(df)
    plot_cumulative_vs_total(df)
    generate_summary_table(df, stats)
    
    print()
    print("="*60)
    print("✅ All visualizations generated!")
    print("="*60)
    print()
    print("Output files:")
    print("  - ../logs/profile_time_distribution.png")
    print("  - ../logs/profile_top_functions.png")
    print("  - ../logs/profile_call_frequency.png")
    print("  - ../logs/profile_cumtime_vs_tottime.png")
    print("  - ../logs/profile_summary_table.png")

if __name__ == '__main__':
    main()