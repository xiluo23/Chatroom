.PHONY: all clean
CFLAGS = -Wall -g -O2
targets = serv
sources = epoll_ser.cpp MyDb.h epoll_ser.h ThreadPool.h
objects = epoll_ser.o

link=-lpthread `mysql_config --cflags --libs` -lcrypt
all: $(targets)
	@echo "Build complete!"

$(targets): $(objects)
	g++ $(CFLAGS) $(objects) -o $@ $(link)

%.o: %.cpp %.h
	g++ $(CFLAGS) -c $< -o $@ $(link)


clean:
	rm -f *.o  $(targets) $(obj)
