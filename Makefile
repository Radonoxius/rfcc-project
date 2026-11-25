CC ?= cc
CFLAGS ?= -O2 -std=c11 -Wall -Wextra -Wpedantic -Iinclude
LDLIBS ?= -lm

all: resonator-array receiver-position-tracker

resonator-array: src/main.o src/resonator_array.o
	$(CC) $(CFLAGS) $^ $(LDLIBS) -o $@

receiver-position-tracker: scripts/receiver_position_tracker.py
	cp $< $@
	chmod +x $@

src/%.o: src/%.c include/resonator_array.h
	$(CC) $(CFLAGS) -c $< -o $@

clean:
	rm -f resonator-array receiver-position-tracker src/*.o results/*.csv results/*.png

.PHONY: all clean
