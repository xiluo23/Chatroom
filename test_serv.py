#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
聊天室服务器测试脚本
支持多个客户端的注册、登录和消息通信测试
"""

import socket
import threading
import time
import sys
import struct
from datetime import datetime

# ========== 协议编解码函数 ==========
def encode_message(message):
    """
    使用长度前缀协议编码消息
    格式: [4字节长度(网络字节序)][数据]
    """
    if isinstance(message, str):
        message = message.encode('utf-8')
    length = len(message)
    # 使用big-endian格式（网络字节序）编码长度
    header = struct.pack('!I', length)  # !I: big-endian unsigned int
    return header + message

def decode_message(buffer):
    """
    从缓冲区解析消息
    返回: (消息字符串, 消费的字节数) 如果消息完整
          (None, -1) 如果消息不完整
    """
    if len(buffer) < 4:
        return None, -1  # 还没有接收到长度头
    
    # 解析长度头
    length = struct.unpack('!I', buffer[:4])[0]
    
    # 检查是否接收了完整的消息
    if len(buffer) < 4 + length:
        return None, -1  # 消息不完整
    
    # 提取消息
    message = buffer[4:4+length].decode('utf-8', errors='ignore')
    return message, 4 + length

class ChatroomClient:
    """模拟聊天室客户端"""
    
    def __init__(self, username, server_host='127.0.0.1', server_port=8080):
        self.username = username
        self.server_host = server_host
        self.server_port = server_port
        self.socket = None
        self.is_connected = False
        self.is_running = False
        self.received_messages = []
        self.heartbeat_thread_started = False
        
    def connect(self):
        """连接到服务器"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.server_host, self.server_port))
            self.is_connected = True
            self.is_running = True
            print(f"[{self.username}] ✓ 已连接到服务器 {self.server_host}:{self.server_port}")
            # 启动接收线程
            recv_thread = threading.Thread(target=self._recv_loop, daemon=True)
            recv_thread.start()
            # 启动心跳线程
            if not self.heartbeat_thread_started:
                heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
                heartbeat_thread.start()
                self.heartbeat_thread_started = True
            return True
        except Exception as e:
            print(f"[{self.username}] ✗ 连接失败: {e}")
            return False
    
    def disconnect(self):
        """断开连接"""
        try:
            if self.socket:
                self.socket.close()
            self.is_connected = False
            print(f"[{self.username}] ✓ 已断开连接")
        except Exception as e:
            print(f"[{self.username}] ✗ 断开连接失败: {e}")
    
    def send_message(self, message):
        """发送消息到服务器（使用协议编码）"""
        try:
            if not self.is_connected:
                print(f"[{self.username}] ✗ 未连接到服务器")
                return False
            # 使用协议编码消息
            encoded = encode_message(message)
            self.socket.sendall(encoded)
            return True
        except Exception as e:
            print(f"[{self.username}] ✗ 发送失败: {e}")
            self.is_connected = False
            return False
    
    def _recv_loop(self):
        """接收消息的循环（支持协议解码和缓冲）"""
        recv_buffer = b''  # 接收缓冲区用于处理粘包/拆包
        
        while self.is_connected:
            try:
                data = self.socket.recv(1024)
                if not data:
                    print(f"[{self.username}] ✗ 连接已断开")
                    self.is_connected = False
                    break
                
                # 将接收的数据追加到缓冲区
                recv_buffer += data
                
                # 循环提取完整的消息
                while len(recv_buffer) > 0:
                    message, consumed = decode_message(recv_buffer)
                    if consumed == -1:
                        # 消息不完整，等待更多数据
                        break
                    elif consumed == 0:
                        # 缓冲区为空
                        break
                    else:
                        # 成功解析一个完整的消息
                        self.received_messages.append(message)
                        self._handle_response(message)
                        # 从缓冲区中移除已处理的数据
                        recv_buffer = recv_buffer[consumed:]
                
            except socket.timeout:
                continue
            except Exception as e:
                if self.is_connected:
                    print(f"[{self.username}] ✗ 接收错误: {e}")
                self.is_connected = False
                break
    
    def _heartbeat_loop(self):
        """定期发送心跳消息以保持连接活跃
        心跳间隔设置为18秒，略少于服务器30秒超时时间
        这样可以确保在服务器进行超时检查前有足够的时间更新last_active
        """
        while self.is_connected:
            try:
                time.sleep(18)  # 18秒发送一次心跳，小于服务器30秒超时
                if self.is_connected:
                    self.send_message("heartbeat")
                    # 不打印心跳消息，以保持日志整洁
            except Exception as e:
                if self.is_connected:
                    print(f"[{self.username}] ✗ 心跳发送失败: {e}")
                break
    
    def _handle_response(self, response):
        """处理服务器响应"""
        # 解析响应格式: cmd|status|data
        parts = response.strip().split('|', 2)
        
        if len(parts) < 2:
            print(f"[{self.username}] 收到: {response.strip()}")
            return
        
        cmd = parts[0]
        status = parts[1]
        data = parts[2] if len(parts) > 2 else ""
        
        if cmd == "sign_up":
            if status == "1":
                print(f"[{self.username}] ✓ 注册成功 - {data}")
            else:
                print(f"[{self.username}] ✗ 注册失败 - {data}")
        
        elif cmd == "sign_in":
            if status == "1":
                print(f"[{self.username}] ✓ 登录成功")
            else:
                print(f"[{self.username}] ✗ 登录失败 - {data}")
        
        elif cmd == "show_online_user":
            if status == "1":
                users = data.replace("|", ", ")
                print(f"[{self.username}] 在线用户: {users}")
            else:
                print(f"[{self.username}] ✗ 获取在线用户失败 - {data}")
        
        elif cmd == "single_chat":
            if status == "1":
                # 收到消息: sender;content
                if ";" in data:
                    sender, content = data.split(";", 1)
                    print(f"[{self.username}] 来自 {sender} 的消息: {content}")
            elif status == "2":
                print(f"[{self.username}] ✓ 消息已发送")
            else:
                print(f"[{self.username}] ✗ 单人聊天失败 - {data}")
        
        elif cmd == "multi_chat":
            if status == "2":
                # 收到消息: sender;content
                if ";" in data:
                    sender, content = data.split(";", 1)
                    print(f"[{self.username}] [群组] 来自 {sender} 的消息: {content}")
            elif status == "1":
                print(f"[{self.username}] ✓ 群组消息已发送")
            else:
                print(f"[{self.username}] ✗ 群组聊天失败 - {data}")
        
        elif cmd == "broadcast_chat":
            if status == "1":
                print(f"[{self.username}] ✓ 广播消息已发送")
            elif status == "2":
                # 收到广播消息: sender;content
                if ";" in data:
                    sender, content = data.split(";", 1)
                    print(f"[{self.username}] [广播] 来自 {sender}: {content}")
            else:
                print(f"[{self.username}] ✗ 广播失败 - {data}")
        
        elif cmd == "show_history":
            if status == "1":
                # 历史消息格式: msg1|msg2|msg3...
                messages = data.split("|") if data else []
                print(f"[{self.username}] 聊天历史 ({len(messages)} 条消息):")
                for msg in messages:
                    if msg:
                        print(f"  {msg}")
            else:
                print(f"[{self.username}] ✗ 查看历史失败 - {data}")
        
        elif cmd == "heartbeat":
            # 心跳响应不需要打印，保持静默
            pass
        
        elif cmd == "chat_unread":
            if status == "1":
                print(f"[{self.username}] 📬 未读消息: {data}")
        
        else:
            print(f"[{self.username}] 收到响应: {response.strip()}")
    
    def sign_up(self, password):
        """注册用户"""
        message = f"sign_up|{self.username}|{password}"
        print(f"[{self.username}] 正在注册...")
        return self.send_message(message)
    
    def sign_in(self, password):
        """登录用户"""
        message = f"sign_in|{self.username}|{password}"
        print(f"[{self.username}] 正在登录...")
        return self.send_message(message)
    
    def show_online_user(self):
        """查询在线用户"""
        message = "show_online_user\n"
        return self.send_message(message)
    
    def single_chat(self, target_user, content):
        """发送单人聊天消息"""
        message = f"single_chat|{target_user}|{content}\n"
        print(f"[{self.username}] 向 {target_user} 发送: {content}")
        return self.send_message(message)
    
    def multi_chat(self, target_users, content):
        """发送群组聊天消息
        target_users: 用户列表，用空格分隔
        """
        message = f"multi_chat|{target_users}|{content}\n"
        print(f"[{self.username}] 向 [{target_users}] 发送群消息: {content}")
        return self.send_message(message)
    
    def broadcast_chat(self, content):
        """发送广播消息"""
        message = f"broadcast_chat|{content}\n"
        print(f"[{self.username}] 发送广播消息: {content}")
        return self.send_message(message)
    
    def show_history(self, target_user):
        """查看与指定用户的聊天历史"""
        message = f"show_history|{target_user}\n"
        print(f"[{self.username}] 查看与 {target_user} 的聊天历史")
        return self.send_message(message)
    
    def wait_for_response(self, timeout=2):
        """等待响应"""
        start_time = time.time()
        initial_count = len(self.received_messages)
        while time.time() - start_time < timeout:
            if len(self.received_messages) > initial_count:
                return True
            time.sleep(0.1)
        return False


