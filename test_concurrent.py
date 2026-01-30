#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
高并发测试脚本 - 验证连接稳定性和吞吐量

这个脚本测试聊天室在高并发场景下的表现。
目标: 50-100个并发连接保持活跃30秒+
"""

import socket
import threading
import time
import sys
import struct
from datetime import datetime
import random
import string

# 导入测试框架
def encode_message(message):
    """编码消息"""
    if isinstance(message, str):
        message = message.encode('utf-8')
    length = len(message)
    header = struct.pack('!I', length)
    return header + message

def decode_message(buffer):
    """解码消息"""
    if len(buffer) < 4:
        return None, -1
    length = struct.unpack('!I', buffer[:4])[0]
    if len(buffer) < 4 + length:
        return None, -1
    message = buffer[4:4+length].decode('utf-8', errors='ignore')
    return message, 4 + length

class TestClient:
    """测试客户端"""
    def __init__(self, client_id, host='127.0.0.1', port=8080):
        self.client_id = client_id
        self.host = host
        self.port = port
        self.socket = None
        self.is_connected = False
        self.last_activity = time.time()
        self.recv_count = 0
        self.send_count = 0
        
    def connect(self):
        """连接"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            self.is_connected = True
            self.last_activity = time.time()
            
            # 启动接收线程
            recv_thread = threading.Thread(target=self._recv_loop, daemon=True)
            recv_thread.start()
            return True
        except Exception as e:
            print(f"  ✗ Client {self.client_id} 连接失败: {e}")
            return False
    
    def disconnect(self):
        """断开连接"""
        try:
            if self.socket:
                self.socket.close()
            self.is_connected = False
        except:
            pass
    
    def send_raw(self, data):
        """发送原始数据"""
        try:
            if not self.is_connected:
                return False
            self.socket.sendall(data)
            self.send_count += 1
            self.last_activity = time.time()
            return True
        except:
            self.is_connected = False
            return False
    
    def send_message(self, message):
        """发送消息"""
        encoded = encode_message(message)
        return self.send_raw(encoded)
    
    def _recv_loop(self):
        """接收循环"""
        buffer = b''
        while self.is_connected:
            try:
                data = self.socket.recv(4096)
                if not data:
                    self.is_connected = False
                    break
                buffer += data
                
                while len(buffer) > 0:
                    message, consumed = decode_message(buffer)
                    if consumed == -1:
                        break
                    elif consumed == 0:
                        break
                    else:
                        self.recv_count += 1
                        self.last_activity = time.time()
                        buffer = buffer[consumed:]
            except:
                self.is_connected = False
                break


def test_concurrent_connections(num_clients=50, duration=30, check_interval=5):
    """高并发连接测试"""
    print("\n" + "="*70)
    print(f"高并发测试: {num_clients}个客户端，{duration}秒")
    print("="*70)
    
    clients = []
    
    # 第一阶段: 建立连接
    print(f"\n[阶段1] 建立{num_clients}个连接")
    print("-"*70)
    
    start_time = time.time()
    success_count = 0
    
    for i in range(num_clients):
        client = TestClient(i)
        if client.connect():
            success_count += 1
            # 快速发送登录命令
            client.send_message(f"sign_up|test_{i}|pass123")
            time.sleep(0.05)  # 稍微错开
            client.send_message(f"sign_in|test_{i}|pass123")
            clients.append(client)
        
        if (i + 1) % 10 == 0:
            print(f"  已连接: {i+1}/{num_clients}")
    
    connect_time = time.time() - start_time
    print(f"✓ 成功连接: {success_count}/{num_clients} (耗时 {connect_time:.1f}s)")
    
    if success_count == 0:
        print("❌ 连接失败，无法继续测试")
        return False
    
    time.sleep(2)  # 等待登录完成
    
    # 第二阶段: 监测连接稳定性
    print(f"\n[阶段2] 监测{duration}秒内的连接稳定性")
    print("-"*70)
    
    start_time = time.time()
    check_times = []
    
    while time.time() - start_time < duration:
        elapsed = time.time() - start_time
        connected = sum(1 for c in clients if c.is_connected)
        
        if elapsed >= len(check_times) * check_interval:
            check_times.append(elapsed)
            print(f"  {elapsed:5.1f}s: 活跃连接 {connected:3}/{num_clients} ({connected/num_clients*100:5.1f}%)")
            
            # 发送心跳保活
            for c in clients:
                if c.is_connected:
                    c.send_message("heartbeat")
        
        time.sleep(0.5)
    
    total_duration = time.time() - start_time
    final_connected = sum(1 for c in clients if c.is_connected)
    
    # 第三阶段: 统计结果
    print(f"\n[阶段3] 测试结果统计")
    print("-"*70)
    
    total_sent = sum(c.send_count for c in clients)
    total_recv = sum(c.recv_count for c in clients)
    avg_lifetime = sum(time.time() - c.last_activity for c in clients) / len(clients) if clients else 0
    
    print(f"总耗时: {total_duration:.1f}秒")
    print(f"初始连接: {success_count}/{ num_clients}")
    print(f"最终连接: {final_connected}/{num_clients} ({final_connected/num_clients*100:.1f}%)")
    print(f"连接保持率: {final_connected/success_count*100:.1f}%")
    print(f"总消息发送: {total_sent}")
    print(f"总消息接收: {total_recv}")
    print(f"平均最后活动: {avg_lifetime:.1f}秒前")
    
    # 判定测试结果
    success_threshold = 0.95  # 95%连接保持率
    if final_connected / success_count >= success_threshold:
        print(f"\n✅ 测试通过: 连接保持率 {final_connected/success_count*100:.1f}% > {success_threshold*100:.0f}%")
        return True
    else:
        print(f"\n⚠️  测试警告: 连接保持率 {final_connected/success_count*100:.1f}% < {success_threshold*100:.0f}%")
        return False


