#!/bin/sh
# Start Xvfb by hand, then run whatever was asked for.
#
# This replaces `xvfb-run`, which hangs in this image and prints nothing at all
# while doing it: it waits for Xvfb to report its display number over a pipe,
# and when Xvfb fails to start, that wait never ends. A silent hang is the
# worst failure mode there is -- the CI job burned fifteen minutes and produced
# an empty log.
#
# Doing it by hand costs about twenty lines and buys two things: Xvfb's own
# error messages reach the log, and a server that does not come up ends the run
# with a message instead of stalling it.
set -e

DISPLAY_NUM=99
SOCKET="/tmp/.X11-unix/X${DISPLAY_NUM}"

Xvfb ":${DISPLAY_NUM}" -screen 0 640x480x24 &
XVFB_PID=$!

# Wait for the socket to appear, but give up rather than block forever. Fifty
# tries at 0.1s is five seconds; Xvfb normally needs a small fraction of that.
attempt=0
while [ "$attempt" -lt 50 ]; do
    if [ -e "$SOCKET" ]; then
        break
    fi
    if ! kill -0 "$XVFB_PID" 2>/dev/null; then
        echo "entrypoint: Xvfb exited before the display was ready" >&2
        wait "$XVFB_PID" || true
        exit 1
    fi
    attempt=$((attempt + 1))
    sleep 0.1
done

if [ ! -e "$SOCKET" ]; then
    echo "entrypoint: Xvfb did not create ${SOCKET} within 5 seconds" >&2
    kill "$XVFB_PID" 2>/dev/null || true
    exit 1
fi

echo "entrypoint: Xvfb ready on :${DISPLAY_NUM}"
export DISPLAY=":${DISPLAY_NUM}"
exec "$@"