def test_basic_registration_login():
    """测试1: 基础注册和登录"""
    print("\n" + "="*60)
    print("测试1: 基础注册和登录")
    print("="*60)
    
    import random
    import string
    # 生成唯一的用户名，避免重复注册导致的错误
    suffix = ''.join(random.choices(string.digits, k=4))
    client1 = ChatroomClient(f"alice{suffix}")
    client2 = ChatroomClient(f"bob{suffix}")
    
    try:
        # 连接
        if not client1.connect():
            return False
        if not client2.connect():
            return False
        
        time.sleep(0.5)
        
        # 注册
        client1.sign_up("password123")
        if not client1.wait_for_response(3):
            print(f"[{client1.username}] ✗ 注册响应超时")
            return False
        time.sleep(0.5)
        
        client2.sign_up("password456")
        if not client2.wait_for_response(3):
            print(f"[{client2.username}] ✗ 注册响应超时")
            return False
        time.sleep(0.5)
        
        # 登录
        client1.sign_in("password123")
        if not client1.wait_for_response(3):
            print(f"[{client1.username}] ✗ 登录响应超时")
            return False
        time.sleep(0.5)
        
        client2.sign_in("password456")
        if not client2.wait_for_response(3):
            print(f"[{client2.username}] ✗ 登录响应超时")
            return False
        time.sleep(0.5)
        
        print("\n✓ 测试1完成")
        return True
        
    finally:
        client1.disconnect()
        client2.disconnect()

