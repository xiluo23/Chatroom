#include "MyDb.h"
#include"epoll_ser.h"
using namespace std;

class ThreadPool{
private:
    queue<Task>tasks;
    pthread_mutex_t mutex;
    pthread_cond_t cond;
    vector<pthread_t>workers;
    queue<MyDb*>db_pool;
    bool stop;
    static void* worker(void*arg);
public:
    ThreadPool(int thread_num);
    ~ThreadPool();
    void addTask(Task task);
    MyDb* get_conn();
    void en_conn(MyDb* conn);
};
MyDb* ThreadPool::get_conn(){
    MyDb* conn=db_pool.front();
    db_pool.pop();
    return conn;
}
void ThreadPool::en_conn(MyDb*conn){
    db_pool.push(conn);
}

ThreadPool::ThreadPool(int thread_num){
    stop=false;
    pthread_mutex_init(&mutex,NULL);
    pthread_cond_init(&cond,NULL);
    pthread_t t_id;
    for(int i=0;i<thread_num;i++){
        MyDb* conn=new MyDb();
        conn->initDB(HOST,USER,PWD,DB_NAME,3306);
        db_pool.push(conn);        
        pthread_create(&t_id,NULL,worker,this);//this:ThreadPool*的一个对象
        workers.push_back(t_id);
    }
}
void* ThreadPool::worker(void*arg){
    ThreadPool*pool=(ThreadPool*)arg;
    while(1){
        Task task;
        pthread_mutex_lock(&pool->mutex);
        while(!pool->stop&&pool->tasks.empty()){
            pthread_cond_wait(&pool->cond,&pool->mutex);
        }
        if(pool->stop&&pool->tasks.empty()){
            pthread_mutex_unlock(&pool->mutex);
            break;
        }
        task=pool->tasks.front();
        pool->tasks.pop();
        pthread_mutex_unlock(&pool->mutex);
        process_clint_data(task);
    }
    return NULL;
}
void ThreadPool::addTask(Task task){
    pthread_mutex_lock(&mutex);
    tasks.push(task);
    pthread_mutex_unlock(&mutex);
    pthread_cond_signal(&cond);
}

ThreadPool::~ThreadPool(){
    pthread_mutex_lock(&mutex);//保证线程可读到最新的stop
    stop=true;
    pthread_mutex_unlock(&mutex);
    pthread_cond_broadcast(&cond);//唤醒所有线程，结束了
    for(auto&t_id:workers){
        pthread_join(t_id,NULL);
    }
    pthread_mutex_destroy(&mutex);
    pthread_cond_destroy(&cond);
}

