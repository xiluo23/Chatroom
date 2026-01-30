#include <iostream>
#include <unordered_map>
#include <pthread.h>
#include <unistd.h>

using namespace std;

unordered_map<string, int> clint_nametofd;

void* send_thread(void* arg) {
    sleep(1);  // 等待一下，制造并发机会

    cout << "[send_thread] try to send to B\n";

    // ⚠️ 没加锁（故意的）
    if (clint_nametofd.count("B")) {
        int fd = clint_nametofd["B"];
        cout << "[send_thread] get fd = " << fd << endl;

        // 模拟 send
        sleep(2);  // 在这里制造时间窗口

        cout << "[send_thread] send to fd " << fd << endl;
    } else {
        cout << "[send_thread] B offline\n";
    }

    return nullptr;
}

void* disconnect_thread(void* arg) {
    sleep(2); // 确保发生在 send 过程中

    cout << "[disconnect_thread] erase B\n";

    // ⚠️ 没加锁（故意的）
    clint_nametofd.erase("B");

    cout << "[disconnect_thread] erased\n";

    return nullptr;
}

int main() {
    clint_nametofd["B"] = 100; // 假设 B 的 fd 是 100

    pthread_t t1, t2;
    pthread_create(&t1, nullptr, send_thread, nullptr);
    pthread_create(&t2, nullptr, disconnect_thread, nullptr);

    pthread_join(t1, nullptr);
    pthread_join(t2, nullptr);

    cout << "done\n";
    return 0;
}
