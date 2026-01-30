/**
 * @file example_logger_usage.cpp
 * @brief 日志系统使用示例 - 展示如何在实际代码中使用日志系统
 * 
 * 这个文件展示了在不同场景下如何使用日志系统
 */

#include "Logger.h"
#include "ErrorCode.h"
#include <string>

using namespace std;

/**
 * @section 示例1: 基础日志记录
 */
void example_basic_logging() {
    // 初始化日志系统
    Logger* logger = Logger::getInstance();
    logger->initialize("logs", "example.log", LogLevel::DEBUG, true);

    // 记录各个级别的日志
    LOG_TRACE("这是一条跟踪消息");
    LOG_DEBUG("这是一条调试消息");
    LOG_INFO("这是一条普通信息");
    LOG_WARN("这是一条警告消息");
    LOG_ERROR("这是一条错误消息", ERR_DB_QUERY_FAIL);
    LOG_FATAL("这是一条致命错误", ERR_INIT_FAIL);

    Logger::destroy();
}

/**
 * @section 示例2: Socket错误日志
 */
void example_socket_error_logging() {
    int socket_fd = 5;

    // Socket创建失败
    LOG_ERROR("Failed to create socket", ERR_SOCKET_CREATE_FAIL);

    // Socket绑定失败
    LOG_ERROR("Failed to bind socket to port 8080", ERR_SOCKET_BIND_FAIL);

    // Socket发送失败
    LOG_NET_ERROR(socket_fd, "Failed to send data to client", ERR_SOCKET_SEND_FAIL);

    // Socket接收失败
    LOG_NET_ERROR(socket_fd, "Failed to receive data from client", ERR_SOCKET_RECV_FAIL);

    // 连接已关闭
    LOG_INFO("Connection closed: FD=" + to_string(socket_fd));
}

/**
 * @section 示例3: 数据库错误日志
 */
void example_database_error_logging() {
    // 数据库连接失败
    LOG_ERROR("Cannot connect to database: Host unavailable", ERR_DB_CONNECTION_FAIL);

    // 数据库查询失败
    string sql = "SELECT * FROM user WHERE user_id=1";
    string error_msg = "Column 'user_id' doesn't exist";
    LOG_DB_ERROR(sql, error_msg, ERR_DB_QUERY_FAIL);

    // 数据库执行失败（INSERT/UPDATE/DELETE）
    sql = "UPDATE user SET password='123' WHERE user_id=1";
    error_msg = "Access denied for user";
    LOG_DB_ERROR(sql, error_msg, ERR_DB_EXECUTE_FAIL);

    // 数据库连接断开
    LOG_ERROR("Database connection lost", ERR_DB_DISCONNECT);
}

/**
 * @section 示例4: 用户认证错误日志
 */
void example_authentication_error_logging() {
    int user_id = 1;
    string username = "admin";

    // 用户不存在
    LOG_ERROR("User not found: " + username, ERR_USER_NOT_FOUND);

    // 密码错误
    LOG_OPERATION(user_id, "login_attempt", "Failed - incorrect password");
    LOG_ERROR("Password verification failed for user: " + username, ERR_PASSWORD_INCORRECT);

    // 用户已存在
    LOG_ERROR("User already exists: " + username, ERR_USER_ALREADY_EXISTS);

    // 用户未登录
    LOG_ERROR("User is not logged in, cannot perform operation", ERR_USER_NOT_LOGIN);

    // 用户会话已过期
    LOG_ERROR("User session expired for user_id=" + to_string(user_id), ERR_USER_SESSION_EXPIRED);

    // 密码强度不够
    LOG_ERROR("Password is too weak, minimum 8 characters required", ERR_PASSWORD_WEAK);
}

/**
 * @section 示例5: 消息处理错误日志
 */
void example_message_error_logging() {
    int client_fd = 10;

    // 消息格式无效
    string received_msg = "invalid@format@message";
    LOG_ERROR("Invalid message format received from FD=" + to_string(client_fd) + 
             ": " + received_msg, ERR_MSG_INVALID_FORMAT);

    // 消息解析失败
    LOG_ERROR("Failed to parse message from client", ERR_MSG_PARSE_FAIL);

    // 消息发送失败
    LOG_NET_ERROR(client_fd, "Failed to send message", ERR_MSG_SEND_FAIL);

    // 消息接收失败
    LOG_NET_ERROR(client_fd, "Failed to receive message", ERR_MSG_RECEIVE_FAIL);

    // 消息过大
    LOG_ERROR("Message too large: 50MB > 10MB limit", ERR_MSG_TOO_LARGE);

    // 消息为空
    LOG_ERROR("Empty message received from client", ERR_MSG_EMPTY);

    // 无效的命令
    LOG_ERROR("Invalid command: UNKNOWN_CMD", ERR_MSG_INVALID_COMMAND);
}

/**
 * @section 示例6: 业务逻辑错误日志
 */
