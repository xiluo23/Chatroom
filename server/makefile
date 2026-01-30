.PHONY: all clean
CFLAGS = -Wall -g -O2
targets = serv
sources = epoll_ser.cpp ErrorCode.cpp Logger.cpp
headers = epoll_ser.h ErrorCode.h Logger.h MyDb.h 
objects = epoll_ser.o ErrorCode.o Logger.o

link=-lpthread `mysql_config --cflags --libs` -lcrypt
all: $(targets)
	@echo "Build complete!"

$(targets): $(objects)
	g++ $(CFLAGS) $(objects) -o $@ $(link)

epoll_ser.o: epoll_ser.cpp $(headers)
	g++ $(CFLAGS) -c $< -o $@ $(link)

ErrorCode.o: ErrorCode.cpp ErrorCode.h
	g++ $(CFLAGS) -c $< -o $@ $(link)

Logger.o: Logger.cpp Logger.h ErrorCode.h
	g++ $(CFLAGS) -c $< -o $@ $(link)

clean:
	rm -f *.o $(targets)
