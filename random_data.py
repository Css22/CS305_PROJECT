import random

def generate_and_write_random_data(filename, num_bytes=100000):
    random_data = random.randbytes(num_bytes)
    
    with open(filename, 'wb') as file:
        file.write(random_data)
    
    print(f"Written {num_bytes} random bytes to {filename}")

# 调用函数，生成随机数据并写入文件
generate_and_write_random_data('original.txt')
