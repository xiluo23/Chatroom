.PHONY: all clean
CFLAGS = -Wall -g -O2
targets = client
sources = epoll_client.cpp epoll_client.h
objects = epoll_client.o
link=-lpthread `mysql_config --cflags --libs` -lcrypt


all: $(targets)
	@echo "Build complete!"

$(targets): $(objects)
	g++ $(CFLAGS) $(objects) -o $@ $(link)

%.o: %.cpp %.h
	g++ $(CFLAGS) -c $< -o $@ $(link)


clean:
	rm -f *.o  client