def test_show_online_users():
    """测试2: 显示在线用户"""
    print("\n" + "="*60)
    print("测试2: 显示在线用户")
    print("="*60)
    
    client1 = ChatroomClient("alice")
    client2 = ChatroomClient("bob")
    client3 = ChatroomClient("charlie")
    
    try:
        # 连接和登录
        clients = [client1, client2, client3]
        for client in clients:
            if not client.connect():
                return False
        
        time.sleep(0.5)
        
        for client in clients:
            client.sign_up("password")
            client.wait_for_response(2)
            time.sleep(0.3)
        
        for client in clients:
            client.sign_in("password")
            client.wait_for_response(2)
            time.sleep(0.3)
        
        time.sleep(1)
        
        # 查询在线用户
        print("\n查询在线用户:")
        client1.show_online_user()
        client1.wait_for_response(3)
        
        print("\n✓ 测试2完成")
        return True
        
    finally:
        for client in clients:
            client.disconnect()

def test_single_chat():
    """测试3: 单人聊天"""
    print("\n" + "="*60)
    print("测试3: 单人聊天")
    print("="*60)
    
    client1 = ChatroomClient("alice")
    client2 = ChatroomClient("bob")
    
    try:
        # 连接和登录
        for client in [client1, client2]:
            if not client.connect():
                return False
        
        time.sleep(0.5)
        
        for client in [client1, client2]:
            client.sign_up("password")
            client.wait_for_response(2)
            time.sleep(0.3)
        
        for client in [client1, client2]:
            client.sign_in("password")
            client.wait_for_response(2)
            time.sleep(0.3)
        
        time.sleep(1)
        
        # Alice向Bob发送消息
        print("\nAlice向Bob发送消息:")
        client1.single_chat("bob", "你好Bob，这是一条测试消息")
        client1.wait_for_response(2)
        time.sleep(0.5)
        
        if client2.received_messages:
            print("Bob收到了消息")
        
        # Bob向Alice回复
        print("\nBob向Alice回复:")
        client2.single_chat("alice", "你好Alice，我收到你的消息了")
        client2.wait_for_response(2)
        time.sleep(0.5)
        
        print("\n✓ 测试3完成")
        return True
        
    finally:
        client1.disconnect()
        client2.disconnect()

