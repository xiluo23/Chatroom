#include"ThreadPool.h"
using namespace std;

unordered_map<string,int>clint_nametofd;
unordered_map<int,string>clint_fdtoname;
pthread_mutex_t resp_mutex;
ThreadPool pool(15);
int ser_fd,epoll_fd;
int event_fd=eventfd(0,EFD_NONBLOCK);
queue<Response>resp_queue;

bool send_message(int clint_fd,const char buf[],int len){
    int total = 0;
    while (total < len) {
        int n = send(clint_fd, buf + total, len - total, 0);
        if (n > 0) {
            total += n;
        } 
        else if (n == -1 && (errno == EAGAIN || errno == EWOULDBLOCK)) {
            continue; 
        } 
        else {
            return false;
        }
    }
    return true;
}
string generate_str(){//生成salt，使用MD5
    string str="";
    int i,flag;
    for(i=0;i<8;i++){
        flag=rand()%3;
        switch (flag){
            case 0:
                str+=rand()%26+'a';
                break;
            case 1:
                str+=rand()%26+'A';
                break;
            case 2:
                str+=rand()%10+'0';
                break;
        }
    }
    return str;
}
int server_init(){
    struct sockaddr_in ser_addr;
    if((ser_fd=socket(PF_INET,SOCK_STREAM,0))==-1){
        perror("Error: ");
        exit(0);
    }
    memset(&ser_addr,0,sizeof(ser_addr));
    ser_addr.sin_family=AF_INET;
    ser_addr.sin_port=htons(8080);
    ser_addr.sin_addr.s_addr=htonl(INADDR_ANY);
    int opt=1;
    if(setsockopt(ser_fd,SOL_SOCKET,SO_REUSEADDR,&opt,sizeof(opt))==-1){
        perror("Error:");
        close(ser_fd);
        exit(0);
    }
    if(bind(ser_fd,(struct sockaddr*)&ser_addr,sizeof(ser_addr))==-1){
        perror("Error:");
        close(ser_fd);
        exit(0);
    }
    if(listen(ser_fd,100)==-1){
        perror("Error:");
        close(ser_fd);
        exit(0);
    }
    puts("server is running");
    return ser_fd;
}

