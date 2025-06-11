import pandas as pd
import json
import argparse
import os
from pathlib import Path

def process_csv_to_parquet(input_file, output_file):
    # 读取CSV文件
    df = pd.read_csv(input_file)
    
    # 创建新的DataFrame
    new_df = pd.DataFrame()
    new_df['instruction'] = df['instruction']
    new_df['prompt'] = df['input']
    new_df['response'] = df['output']
    
    # 处理meta字段
    def create_meta_dict(row):
        return {
            "game_setting": row['meta.game_setting'],
            "game_id": row['meta.game_id'],
            "player_id": row['meta.player_id'],
            "role": row['meta.role'],
            "type": row['meta.type'],
            "turn": f"{row['meta.extra.turn']}-{row['meta.extra.type']}"
        }
    
    # 将meta相关字段转换为字典
    new_df['meta'] = df.apply(create_meta_dict, axis=1)
    
    # 保存为parquet文件
    new_df.to_parquet(output_file)
    return new_df

def main():
    # 设置命令行参数
    parser = argparse.ArgumentParser(description='Convert CSV files to Parquet format')
    parser.add_argument('--csv_paths', type=str, required=True,
                      help='Directory containing the CSV files')
    
    args = parser.parse_args()
    
    # 确保输入路径存在
    csv_dir = Path(args.csv_paths)
    if not csv_dir.exists():
        raise ValueError(f"Directory {csv_dir} does not exist")
    
    # 查找目录中的所有CSV文件
    target_files = ['speech.csv', 'vote.csv', 'action.csv']
    dfs = {}
    
    for csv_file in target_files:
        input_path = csv_dir / csv_file
        if not input_path.exists():
            print(f"Warning: {input_path} not found, skipping...")
            continue
            
        # 生成输出文件名（将.csv替换为.parquet）
        output_file = csv_dir / f"{csv_file.rsplit('.', 1)[0]}.parquet"
        
        print(f"Processing {input_path}...")
        dfs[csv_file] = process_csv_to_parquet(input_path, output_file)
        print(f"Created {output_file}")

    if dfs:
        # 合并所有DataFrame
        merged_df = pd.concat(dfs.values(), ignore_index=True)
        
        # 保存最终的合并文件
        output_merged = csv_dir / 'train_all_en.parquet'
        merged_df.to_parquet(output_merged)
        print(f"\nCreated final merged file: {output_merged}")
    else:
        print("No CSV files were processed")

if __name__ == "__main__":
    main()