def test_multi_chat():
    """测试4: 群组聊天"""
    print("\n" + "="*60)
    print("测试4: 群组聊天")
    print("="*60)
    
    client1 = ChatroomClient("alice")
    client2 = ChatroomClient("bob")
    client3 = ChatroomClient("charlie")
    
    try:
        # 连接和登录
        clients = [client1, client2, client3]
        for client in clients:
            if not client.connect():
                return False
        
        time.sleep(0.5)
        
        for client in clients:
            client.sign_up("password")
            client.wait_for_response(2)
            time.sleep(0.3)
        
        for client in clients:
            client.sign_in("password")
            client.wait_for_response(2)
            time.sleep(0.3)
        
        time.sleep(1)
        
        # Alice向Bob和Charlie发送群消息
        print("\nAlice向Bob和Charlie发送群消息:")
        client1.multi_chat("bob charlie", "大家好，这是一条群组测试消息")
        client1.wait_for_response(2)
        time.sleep(0.5)
        
        print("\n✓ 测试4完成")
        return True
        
    finally:
        for client in clients:
            client.disconnect()


def test_broadcast_chat():
    """测试5: 广播聊天"""
    print("\n" + "="*60)
    print("测试5: 广播聊天")
    print("="*60)
    
    client1 = ChatroomClient("alice")
    client2 = ChatroomClient("bob")
    client3 = ChatroomClient("charlie")
    
    try:
        # 连接和登录
        clients = [client1, client2, client3]
        for client in clients:
            if not client.connect():
                return False
        
        time.sleep(0.5)
        
        for client in clients:
            client.sign_up("password")
            client.wait_for_response(2)
            time.sleep(0.3)
        
        for client in clients:
            client.sign_in("password")
            client.wait_for_response(2)
            time.sleep(0.3)
        
        time.sleep(1)
        
        # Alice发送广播消息
        print("\nAlice发送广播消息:")
        client1.broadcast_chat("各位同学，这是一条广播消息！")
        client1.wait_for_response(2)
        time.sleep(1)
        
        print("\n✓ 测试5完成")
        return True
        
    finally:
        for client in clients:
            client.disconnect()