void example_business_logic_error_logging() {
    int sender_id = 1;
    int recipient_id = 999;

    // 接收者不存在
    LOG_ERROR("Cannot send message: recipient does not exist (user_id=" + 
             to_string(recipient_id) + ")", ERR_RECIPIENT_NOT_FOUND);

    // 接收者离线
    LOG_WARN("Recipient is offline (user_id=" + to_string(recipient_id) + 
            "), message will be saved for later delivery");

    // 群组不存在
    int group_id = 888;
    LOG_ERROR("Group not found: group_id=" + to_string(group_id), ERR_GROUP_NOT_FOUND);

    // 用户不在群组中
    LOG_ERROR("User not in group: user_id=" + to_string(sender_id) + 
             ", group_id=" + to_string(group_id), ERR_USER_NOT_IN_GROUP);

    // 权限不足
    LOG_ERROR("Permission denied: user_id=" + to_string(sender_id) + 
             " cannot access this resource", ERR_PERMISSION_DENIED);

    // 操作不被允许
    LOG_WARN("Operation not allowed: cannot delete admin user", ERR_OPERATION_NOT_ALLOWED);

    // 重复操作
    LOG_WARN("Duplicate operation detected: user already in group", ERR_DUPLICATE_OPERATION);

    // 资源耗尽
    LOG_ERROR("Resource exhausted: maximum connections reached", ERR_RESOURCE_EXHAUSTED);
}

/**
 * @section 示例7: 线程和并发错误日志
 */
void example_concurrency_error_logging() {
    // 线程池已满
    LOG_ERROR("Thread pool is full, cannot accept new tasks", ERR_THREAD_POOL_FULL);

    // 线程创建失败
    LOG_ERROR("Failed to create new worker thread", ERR_THREAD_CREATE_FAIL);

    // 互斥锁锁定失败
    LOG_ERROR("Failed to acquire mutex lock", ERR_MUTEX_LOCK_FAIL);

    // 死锁检测
    LOG_FATAL("Deadlock detected between threads", ERR_DEADLOCK_DETECTED);

    // 竞态条件检测
    LOG_WARN("Race condition detected in shared resource access", ERR_RACE_CONDITION);
}

/**
 * @section 示例8: 文件系统错误日志
 */
void example_filesystem_error_logging() {
    // 文件打开失败
    LOG_ERROR("Failed to open file: /tmp/config.ini", ERR_FILE_OPEN_FAIL);

    // 文件读取失败
    LOG_ERROR("Failed to read from file: /data/user_data.db", ERR_FILE_READ_FAIL);

    // 文件写入失败
    LOG_ERROR("Failed to write to file: /var/log/app.log", ERR_FILE_WRITE_FAIL);

    // 文件不存在
    LOG_ERROR("File not found: /etc/chatroom.conf", ERR_FILE_NOT_FOUND);

    // 文件权限拒绝
    LOG_ERROR("Permission denied: cannot write to /root/config.ini", ERR_FILE_PERMISSION_DENIED);

    // 磁盘空间满
    LOG_FATAL("Disk space full: cannot write to /var/log", ERR_DISK_SPACE_FULL);
}

/**
 * @section 示例9: 内存管理错误日志
 */
void example_memory_error_logging() {
    // 内存分配失败
    LOG_ERROR("Failed to allocate 1GB of memory", ERR_MEMORY_ALLOC_FAIL);

    // 内存泄漏检测
    LOG_WARN("Potential memory leak detected in module: ChatHandler", ERR_MEMORY_LEAK);

    // 空指针错误
    LOG_ERROR("Null pointer dereference in function: process_message()", ERR_NULL_POINTER);

    // 缓冲区溢出
    LOG_FATAL("Buffer overflow detected: copying 1000 bytes into 512-byte buffer", 
             ERR_BUFFER_OVERFLOW);
}

/**
 * @section 示例10: 操作审计日志
 */
void example_operation_audit_logging() {
    int admin_id = 1;

    // 用户登录
    LOG_OPERATION(admin_id, "login", "IP: 192.168.1.100");

    // 用户注册
    LOG_OPERATION(2, "register", "New user registration");

    // 创建群组
    LOG_OPERATION(admin_id, "create_group", "Group name: Developer Team, members: 5");

    // 修改用户信息
    LOG_OPERATION(admin_id, "update_profile", "Changed nickname to 'New Nickname'");

    // 发送消息
    LOG_OPERATION(admin_id, "send_message", "Recipient: user_id=2");

    // 删除消息
    LOG_OPERATION(admin_id, "delete_message", "Message ID: 12345");

    // 用户登出
    LOG_OPERATION(admin_id, "logout", "Session duration: 30 minutes");

    // 管理员操作
    LOG_OPERATION(admin_id, "admin_action", "Banned user: user_id=999");
}

/**
 * @section 示例11: 使用错误码查询
 */