int set_unblocking(int fd){
    int flag=fcntl(fd,F_GETFL);
    if(flag==-1){
        perror("set_unblocking:");
        return 0;
    }
    if(fcntl(fd,F_SETFL,flag|O_NONBLOCK)==-1){
        perror("set_unblocking:");
        return 0;
    }
    return 1;
}
void handle_new_connect(){
    socklen_t clint_size;
    int clint_fd;
    struct sockaddr_in clint_addr;
    struct epoll_event event;
    clint_size=sizeof(clint_addr);
    event.events=EPOLLIN|EPOLLET|EPOLLRDHUP;
    // printf("handle_new_connect\n");
    while(1){
        clint_size=sizeof(clint_addr);
        clint_fd=accept(ser_fd,(struct sockaddr*)&clint_addr,&clint_size);
        if(clint_fd==-1){
            if(errno==EAGAIN||errno==EWOULDBLOCK){
                break;
            }
            else{
                perror("Accept Error:");
                break;
            }
        }
        if(set_unblocking(clint_fd)==0){
            close(clint_fd);
            continue;
        }
        event.data.fd=clint_fd;
        event.events=EPOLLIN|EPOLLRDHUP;
        if(epoll_ctl(epoll_fd,EPOLL_CTL_ADD,clint_fd,&event)==-1){
            perror("epoll_ctl:");
            close(clint_fd);
            break;
        }
        printf("新的客户端连接,socket_fd:%d\n",clint_fd);
    }
}
void close_clint(int epoll_fd,int clint_fd){
    epoll_ctl(epoll_fd,EPOLL_CTL_DEL,clint_fd,NULL);
    close(clint_fd);
    clint_nametofd.erase(clint_fdtoname[clint_fd]);
    clint_fdtoname.erase(clint_fd);
}
void handle_clint_data(int epoll_fd,int clint_fd){
    int bytes_read;
    int str_len=0;
    char buf[BUF_SIZE];
    while(1){
        bytes_read=recv(clint_fd,buf+str_len,BUF_SIZE-str_len-1,0);
        if(bytes_read==-1){
            if(errno==EAGAIN||errno==EWOULDBLOCK){//无数据可读
                break ;
            }
            else{
                close_clint(epoll_fd,clint_fd);
                return ;
            }
        }
        else if(bytes_read==0){
            printf("客户端%d断开连接\n",clint_fd);
            close_clint(epoll_fd,clint_fd);
            return ;
        }
        else{
            str_len+=bytes_read;
        }
    }
    //数据接受完毕
    buf[str_len]=0;
    Task task;
    task.fd=clint_fd;
    task.message=string(buf);
    pool.addTask(task);
}
void signal_event_fd(){
    uint64_t one=1;
    write(event_fd,&one,sizeof(one));
}
void en_resp(char msg[],int clint_fd){
    Response resp;
    resp.fd=clint_fd;
    resp.out=string(msg);
    resp.close_after=false;
    pthread_mutex_lock(&resp_mutex);
    resp_queue.push(resp);
    pthread_mutex_unlock(&resp_mutex);
    signal_event_fd();
}
void process_clint_data(Task&task){
    MyDb* conn=pool.get_conn();
    char buf[BUF_SIZE];
    size_t len = min(task.message.size(), (size_t)BUF_SIZE - 1);
    memcpy(buf, task.message.data(), len);
    buf[len] = '\0';
    // puts(buf);
    int clint_fd=task.fd;
    char*saveptr=NULL;
    char*cmd=strtok_r(buf,"|",&saveptr);
    // puts(cmd);
    if(!cmd){
        pool.en_conn(conn);
        return;
    }
    if(strcmp(cmd,"sign_up")==0){
        char*username=strtok_r(NULL,"|",&saveptr);
        char*password=strtok_r(NULL,"|",&saveptr);
        if (!username || !password) {
            char msg[] = "sign_up|0|请重试";
            en_resp(msg,clint_fd);
            pool.en_conn(conn);
            return;
        }           
        string sql="select user_id from user where user_name='"+string(username)+"'";
        string ret="";
        bool res=conn->select_one_SQL(sql,ret);
        // puts("1");
        if(!res){//无相同的name
            string p = generate_str();
            string salt="$1$"+p+"$";
            string new_password = crypt(password, salt.c_str());
            string sql = "insert into user (user_name, password, salt) values ('" + string(username) + "', '" + new_password + "', '" + p + "')";
            res=conn->exeSQL(sql);
            if(res){
                //查询该用户的user_id
                int user_id=conn->get_id(username);
                printf("user_id:%d\n",user_id);
                if(user_id==-1){
                    char msg[]="sign_up|0|请重试";
                    en_resp(msg,clint_fd);
                    pool.en_conn(conn);
                    return;
                }
                sql="insert into user_status (user_id) values ("+to_string(user_id)+")";//新用户信息插入user_status
                if(!conn->exeSQL(sql)){
                    char msg[]="sign_up|0|请重试";
                    en_resp(msg,clint_fd);
                    pool.en_conn(conn);
                    return;
                }
                char msg[]="sign_up|1|请登录";
                en_resp(msg,clint_fd);
            }
            else{
                char msg[]="sign_up|0|请重试";
                en_resp(msg,clint_fd);
            }
        }
        else{//name重复
            char msg[]="sign_up|0|用户名重复";
            en_resp(msg,clint_fd);
        }
    }
    else if(strcmp(cmd,"sign_in")==0){
        char*username=strtok_r(NULL,"|",&saveptr);
        char*password=strtok_r(NULL,"|",&saveptr);
        if (!username || !password) {
            char msg[] = "sign_in|0|请重试";//eg:sign_in|1|ok
            en_resp(msg,clint_fd);
            pool.en_conn(conn);
            return;
        }           
        string sql="select user_name,password,salt from user where user_name='"+string(username)+"'";
        string ret="";
        bool res=conn->select_one_SQL(sql,ret);
        if(!res){
            char msg[]="sign_in|0|无此用户";
            en_resp(msg,clint_fd);
        }
        else{
            //对查询结果进行解析
            char *str=new char[ret.size()+1];
            strcpy(str,ret.c_str());
            char*db_name=strtok(str,"|");
            char*db_password=strtok(NULL,"|");
            char*db_salt=strtok(NULL,"|");
            string salt="$1$"+string(db_salt)+"$";
            if(strcmp(db_password,crypt(password,salt.c_str()))==0){
                //更新status表
                int id=conn->get_id(db_name);
                // printf("userid:%d\n",id);
                sql="update user_status set is_online=1 , last_active = NOW() where user_id = "+to_string(id)+" and is_online=0";
                if(!conn->exeSQL(sql)){
                    char msg[] = "sign_in|0|请重试";
                    en_resp(msg,clint_fd);
                }
                else{
                    clint_fdtoname[clint_fd]=string(username);
                    clint_nametofd[string(username)]=clint_fd;
                    char msg[]="sign_in|1|ok";
                    en_resp(msg,clint_fd);
                    //查询是否有未读信息
                    string ret="";
                    string sql="select su.user_name,c.send_time,c.content from chat_log c join user ru on c.receiver_id=ru.user_id join user su on c.sender_id=su.user_id where ru.user_name='"+string(username)+"' and c.is_delivered=0 order by c.send_time";
                    conn->select_many_SQL(sql,ret);
                    if(ret.empty()){
                        return ;
                    }
                    char resp[BUF_SIZE];
                    snprintf(resp,BUF_SIZE-1,"chat_unread|1|%s",ret.c_str());
                    resp[strlen(resp)]=0;
                    en_resp(resp,clint_fd);
                    int receiver_id=conn->get_id(username);
                    sql="update chat_log set is_delivered=1 where is_delivered=0 and receiver_id="+to_string(receiver_id);
                    puts(sql.c_str());
                    conn->exeSQL(sql);
                    // printf("查询未读信息:%s\n",resp);
                    // puts(resp);
                }
            }
            else{//密码错误
                char msg[]="sign_in|0|密码错误";
                en_resp(msg,clint_fd);
            }
            delete[]str;
        }
    }
    else if(strcmp(cmd,"show_online_user")==0){
        string sql="select user_name from user join user_status on user.user_id = user_status.user_id where is_online = 1";
        string ret="";
        if(conn->select_many_SQL(sql,ret)){
            char msg[BUF_SIZE];
            snprintf(msg,BUF_SIZE-1,"show_online_user|1|%s",ret.c_str());
            msg[strlen(msg)]=0;
            en_resp((char*)msg,clint_fd);
        }
        else{
            char msg[]="show_online_user|0|请重试";
            en_resp(msg,clint_fd);
        }
    }
    else if(strcmp(cmd,"single_chat")==0){
        const char*from=clint_fdtoname[clint_fd].c_str();
        const char*to=strtok_r(NULL,"|",&saveptr);
        const char*text=strtok_r(NULL,"|",&saveptr);
        string receiver_id=to_string(conn->get_id(to));
        if(receiver_id=="-1"){//发送给的用户不存在
            char msg[BUF_SIZE];
            snprintf(msg,BUF_SIZE-1,"single_chat|0|%s","用户不存在");
            msg[strlen(msg)]=0;
            en_resp(msg,clint_fd);
            return ;
        }
        string sender_id=to_string(conn->get_id(from));
        string is_delivered="1";
        string group_type="single";
        if(!clint_nametofd.count(to)){//接收用户不在线，不发送
            is_delivered="0";
        }
        else{
            int to_fd=clint_nametofd[to];
            char msg[BUF_SIZE];
            snprintf(msg,BUF_SIZE-1,"single_chat|1|%s;%s",from,text);
            msg[strlen(msg)]=0;
            en_resp(msg,to_fd);
        }
        char msg_resp[BUF_SIZE];
        snprintf(msg_resp,BUF_SIZE-1,"single_chat|2|发送成功");
        msg_resp[strlen(msg_resp)]=0;
        en_resp(msg_resp, clint_fd);
        string sql="insert into chat_log (sender_id,receiver_id,is_delivered,group_type,content) values("+sender_id+","+receiver_id+","+is_delivered+",'"+group_type+"','"+text+"')";
        conn->exeSQL(sql);
        //更新status
        sql="update user_status set last_active = NOW() where user_id = "+sender_id;
        conn->exeSQL(sql);        
    }
    else if(strcmp(cmd,"multi_chat")==0){
        char*usernames=strtok_r(NULL,"|",&saveptr);
        const char*text=strtok_r(NULL,"|",&saveptr);
        const char*from=clint_fdtoname[clint_fd].c_str();
        // printf("usernames:%s,text:%s\n",usernames,text);
        if(!text||!usernames){
            char msg[BUF_SIZE];
            snprintf(msg,BUF_SIZE-1,"mulit_chat|0|error");
            return ;
        }
        string sender_id=to_string(conn->get_id(from));
        char* to=strtok_r(usernames," ",&saveptr);
        while(to){
            string receiver_id=to_string(conn->get_id(to));
            if(receiver_id=="-1"){//发送给的用户不存在
                continue;
            }
            string is_delivered="1";
            string group_type="multi";
            if(!clint_nametofd.count(to)){//接收用户不在线，不发送
                is_delivered="0";
            }
            else{
                printf("to:%s\n",to);
                int to_fd=clint_nametofd[to];
                char msg[BUF_SIZE];
                snprintf(msg,BUF_SIZE-1,"multi_chat|2|%s;%s",from,text);
                msg[strlen(msg)]=0;
                en_resp(msg,to_fd);
            }
            string sql="insert into chat_log (sender_id,receiver_id,is_delivered,group_type,content) values("+sender_id+","+receiver_id+","+is_delivered+",'"+group_type+"','"+text+"')";
            conn->exeSQL(sql);    
            to=strtok_r(NULL," ",&saveptr);
        }
        //更新status
        string sql="update user_status set last_active = NOW() where user_id = "+sender_id;
        conn->exeSQL(sql); 
        char msg_resp[BUF_SIZE];
        snprintf(msg_resp,BUF_SIZE-1,"multi_chat|1|发送成功");
        msg_resp[strlen(msg_resp)]=0;
        en_resp(msg_resp,clint_fd);
    }
    else if(strcmp(cmd,"broadcast_chat")==0){
        const char*text=strtok_r(NULL,"|",&saveptr);
        const char*from=clint_fdtoname[clint_fd].c_str();
        if(!text){
            char msg[BUF_SIZE];
            snprintf(msg,BUF_SIZE-1,"mulit_chat|0|error");
            return ;
        }
        string sender_id=to_string(conn->get_id(from));
        
        for(auto&it:clint_nametofd){
            string to=it.first;
            int to_fd=it.second;
            if(to==from)continue;
            string receiver_id=to_string(conn->get_id(to.c_str()));
            if(receiver_id=="-1"){//发送给的用户不存在
                continue;
            }
            string is_delivered="1";
            string group_type="broadcast";
            if(!clint_nametofd.count(to)){//接收用户不在线，不发送
                is_delivered="0";
            }
            else{
                // printf("to:%s\n",to);
                char msg[BUF_SIZE];
                snprintf(msg,BUF_SIZE-1,"broadcast_chat|2|%s;%s",from,text);
                msg[strlen(msg)]=0;
                en_resp(msg,to_fd);
            }
            string sql="insert into chat_log (sender_id,receiver_id,is_delivered,group_type,content) values("+sender_id+","+receiver_id+","+is_delivered+",'"+group_type+"','"+text+"')";
            conn->exeSQL(sql);    
        }
        //更新status
        string sql="update user_status set last_active = NOW() where user_id = "+sender_id;
        conn->exeSQL(sql); 
        char msg_resp[BUF_SIZE];
        snprintf(msg_resp,BUF_SIZE-1,"broadcast_chat|1|发送成功");
        msg_resp[strlen(msg_resp)]=0;
        en_resp(msg_resp,clint_fd);
    }
    else if(strcmp(cmd,"show_history")==0){
        string username=clint_fdtoname[clint_fd];
        string sql="select ru.user_name as sender,u.user_name as receiver,send_time,group_type,content from chat_log c join user u on c.receiver_id=u.user_id join user ru on ru.user_id = c.sender_id where u.user_name='"+username+"'";
        string ret="";
        conn->select_many_SQL(sql,ret);
        char msg[BUF_SIZE];
        snprintf(msg,BUF_SIZE-1,"show_history|1|%s",ret.c_str());
        en_resp(msg,clint_fd);
    }
    else if(strcmp(cmd,"q\n")==0||strcmp(cmd,"Q\n")==0){
        //更新status
        int id=conn->get_id(clint_fdtoname[clint_fd].c_str());
        printf("user_id:%d\n",id);
        string sql="update user_status set is_online = 0 where user_id ="+to_string(id);
        conn->exeSQL(sql);
        char msg[]="bye\n";
        en_resp(msg,clint_fd);
    }
    pool.en_conn(conn);
}
void handle_response(){
    uint64_t tmp;
    read(event_fd,&tmp,sizeof(tmp));
    while(1){
        pthread_mutex_lock(&resp_mutex);
        if(resp_queue.empty()){
            pthread_mutex_unlock(&resp_mutex);
            break;
        }
        Response resp=resp_queue.front();
        resp_queue.pop();
        pthread_mutex_unlock(&resp_mutex);
        send(resp.fd,resp.out.c_str(),resp.out.size(),0);
        if(resp.close_after){
            close_clint(epoll_fd,resp.fd);
        }
    }
}