def test_cross_communication():
    """测试多客户端交叉通信 - 触发线程竞争问题"""
    print("\n" + "="*60)
    print("测试: 多客户端交叉通信（高强度压力测试）")
    print("="*60)
    print("目标: 检测多线程并发发送时的问题\n")
    
    import random
    import string
    # 生成唯一的用户名
    suffix = ''.join(random.choices(string.digits, k=4))
    num_clients = 4  # 4个客户端
    clients = [ChatroomClient(f"user{i}_{suffix}") for i in range(num_clients)]
    
    try:
        # 连接和登录阶段
        print("步骤1: 连接所有客户端...")
        for client in clients:
            if not client.connect():
                return False
        
        time.sleep(0.5)
        
        print("步骤2: 所有客户端注册...")
        for client in clients:
            client.sign_up("password")
            if not client.wait_for_response(3):
                print(f"[{client.username}] ✗ 注册失败或超时")
                return False
            time.sleep(0.1)
        
        time.sleep(0.5)
        
        print("步骤3: 所有客户端登录...")
        for client in clients:
            client.sign_in("password")
            if not client.wait_for_response(3):
                print(f"[{client.username}] ✗ 登录失败或超时")
                return False
            time.sleep(0.1)
        
        time.sleep(1)
        
        print("\n步骤4: 开始交叉通信测试...")
        print("场景: 多个客户端同时互相发送消息\n")
        
        # 测试参数
        rounds = 3  # 3轮
        messages_per_target = 3  # 每个目标3条消息
        
        all_failed = False
        
        for round_num in range(rounds):
            print(f"--- 第 {round_num+1} 轮 ---")
            start_time = time.time()
            
            # 创建线程让每个客户端并发发送消息
            def send_messages(sender, sender_idx):
                try:
                    for target_idx in range(num_clients):
                        if target_idx != sender_idx and sender.is_connected:
                            target_name = clients[target_idx].username
                            for msg_num in range(messages_per_target):
                                if not sender.is_connected:
                                    return
                                msg = f"test_msg_{round_num+1}_{msg_num+1}"
                                sender.single_chat(target_name, msg)
                                time.sleep(0.02)
                except Exception as e:
                    print(f"  [{sender.username}] 发送异常: {e}")
            
            # 启动所有客户端的发送线程
            threads = []
            for i, client in enumerate(clients):
                if not client.is_connected:
                    continue
                t = threading.Thread(target=send_messages, args=(client, i), daemon=True)
                threads.append(t)
                t.start()
            
            # 等待所有线程完成
            for t in threads:
                t.join(timeout=30)
            
            time.sleep(0.5)
            
            # 检查连接状态
            connected_count = sum(1 for c in clients if c.is_connected)
            print(f"  连接状态: {connected_count}/{num_clients} 客户端在线")
            elapsed = time.time() - start_time
            print(f"  本轮耗时: {elapsed:.2f}秒")
            
            if connected_count == 0:
                print("\n✗ 所有客户端都已断开连接！")
                all_failed = True
                return False
            
            if connected_count < num_clients:
                print(f"  ⚠️  有 {num_clients - connected_count} 个客户端已断开")
        
        print("\n✓ 交叉通信测试完成")
        return True
        
    except Exception as e:
        print(f"\n✗ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        print("\n清理: 断开所有客户端...")
        for client in clients:
            if client.is_connected:
                client.disconnect()


def test_show_history():
    """测试6: 查看聊天历史"""
    print("\n" + "="*60)
    print("测试6: 查看聊天历史")
    print("="*60)
    
    client1 = ChatroomClient("alice")
    client2 = ChatroomClient("bob")
    
    try:
        # 连接和登录
        for client in [client1, client2]:
            if not client.connect():
                return False
        
        time.sleep(0.5)
        
        for client in [client1, client2]:
            client.sign_up("password")
            client.wait_for_response(2)
            time.sleep(0.3)
        
        for client in [client1, client2]:
            client.sign_in("password")
            client.wait_for_response(2)
            time.sleep(0.3)
        
        time.sleep(1)
        
        # Alice和Bob互相发送消息
        print("\nAlice向Bob发送消息...")
        client1.single_chat("bob", "你好Bob！")
        client1.wait_for_response(2)
        time.sleep(0.5)
        
        print("Bob向Alice回复...")
        client2.single_chat("alice", "你好Alice！")
        client2.wait_for_response(2)
        time.sleep(0.5)
        
        # 查看聊天历史
        print("\nAlice查看与Bob的聊天历史...")
        message = "show_history|bob\n"
        client1.send_message(message)
        client1.wait_for_response(3)
        time.sleep(0.5)
        
        print("\n✓ 测试6完成")
        return True
        
    finally:
        client1.disconnect()
        client2.disconnect()


def test_heartbeat():
    """测试7: 心跳机制"""
    print("\n" + "="*60)
    print("测试7: 心跳机制")
    print("="*60)
    print("让客户端保持连接20秒，验证心跳是否正常工作")
    
    client1 = ChatroomClient("alice")
    
    try:
        if not client1.connect():
            return False
        
        time.sleep(0.5)
        
        client1.sign_up("password")
        client1.wait_for_response(2)
        time.sleep(0.5)
        
        client1.sign_in("password")
        client1.wait_for_response(2)
        time.sleep(0.5)
        
        print("\n保持连接并发送心跳...")
        # 客户端应该每20秒发送一次心跳
        for i in range(3):
            time.sleep(5)
            print(f"  [{i*5+5}秒] 保持在线...")
            if not client1.is_connected:
                print("  ✗ 连接已断开")
                return False
        
        print("\n✓ 测试7完成（心跳正常）")
        return True
        
    finally:
        client1.disconnect()


def test_high_concurrency(num_clients=10, duration_seconds=30, messages_per_client=100):
    """高并发性能测试
    
    参数:
        num_clients: 客户端数量（默认10个）
        duration_seconds: 测试持续时间（秒）
        messages_per_client: 每个客户端发送的消息数
    """
    print("\n" + "="*60)
    print("高并发性能测试")
    print("="*60)
    print(f"配置: {num_clients}个客户端, {duration_seconds}秒持续测试, 每个客户端发{messages_per_client}条消息")
    print()
    
    import random
    import string
    from concurrent.futures import ThreadPoolExecutor, as_completed
    
    suffix = ''.join(random.choices(string.digits, k=4))
    clients = [ChatroomClient(f"stress_{i}_{suffix}") for i in range(num_clients)]
    
    # 统计指标
    stats = {
        'total_messages': 0,
        'successful_messages': 0,
        'failed_messages': 0,
        'disconnected_clients': 0,
        'start_time': None,
        'end_time': None,
        'errors': []
    }
    
    try:
        # 步骤1: 连接和认证
        print("步骤1: 连接和认证阶段...")
        stats['start_time'] = time.time()
        
        for client in clients:
            if not client.connect():
                stats['disconnected_clients'] += 1
                continue
        
        time.sleep(0.5)
        
        # 注册和登录
        for client in clients:
            if not client.is_connected:
                continue
            client.sign_up("password")
            client.wait_for_response(2)
            time.sleep(0.05)
        
        time.sleep(0.5)
        
        for client in clients:
            if not client.is_connected:
                continue
            client.sign_in("password")
            client.wait_for_response(2)
            time.sleep(0.05)
        
        connected_count = sum(1 for c in clients if c.is_connected)
        print(f"✓ 认证完成: {connected_count}/{num_clients} 客户端在线")
        time.sleep(1)
        
        # 步骤2: 高并发消息发送阶段
        print(f"\n步骤2: 高并发消息发送（{duration_seconds}秒）...")
        
        send_start = time.time()
        
        def send_message_worker(client_id, client):
            """工作线程：发送消息"""
            local_success = 0
            local_failed = 0
            try:
                for msg_id in range(messages_per_client):
                    if not client.is_connected:
                        break
                    
                    # 随机选择目标（不包括自己）
                    other_clients = [c for i, c in enumerate(clients) 
                                    if i != client_id and c.is_connected]
                    if not other_clients:
                        continue
                    
                    target = random.choice(other_clients)
                    msg = f"perf_test_{msg_id}"
                    
                    if client.single_chat(target.username, msg):
                        local_success += 1
                    else:
                        local_failed += 1
                    
                    time.sleep(0.011)  # 极小延迟增加吞吐量
                    
            except Exception as e:
                local_failed += messages_per_client
                stats['errors'].append(str(e))
            
            return local_success, local_failed
        
        # 使用线程池并发发送消息
        with ThreadPoolExecutor(max_workers=min(num_clients, 20)) as executor:
            futures = []
            for i, client in enumerate(clients):
                if client.is_connected:
                    future = executor.submit(send_message_worker, i, client)
                    futures.append(future)
            
            # 收集结果
            for future in as_completed(futures, timeout=duration_seconds + 10):
                try:
                    success, failed = future.result()
                    stats['successful_messages'] += success
                    stats['failed_messages'] += failed
                    stats['total_messages'] += success + failed
                except Exception as e:
                    stats['errors'].append(str(e))
        
        send_end = time.time()
        actual_duration = send_end - send_start
        
        # 等待响应处理
        print("等待响应处理...")
        time.sleep(2)
        
        # 步骤3: 统计和分析
        stats['end_time'] = time.time()
        
        connected_now = sum(1 for c in clients if c.is_connected)
        stats['disconnected_clients'] = num_clients - connected_now
        
        # 计算性能指标
        total_time = stats['end_time'] - stats['start_time']
        throughput = stats['total_messages'] / actual_duration if actual_duration > 0 else 0
        success_rate = (stats['successful_messages'] / stats['total_messages'] * 100) \
                      if stats['total_messages'] > 0 else 0
        
        print("\n" + "="*60)
        print("性能测试结果")
        print("="*60)
        print(f"总消息数:        {stats['total_messages']}")
        print(f"成功消息:        {stats['successful_messages']}")
        print(f"失败消息:        {stats['failed_messages']}")
        print(f"成功率:          {success_rate:.2f}%")
        print(f"吞吐量:          {throughput:.2f} msg/sec")
        print(f"测试耗时:        {actual_duration:.2f} 秒")
        print(f"客户端在线:      {connected_now}/{num_clients}")
        print(f"客户端断开:      {stats['disconnected_clients']}")
        
        if stats['errors']:
            print(f"\n错误日志 ({len(stats['errors'])} 条):")
            for err in stats['errors'][:5]:  # 只显示前5条
                print(f"  - {err}")
        
        # 评估结果
        print("\n评估:")
        if success_rate >= 99:
            print("✓ 优秀: 成功率 >= 99%")
        elif success_rate >= 95:
            print("△ 良好: 成功率 >= 95%")
        elif success_rate >= 80:
            print("⚠️  一般: 成功率 >= 80%")
        else:
            print("✗ 差: 成功率 < 80%")
        
        if stats['disconnected_clients'] == 0:
            print("✓ 优秀: 所有客户端保持在线")
        elif stats['disconnected_clients'] <= num_clients * 0.1:
            print(f"△ 良好: 客户端断开率 <= 10%")
        else:
            print(f"✗ 差: 客户端断开率 > 10%")
        
        return success_rate >= 80 and stats['disconnected_clients'] <= num_clients * 0.2
        
    except Exception as e:
        print(f"\n✗ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        print("\n清理: 断开所有客户端...")
        for client in clients:
            if client.is_connected:
                client.disconnect()


def test_stress_single_client(duration_seconds=15, messages_per_second=10):
    """单客户端压力测试
    
    参数:
        duration_seconds: 测试持续时间（秒）
        messages_per_second: 每秒发送的消息数
    """
    print("\n" + "="*60)
    print("单客户端压力测试")
    print("="*60)
    print(f"配置: 持续{duration_seconds}秒, 每秒发送{messages_per_second}条消息")
    print()
    
    import random
    import string
    
    suffix = ''.join(random.choices(string.digits, k=4))
    client1 = ChatroomClient(f"stress_sender_{suffix}")
    client2 = ChatroomClient(f"stress_receiver_{suffix}")
    
    stats = {
        'messages_sent': 0,
        'messages_received': 0,
        'errors': 0,
        'start_time': None,
        'end_time': None
    }
    
    try:
        # 连接和认证
        print("连接和认证...")
        for client in [client1, client2]:
            if not client.connect():
                return False
        
        time.sleep(0.3)
        
        for client in [client1, client2]:
            client.sign_up("password")
            client.wait_for_response(2)
        
        time.sleep(0.3)
        
        for client in [client1, client2]:
            client.sign_in("password")
            client.wait_for_response(2)
        
        time.sleep(0.5)
        
        # 开始高频发送
        print(f"开始发送 ({duration_seconds}秒)...\n")
        stats['start_time'] = time.time()
        
        msg_count = 0
        start_msg_count = len(client2.received_messages)
        
        while time.time() - stats['start_time'] < duration_seconds:
            for _ in range(messages_per_second):
                msg = f"msg_{msg_count}"
                if client1.single_chat(client2.username, msg):
                    stats['messages_sent'] += 1
                else:
                    stats['errors'] += 1
                msg_count += 1
                time.sleep(1.0 / (messages_per_second * 10))  # 细粒度控制
            
            elapsed = time.time() - stats['start_time']
            received = len(client2.received_messages) - start_msg_count
            print(f"  [{elapsed:.1f}s] 发送: {stats['messages_sent']:4d}, 接收: {received:4d}")
            time.sleep(0.1)
        
        stats['end_time'] = time.time()
        actual_duration = stats['end_time'] - stats['start_time']
        stats['messages_received'] = len(client2.received_messages) - start_msg_count
        
        # 输出结果
        throughput = stats['messages_sent'] / actual_duration if actual_duration > 0 else 0
        latency = (stats['messages_sent'] - stats['messages_received']) / stats['messages_sent'] * 100 \
                  if stats['messages_sent'] > 0 else 0
        
        print("\n" + "="*60)
        print("单客户端压力测试结果")
        print("="*60)
        print(f"发送消息:        {stats['messages_sent']}")
        print(f"接收消息:        {stats['messages_received']}")
        print(f"发送失败:        {stats['errors']}")
        print(f"吞吐量:          {throughput:.2f} msg/sec")
        print(f"消息延迟率:      {latency:.2f}%")
        print(f"测试耗时:        {actual_duration:.2f} 秒")
        
        return stats['messages_sent'] > 0
        
    finally:
        client1.disconnect()
        client2.disconnect()


def test_connection_stability(num_clients=20, hold_time=60):
    """连接稳定性测试
    
    参数:
        num_clients: 客户端数量
        hold_time: 保持连接的时间（秒）
    """
    print("\n" + "="*60)
    print("连接稳定性测试")
    print("="*60)
    print(f"配置: {num_clients}个客户端, 保持连接{hold_time}秒")
    print()
    
    import random
    import string
    
    suffix = ''.join(random.choices(string.digits, k=4))
    clients = [ChatroomClient(f"stable_{i}_{suffix}") for i in range(num_clients)]
    
    try:
        # 连接和认证
        print("连接和认证...")
        for client in clients:
            if not client.connect():
                continue
        
        time.sleep(0.5)
        
        for client in clients:
            if client.is_connected:
                client.sign_up("password")
                client.wait_for_response(1)
        
        time.sleep(0.3)
        
        for client in clients:
            if client.is_connected:
                client.sign_in("password")
                client.wait_for_response(1)
        
        time.sleep(1)
        
        initial_connected = sum(1 for c in clients if c.is_connected)
        print(f"初始在线: {initial_connected}/{num_clients}")
        
        # 保持连接并监控
        print(f"\n保持连接{hold_time}秒...\n")
        
        for i in range(hold_time):
            time.sleep(1)
            connected = sum(1 for c in clients if c.is_connected)
            
            # 每5秒显示一次状态
            if (i + 1) % 5 == 0:
                print(f"  [{i+1:2d}s] 在线: {connected}/{num_clients}", end="")
                if connected < initial_connected:
                    print(f" (↓ {initial_connected - connected}个断开)")
                else:
                    print()
        
        final_connected = sum(1 for c in clients if c.is_connected)
        disconnected = initial_connected - final_connected
        
        print("\n" + "="*60)
        print("连接稳定性测试结果")
        print("="*60)
        print(f"初始在线:        {initial_connected}/{num_clients}")
        print(f"最终在线:        {final_connected}/{num_clients}")
        print(f"断开连接:        {disconnected}")
        print(f"稳定性:          {final_connected/initial_connected*100:.2f}%")
        
        if disconnected == 0:
            print("\n✓ 优秀: 所有连接始终稳定")
        elif disconnected <= initial_connected * 0.05:
            print("\n△ 良好: 断开率 <= 5%")
        else:
            print("\n⚠️  需要改进: 连接不稳定")
        
        return disconnected == 0
        
    finally:
        for client in clients:
            if client.is_connected:
                client.disconnect()


def run_all_tests():
    """运行所有测试"""
    print("\n" + "="*60)
    print("聊天室服务器完整测试套件")
    print("="*60)
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    tests = [
        ("基础注册和登录", test_basic_registration_login),
        ("显示在线用户", test_show_online_users),
        ("单人聊天", test_single_chat),
        ("群组聊天", test_multi_chat),
        ("广播聊天", test_broadcast_chat),
        ("查看聊天历史", test_show_history),
        ("心跳机制", test_heartbeat),
        ("多客户端交叉通信", test_cross_communication),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, "✓ 通过" if result else "✗ 失败"))
        except Exception as e:
            print(f"\n✗ {test_name} 异常: {e}")
            results.append((test_name, "✗ 异常"))
        time.sleep(2)
    
    # 输出测试结果总结
    print("\n" + "="*60)
    print("测试结果总结")
    print("="*60)
    for test_name, result in results:
        print(f"{result} - {test_name}")
    
    # 统计通过和失败
    passed = sum(1 for _, r in results if "通过" in r)
    failed = len(results) - passed
    
    print(f"\n总计: {len(results)} 个测试, 通过 {passed} 个, 失败 {failed} 个")
    print(f"结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


def run_performance_tests():
    """运行所有性能测试"""
    print("\n" + "="*80)
    print(" "*20 + "聊天室服务器性能测试套件")
    print("="*80)
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    performance_tests = [
        ("单客户端压力测试", lambda: test_stress_single_client(duration_seconds=15, messages_per_second=20)),
        ("连接稳定性测试", lambda: test_connection_stability(num_clients=15, hold_time=30)),
        ("高并发性能测试", lambda: test_high_concurrency(num_clients=8, duration_seconds=20, messages_per_client=50)),
    ]
    
    results = []
    for test_name, test_func in performance_tests:
        try:
            result = test_func()
            results.append((test_name, "✓ 通过" if result else "✗ 失败"))
        except Exception as e:
            print(f"\n✗ {test_name} 异常: {e}")
            results.append((test_name, "✗ 异常"))
        time.sleep(3)
    
    # 输出结果总结
    print("\n" + "="*80)
    print("性能测试结果总结")
    print("="*80)
    for test_name, result in results:
        print(f"{result} - {test_name}")
    
    print(f"\n结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    try:
        print("聊天室服务器测试工具")
        print("="*60)
        print("选择要运行的测试:")
        print("  1. 功能测试（所有功能验证）")
        print("  2. 性能测试（吞吐量、延迟、稳定性）")
        print("  3. 单客户端压力测试")
        print("  4. 连接稳定性测试")
        print("  5. 高并发测试")
        print("  0. 退出")
        print("="*60)
        
        import sys
        if len(sys.argv) > 1:
            choice = sys.argv[1]
        else:
            choice = input("请选择 [0-5]: ").strip()
        
        if choice == "1":
            run_all_tests()
        elif choice == "2":
            run_performance_tests()
        elif choice == "3":
            test_stress_single_client(duration_seconds=30, messages_per_second=50)
        elif choice == "4":
            test_connection_stability(num_clients=64, hold_time=60)
        elif choice == "5":
            test_high_concurrency(num_clients=40, duration_seconds=60, messages_per_client=100)
        elif choice == "0":
            print("退出")
            sys.exit(0)
        else:
            print("无效的选择")
            sys.exit(1)
    
    except KeyboardInterrupt:
        print("\n\n测试被中断")
        sys.exit(0)