void example_error_code_query() {
    // 获取错误码的描述
    string desc = ErrorCodeManager::getDescription(ERR_DB_QUERY_FAIL);
    cout << "Error description: " << desc << endl;

    // 获取错误码的分类
    string category = ErrorCodeManager::getCategory(ERR_DB_QUERY_FAIL);
    cout << "Error category: " << category << endl;

    // 获取完整的错误消息
    string full_msg = ErrorCodeManager::getFullMessage(ERR_DB_QUERY_FAIL);
    cout << "Full message: " << full_msg << endl;
    // 输出: [DATABASE] (2002) 数据库查询失败
}

/**
 * @section 示例12: 条件日志记录
 */
void example_conditional_logging() {
    bool debug_mode = true;
    int response_time = 5000;  // 毫秒

    // 仅在调试模式下记录
    if (debug_mode) {
        LOG_DEBUG("Detailed debug information");
    }

    // 在响应时间超过阈值时记录警告
    if (response_time > 1000) {
        LOG_WARN("Slow response detected: " + to_string(response_time) + "ms > 1000ms threshold");
    }

    // 记录性能指标
    LOG_INFO("Request processed in " + to_string(response_time) + "ms");
}

/**
 * @section 示例13: 实际场景 - Socket服务器
 */
void example_socket_server_scenario() {
    LOG_INFO("Server starting...");

    // 初始化
    if (false) {  // 模拟初始化失败
        LOG_FATAL("Failed to initialize server", ERR_INIT_FAIL);
        return;
    }

    LOG_INFO("Server listening on port 8080");

    // 接受连接
    int client_fd = 5;
    LOG_INFO("New client connected: FD=" + to_string(client_fd));

    // 接收消息
    string received_data = "user@password";
    LOG_DEBUG("Received data from FD=" + to_string(client_fd) + ": " + received_data);

    // 处理消息
    if (received_data.find('@') == string::npos) {
        LOG_ERROR("Invalid login format", ERR_MSG_INVALID_FORMAT);
        return;
    }

    // 数据库查询
    LOG_DEBUG("Querying database for user");
    if (false) {  // 模拟数据库查询失败
        LOG_ERROR("Database query failed", ERR_DB_QUERY_FAIL);
        return;
    }

    LOG_INFO("User authentication successful");

    // 发送响应
    if (false) {  // 模拟发送失败
        LOG_ERROR("Failed to send response", ERR_SOCKET_SEND_FAIL);
        return;
    }

    LOG_DEBUG("Response sent to FD=" + to_string(client_fd));

    // 关闭连接
    LOG_INFO("Connection closed: FD=" + to_string(client_fd));
}

/**
 * @section 示例14: 实际场景 - 数据库操作
 */
void example_database_operation_scenario() {
    LOG_INFO("Database operation started");

    // 连接数据库
    if (false) {  // 模拟连接失败
        LOG_ERROR("Failed to connect to database", ERR_DB_CONNECTION_FAIL);
        return;
    }

    LOG_INFO("Database connected");

    // 执行查询
    string sql = "SELECT * FROM user WHERE user_id=1";
    LOG_DEBUG("Executing query: " + sql);

    if (false) {  // 模拟查询失败
        LOG_ERROR("Query failed: syntax error", ERR_DB_QUERY_FAIL);
        return;
    }

    LOG_DEBUG("Query successful, processing results");

    // 处理结果
    int result_count = 1;
    LOG_INFO("Query returned " + to_string(result_count) + " rows");

    // 执行更新
    sql = "UPDATE user SET last_login=NOW() WHERE user_id=1";
    LOG_DEBUG("Executing update: " + sql);

    if (false) {  // 模拟更新失败
        LOG_ERROR("Update failed", ERR_DB_EXECUTE_FAIL);
        return;
    }

    LOG_INFO("Update successful, 1 row affected");
}

// 主函数 - 展示如何调用这些示例
int main_example_usage() {
    // 初始化日志系统
    Logger* logger = Logger::getInstance();
    logger->initialize("logs", "examples.log", LogLevel::TRACE, true);

    cout << "=== 日志系统使用示例 ===" << endl;
    cout << "日志已写入 logs/examples.log" << endl;
    cout << endl;

    // 运行示例
    cout << "示例1: 基础日志记录" << endl;
    example_basic_logging();

    cout << "\n示例2: Socket错误日志" << endl;
    example_socket_error_logging();

    cout << "\n示例3: 数据库错误日志" << endl;
    example_database_error_logging();

    cout << "\n示例4: 用户认证错误日志" << endl;
    example_authentication_error_logging();

    // ... 其他示例

    Logger::destroy();
    return 0;
}

/**
 * 使用这个文件的方法：
 * 
 * 1. 复制相关的代码段到你的项目中
 * 2. 修改错误处理逻辑中的条件（if(false)改为实际的错误检查）
 * 3. 根据实际情况调整日志消息和错误码
 * 
 * 示例：
 * 
 *   if (mysql_query(mysql, sql.c_str())) {
 *       LOG_ERROR("Database query failed: " + string(mysql_error(mysql)), ERR_DB_QUERY_FAIL);
 *       return false;
 *   }
 */