def test_message_throughput(num_clients=50, duration=20):
    """消息吞吐量测试"""
    print("\n" + "="*70)
    print(f"吞吐量测试: {num_clients}个客户端")
    print("="*70)
    
    clients = []
    
    # 建立连接
    print(f"\n[阶段1] 建立{num_clients}个连接")
    for i in range(num_clients):
        client = TestClient(i)
        if client.connect():
            client.send_message(f"sign_up|perf_{i}|pass")
            client.send_message(f"sign_in|perf_{i}|pass")
            clients.append(client)
    
    print(f"✓ 已连接: {len(clients)}/{num_clients}")
    time.sleep(1)
    
    # 测试消息吞吐
    print(f"\n[阶段2] {duration}秒内发送消息")
    print("-"*70)
    
    start_time = time.time()
    messages_per_client = 0
    
    while time.time() - start_time < duration:
        for client in clients:
            if client.is_connected:
                # 发送广播消息
                msg = f"broadcast_chat|Test message {messages_per_client}\n"
                client.send_message(msg)
        messages_per_client += 1
        time.sleep(0.3)  # 每300ms发一轮 (稳定吞吐: 160 msg/sec)
    
    elapsed = time.time() - start_time
    
    # 统计结果
    total_sent = sum(c.send_count for c in clients)
    total_recv = sum(c.recv_count for c in clients)
    throughput = total_sent / elapsed
    
    print(f"\n[阶段3] 吞吐量统计")
    print("-"*70)
    print(f"测试时长: {elapsed:.1f}秒")
    print(f"总消息发送: {total_sent}")
    print(f"总消息接收: {total_recv}")
    print(f"吞吐率: {throughput:.0f} msg/sec")
    print(f"活跃连接: {sum(1 for c in clients if c.is_connected)}/{len(clients)}")
    
    # 清理
    for c in clients:
        c.disconnect()
    
    return True


def test_stress(num_clients_start=10, num_clients_max=100, step=10):
    """压力测试 - 逐步增加连接数"""
    print("\n" + "="*70)
    print("压力测试: 逐步增加连接数")
    print("="*70)
    
    results = []
    
    for num_clients in range(num_clients_start, num_clients_max + 1, step):
        print(f"\n[压力测试] {num_clients}个并发连接...")
        
        success = test_concurrent_connections(
            num_clients=num_clients,
            duration=15,
            check_interval=3
        )
        
        results.append({
            'clients': num_clients,
            'success': success
        })
        
        time.sleep(1)  # 测试间隔
    
    # 总结
    print("\n" + "="*70)
    print("压力测试结果总结")
    print("="*70)
    print(f"{'连接数':>8} | {'结果':>6}")
    print("-"*20)
    for r in results:
        status = "✅ PASS" if r['success'] else "❌ FAIL"
        print(f"{r['clients']:>8} | {status}")
    
    return results


def main():
    """主测试函数"""
    print("="*70)
    print("高并发测试套件")
    print("="*70)
    print("\n测试场景:")
    print("  1. 50个并发连接 30秒稳定性")
    print("  2. 100个并发连接 30秒稳定性")
    print("  3. 消息吞吐量测试")
    print("  4. 压力测试 (逐步增加连接)")
    
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--test', type=int, default=0, help='选择测试 (0=全部, 1-4=单项)')
    parser.add_argument('--clients', type=int, default=50, help='客户端数量')
    parser.add_argument('--duration', type=int, default=30, help='持续时间(秒)')
    args = parser.parse_args()
    
    results = {}
    
    if args.test in [0, 1]:
        results['50并发30秒'] = test_concurrent_connections(50, 30)
        time.sleep(2)
    
    if args.test in [0, 2]:
        results['100并发30秒'] = test_concurrent_connections(100, 30)
        time.sleep(2)
    
    if args.test in [0, 3]:
        results['吞吐量'] = test_message_throughput(50, 20)
        time.sleep(2)
    
    if args.test in [0, 4]:
        test_stress(10, 100, 20)
        return 0
    
    # 总结
    if results:
        print("\n" + "="*70)
        print("最终测试结果")
        print("="*70)
        for test_name, result in results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{test_name:20} : {status}")


if __name__ == "__main__":
    main()
