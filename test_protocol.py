#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
协议测试脚本 - 验证粘包/拆包处理
"""

import struct
import sys

def encode_message(message):
    """使用长度前缀协议编码消息"""
    if isinstance(message, str):
        message = message.encode('utf-8')
    length = len(message)
    header = struct.pack('!I', length)
    return header + message

def decode_message(buffer):
    """从缓冲区解析消息"""
    if len(buffer) < 4:
        return None, -1
    
    length = struct.unpack('!I', buffer[:4])[0]
    
    if len(buffer) < 4 + length:
        return None, -1
    
    message = buffer[4:4+length].decode('utf-8', errors='ignore')
    return message, 4 + length

def test_basic_encoding():
    """测试基本的编码解码"""
    print("=" * 50)
    print("测试1: 基本编码解码")
    print("=" * 50)
    
    message = "sign_up|user1|password"
    encoded = encode_message(message)
    print(f"原始消息: {message}")
    print(f"编码后长度: {len(encoded)} 字节")
    print(f"长度字段: {hex(struct.unpack('!I', encoded[:4])[0])}")
    
    decoded, consumed = decode_message(encoded)
    print(f"解码后消息: {decoded}")
    print(f"消费字节数: {consumed}")
    assert decoded == message, "编码解码不匹配！"
    print("✓ 测试通过\n")

def test_sticky_packets():
    """测试粘包处理"""
    print("=" * 50)
    print("测试2: 粘包处理（两个消息在一个buffer中）")
    print("=" * 50)
    
    msg1 = "sign_up|user1|pass1"
    msg2 = "sign_in|user1|pass1"
    
    # 模拟两个消息被粘在一起
    buffer = encode_message(msg1) + encode_message(msg2)
    print(f"缓冲区总大小: {len(buffer)} 字节")
    
    # 第一个消息
    msg_out, consumed = decode_message(buffer)
    assert msg_out == msg1, f"第一个消息不匹配！{msg_out}"
    print(f"✓ 提取第一个消息: {msg_out} ({consumed} 字节)")
    
    # 移除已处理的数据
    buffer = buffer[consumed:]
    
    # 第二个消息
    msg_out, consumed = decode_message(buffer)
    assert msg_out == msg2, f"第二个消息不匹配！{msg_out}"
    print(f"✓ 提取第二个消息: {msg_out} ({consumed} 字节)")
    
    print("✓ 粘包处理测试通过\n")

def test_fragmented_packets():
    """测试拆包处理"""
    print("=" * 50)
    print("测试3: 拆包处理（一个消息分多次接收）")
    print("=" * 50)
    
    message = "This is a long message for testing packet fragmentation"
    encoded = encode_message(message)
    print(f"完整编码消息长度: {len(encoded)} 字节")
    
    # 模拟分三次接收
    buffer = b''
    chunks = [encoded[:10], encoded[10:35], encoded[35:]]
    
    for i, chunk in enumerate(chunks):
        buffer += chunk
        print(f"第{i+1}次接收 ({len(chunk)} 字节)，缓冲区总长: {len(buffer)} 字节")
        
        msg_out, consumed = decode_message(buffer)
        if consumed == -1:
            print(f"  消息不完整，继续等待...")
        else:
            print(f"  ✓ 消息完整，提取: {msg_out}")
            assert msg_out == message, "拆包后消息不匹配！"
            buffer = buffer[consumed:]
    
    print("✓ 拆包处理测试通过\n")

def test_multiple_mixed():
    """测试混合场景"""
    print("=" * 50)
    print("测试4: 混合场景（粘包+拆包）")
    print("=" * 50)
    
    msg1 = "short"
    msg2 = "medium_message"
    msg3 = "long message for testing"
    
    # 创建完整数据
    complete_data = encode_message(msg1) + encode_message(msg2) + encode_message(msg3)
    print(f"完整数据: {len(complete_data)} 字节")
    
    # 随机分割（模拟网络分割）
    buffer = b''
    chunks = [complete_data[:15], complete_data[15:45], complete_data[45:]]
    extracted_msgs = []
    
    for i, chunk in enumerate(chunks):
        buffer += chunk
        print(f"第{i+1}次接收 ({len(chunk)} 字节)，缓冲区: {len(buffer)} 字节")
        
        # 提取所有完整的消息
        while True:
            msg_out, consumed = decode_message(buffer)
            if consumed == -1:
                print(f"  消息不完整，等待更多数据")
                break
            elif consumed == 0:
                print(f"  缓冲区为空")
                break
            else:
                print(f"  ✓ 提取消息: {msg_out}")
                extracted_msgs.append(msg_out)
                buffer = buffer[consumed:]
    
    assert extracted_msgs == [msg1, msg2, msg3], "混合场景测试失败"
    print("✓ 混合场景测试通过\n")

def test_incomplete_messages():
    """测试不完整消息处理"""
    print("=" * 50)
    print("测试5: 不完整消息处理")
    print("=" * 50)
    
    message = "This is a test message"
    encoded = encode_message(message)
    
    # 只接收前10个字节
    partial = encoded[:10]
    msg_out, consumed = decode_message(partial)
    assert consumed == -1, "应该返回-1表示消息不完整"
    print(f"✓ 部分数据返回-1（不完整）")
    
    # 接收完整消息
    complete = partial + encoded[10:]
    msg_out, consumed = decode_message(complete)
    assert msg_out == message, "完整消息解析失败"
    assert consumed == len(complete), "消费字节数不正确"
    print(f"✓ 完整数据成功解析: {msg_out}\n")

if __name__ == "__main__":
    try:
        test_basic_encoding()
        test_sticky_packets()
        test_fragmented_packets()
        test_multiple_mixed()
        test_incomplete_messages()
        
        print("=" * 50)
        print("所有测试通过！✓")
        print("=" * 50)
    except AssertionError as e:
        print(f"\n✗ 测试失败: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ 发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
