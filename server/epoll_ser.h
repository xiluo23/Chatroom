#include<stdio.h>
#include<iostream>
#include<vector>
#include<string.h>
#include<sys/socket.h>
#include<sys/epoll.h>
#include<netinet/in.h>
#include<errno.h>
#include<arpa/inet.h>
#include<fcntl.h>
#include<unistd.h>
#include<errno.h>
#include<unordered_set>
#include<unordered_map>
#include<pthread.h>
#include"MyDb.h"
#include<queue>
#include<vector>
#include<crypt.h>
#include<sys/eventfd.h>

#define BUF_SIZE 1024
#define CLINT_SIZE 1000
#define MAX_EVENTS 1024
#define PORT 3306
#define HOST "192.168.147.130"
#define USER "ftpuser"
#define DB_NAME "Chatroom"
#define PWD "926472"

struct Task{
    int fd;//clinent_fd
    string message;
};

struct Response{
    int fd;
    string out;
    bool close_after;
};

int server_init();//服务器初始化
int set_unblocking(int fd);//为ET触发，设置非阻塞式i/o
void handle_new_connect();//与客户端建立连接
void handle_clint_data(int epoll_fd,int clint_fd);//接受并处理客户端数据
void close_clint(int epoll_fd,int clint_fd);
void process_clint_data(Task&task);
bool send_message(int clint_fd,const char buf[],int len);
void handle_response();
void signal_event_fd();
void en_resp(char*msg,int clint_fd);
