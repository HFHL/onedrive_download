import os
import tarfile

PROCESSED_FILE_RECORD = "unziped_record.txt"

def load_processed_files(record_file):
    """
    加载已经处理的 tar 文件列表。
    """
    if os.path.exists(record_file):
        with open(record_file, 'r') as f:
            return set(f.read().splitlines())
    return set()

def save_processed_file(record_file, file_path):
    """
    保存已处理的 tar 文件路径到记录文件。
    """
    with open(record_file, 'a') as f:
        f.write(file_path + '\n')

def extract_tar_files_in_batches(directory, batch_size=5, record_file=PROCESSED_FILE_RECORD):
    """
    批量解压目录中的 .tar 文件，带有检查点机制，避免重复解压已处理的文件。
    """
    # 加载已经处理的文件
    processed_files = load_processed_files(record_file)

    # 找到目录中的 tar 文件，并且排除已经处理过的文件
    tar_files = [f for f in os.listdir(directory) if f.endswith('.tar') and os.path.join(directory, f) not in processed_files]
    
    total_files = len(tar_files)
    if total_files == 0:
        print(f"目录 {directory} 中没有新的 tar 文件。")
        return

    # 分批处理文件
    for i in range(0, total_files, batch_size):
        batch_files = tar_files[i:i+batch_size]
        print(f"正在解压批次 {i//batch_size + 1}: {batch_files}")
        
        for tar_file in batch_files:
            tar_path = os.path.join(directory, tar_file)
            try:
                with tarfile.open(tar_path, 'r') as tar:
                    tar.extractall(path=directory)
                print(f"成功解压 {tar_file}。")
                # 记录已处理的文件，使用完整路径
                save_processed_file(record_file, tar_path)
            except Exception as e:
                print(f"解压 {tar_file} 时出错: {e}")

def process_directories(base_directory, batch_size=5):
    """
    处理 train, test 和 valid 目录，并解压其中的 tar 文件。
    """
    for sub_dir in ['train', 'test', 'valid']:
        full_path = os.path.join(base_directory, sub_dir)
        if os.path.isdir(full_path):
            print(f"正在处理目录: {full_path}")
            extract_tar_files_in_batches(full_path, batch_size=batch_size)
        else:
            print(f"目录 {full_path} 未找到。")

if __name__ == "__main__":
    # 替换为你的基础目录路径
    base_dir = "./"
    
    process_directories(base_dir)
    