int main(int argc,char*argv[]){
    pthread_mutex_init(&resp_mutex,NULL);
    srand(time(NULL));
    ser_fd=server_init();
    if(set_unblocking(ser_fd)==0){
        close(ser_fd);
        exit(0);
    }
    struct epoll_event event,events[MAX_EVENTS];
    epoll_fd=epoll_create(1);
    if(epoll_fd==-1){
        perror("Error:");
        exit(0);
    }
    event.events=EPOLLIN|EPOLLET|EPOLLRDHUP;
    event.data.fd=ser_fd;
    if(epoll_ctl(epoll_fd,EPOLL_CTL_ADD,ser_fd,&event)==-1){
        perror("Error:");
        close(epoll_fd);
        close(ser_fd);
        close(event_fd);
        exit(0);
    }
    event.events=EPOLLIN;
    event.data.fd=event_fd;
    if(epoll_ctl(epoll_fd,EPOLL_CTL_ADD,event_fd,&event)==-1){
        perror("Error:");
        close(epoll_fd);
        close(ser_fd);
        close(event_fd);
        exit(0);
    }
    puts("epoll服务器启动成功,等待连接...");
    int i;
    while(1){
        int num_fd=epoll_wait(epoll_fd,events,MAX_EVENTS,-1);
        if(num_fd==-1){
            perror("Error:");
            break;
        }
        for(i=0;i<num_fd;i++){
            int fd=events[i].data.fd;
            uint32_t ev=events[i].events;
            if(fd==ser_fd){//有新客户端连接
                handle_new_connect();
            }
            else if(fd==event_fd){
                handle_response();
            }
            else{
                if(ev&EPOLLIN){//客户端有消息发送
                    handle_clint_data(epoll_fd,fd);
                }
                if(ev&(EPOLLERR|EPOLLHUP|EPOLLRDHUP)){//客户端断开连接
                    close_clint(epoll_fd,fd);
                }
            }
        }
    }
    close(ser_fd);
    close(epoll_fd);
    return 0;
}