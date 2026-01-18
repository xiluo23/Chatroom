#pragma once
#include<string>
#include<mysql/mysql.h>
#include<iostream>
using namespace std;
typedef unsigned long long ull;

class MyDb{
private:
    MYSQL*mysql;
    MYSQL_RES*result;
    MYSQL_ROW row;
public:
    MyDb();
    ~MyDb();
    bool initDB(string host,string user,string pwd,string db_name,int port);
    bool exeSQL(string sql);
    bool select_one_SQL(string sql,string& str);
    bool select_many_SQL(string sql,string& str);
    int get_id(const char* name);
};
int MyDb::get_id(const char* name){
    string sql="select user_id from user where user_name='"+string(name)+"'";
    if(mysql_query(mysql,sql.c_str())){
        cout<<"Query Error:"<<mysql_error(mysql);
        return -1;
    }
    result=mysql_store_result(mysql);
    row=mysql_fetch_row(result);
    if(!row)return -1;
    return atoi(row[0]);
}


MyDb::MyDb(){
    mysql=mysql_init(NULL);
    if(mysql==NULL){
        cout<<"Error:"<<mysql_error(mysql);
        exit(0);
    }

}
MyDb::~MyDb(){
    if(result)mysql_free_result(result);
    if(mysql){
        mysql_close(mysql);
    }
}

bool MyDb::initDB(string host,string user,string pwd,string db_name,int port=3306){
    mysql=mysql_real_connect(mysql,host.c_str(),user.c_str(),pwd.c_str(),db_name.c_str(),port,NULL,0);
    if(!mysql){
        cout<<"InitDb: "<<mysql_error(mysql)<<'\n';
        return false;
    }
    return true;
}

bool MyDb::exeSQL(string sql){
    if(mysql_query(mysql,sql.c_str())){
        cout<<"Query Error:"<<mysql_error(mysql);
        return false;
    }
    result=mysql_store_result(mysql);
    //select
    if(result){
        int num_fields=mysql_num_fields(result);
        ull num_rows=mysql_num_rows(result);
        for(ull i=0;i<num_rows;i++){
            row=mysql_fetch_row(result);
            if(!row){
                break;
            }
            for(int j=0;j<num_fields;j++){
                cout<<row[j]<<"\t\t";
            }
            cout<<'\n';
        }
        mysql_free_result(result);
    }
    //update,insert,del
    else{
        cout<<"affect "<<mysql_affected_rows(mysql)<<" rows\n";
    }
    return true;
}

bool MyDb::select_one_SQL(string sql, string& str) {
    if (mysql_query(mysql, sql.c_str())) {
        cout << "Query Error: " << mysql_error(mysql) << '\n';
        return false;
    }

    result = mysql_store_result(mysql);
    if (!result) {
        cout << "Get Result Error: " << mysql_error(mysql) << '\n';
        return false;
    }
    row=mysql_fetch_row(result);
    if(!row||!row[0]){
        mysql_free_result(result);
        return false;  // 没查到数据
    }
    int num_fields=mysql_num_fields(result);
    for(int i=0;i<num_fields;i++){
        if(row[i]){
            str+=row[i];
            str+="|";
        }
        else
            break;
    }
    if(!str.empty())
        str.pop_back();
    mysql_free_result(result);
    return true;      // 查到一条
}


bool MyDb::select_many_SQL(string sql,string &str){
    if(mysql_query(mysql,sql.c_str())){
        cout<<"Query Error: "<<mysql_error(mysql)<<'\n';
        return false;
    }
    result=mysql_store_result(mysql);
    if(result){
        int num_fields=mysql_num_fields(result);
        ull num_rows=mysql_num_rows(result);
        for(ull i=0;i<num_rows;i++){
            row=mysql_fetch_row(result);
            if(!row){
                break;
            }
            for(int j=0;j<num_fields;j++){
                str+=string(row[j])+" ";
            }
            str+='\n';
        }
        if(!str.empty())
            str.pop_back();
    }
    else{
        cout<<"Get Result Error: "<<mysql_error(mysql)<<'\n';
        return false;
    }
    mysql_free_result(result);
    return true;
}