// gateway.js
const net = require('net');
const WebSocket = require('ws');

// 聊天服务器地址
const TCP_HOST = '127.0.0.1';
const TCP_PORT = 8080;

// WebSocket 服务监听端口（给浏览器连）
const WS_PORT = 9000;

const wss = new WebSocket.Server({ host: '0.0.0.0', port: WS_PORT }, () => {
  console.log(`WebSocket 网关已启动: ws://0.0.0.0:${WS_PORT}`);
  console.log(`Windows 主机请使用: ws://192.168.147.130:${WS_PORT}`);
});

wss.on('connection', (ws) => {
  console.log('前端 WebSocket 已连接');

  // 为每个 WebSocket 客户端创建一个 TCP 连接到 C++ 服务器
  const tcpSocket = net.createConnection({ host: TCP_HOST, port: TCP_PORT }, () => {
    console.log('已连接到 C++ 聊天服务器');
  });

  tcpSocket.on('data', (data) => {
    // 将 C++ 服务器发来的数据原样转发给浏览器
    ws.send(data.toString());
  });

  tcpSocket.on('error', (err) => {
    console.error('TCP 错误:', err.message);
    ws.close();
  });

  tcpSocket.on('close', () => {
    console.log('TCP 连接关闭');
    ws.close();
  });

  ws.on('message', (message) => {
    // 浏览器发来的字符串，转发给 C++ 服务器
    // 建议统一在前端不要带 \n，这里也不要额外加
    tcpSocket.write(message.toString());
  });

  ws.on('close', () => {
    console.log('WebSocket 关闭');
    tcpSocket.end();
  });

  ws.on('error', (err) => {
    console.error('WebSocket 错误:', err.message);
    tcpSocket.end();
  });
});