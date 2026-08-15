# A reproducible environment for the test suite, including the OpenGL tests.
#
# Why a container for a desktop OpenGL app? Not to run the app -- a GUI in a
# container needs the host's display socket, which makes it harder to run, not
# easier. The point is the *tests*: `tests/test_render.py` needs a GL context,
# and that normally means "whatever driver happens to be on your machine".
# This image pins the other half of that: freeglut for the context, Xvfb for a
# display that lives in memory, and Mesa's software rasterizer instead of a
# GPU. The rendering tests then produce the same pixels on a laptop, on a CI
# runner and on a machine with no graphics card at all.
#
#   docker build -t morph-3d-tests .
#   docker run --rm morph-3d-tests

FROM python:3.12-slim

# freeglut3-dev  -> the GLUT implementation PyOpenGL binds to
# libgl1          -> the OpenGL runtime itself
# libgl1-mesa-dri -> Mesa's drivers, including the llvmpipe software rasterizer
# libglu1-mesa    -> GLU, used here for gluPerspective / gluLookAt
# xvfb            -> an X server that renders into memory, with no monitor
# xauth           -> xvfb-run authorises the X connection with it. Debian lists
#                    it as a Recommends of xvfb rather than a Depends, so
#                    --no-install-recommends silently leaves it out and
#                    xvfb-run then fails. It has to be named explicitly.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        freeglut3-dev \
        libgl1 \
        libgl1-mesa-dri \
        libglu1-mesa \
        xauth \
        xvfb \
    && rm -rf /var/lib/apt/lists/*

# LIBGL_ALWAYS_SOFTWARE forces Mesa to use llvmpipe instead of looking for
# hardware that is not there.
#
# PYTHONUNBUFFERED matters more than it looks: CI pipes the container output,
# and a piped stdout makes Python switch to block buffering, so nothing appears
# until the buffer fills or the process exits. If the run is then killed, the
# buffer dies with it and the log is empty.
ENV LIBGL_ALWAYS_SOFTWARE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# dependencies first, so editing the source does not invalidate this layer
COPY requirements-dev.txt ./
RUN pip install -r requirements-dev.txt

COPY . .

# xvfb-run starts a throwaway X server and runs the command against it
CMD ["xvfb-run", "-a", "pytest", "--cov", "--cov-report=term-missing"]
