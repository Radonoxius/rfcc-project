CC ?= cc
CFLAGS ?= -O2 -std=c11 -Wall -Wextra -Wpedantic -Iinclude
LDLIBS ?= -lm

all: rfcc

rfcc: src/main.o src/resonator_array.o
	$(CC) $(CFLAGS) $^ $(LDLIBS) -o $@

src/%.o: src/%.c include/resonator_array.h
	$(CC) $(CFLAGS) -c $< -o $@

clean:
	rm -f rfcc src/*.o results/*.csv results/*.png

.PHONY: all clean
