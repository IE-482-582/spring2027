FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

# Install Gazebo Harmonic
RUN apt update && apt install -y \
    curl gnupg lsb-release \
    python3 python3-pip python3-numpy python3-opencv \
    libgl1 \
    && curl -sSL http://packages.osrfoundation.org/gazebo.gpg | apt-key add - \
    && echo "deb http://packages.osrfoundation.org/gazebo/ubuntu-stable $(lsb_release -cs) main" > /etc/apt/sources.list.d/gazebo-stable.list \
    && apt update \
    && apt install -y gz-harmonic python3-gz-transport13 \
    && rm -rf /var/lib/apt/lists/*

# Text editor
RUN apt update && apt install -y nano

# Environment
ENV DISPLAY=:0

COPY Projects/socket_demo/client/requirements.txt /tmp/req_socket.txt
COPY Projects/ub_racer/client/requirements.txt /tmp/req_racer.txt
RUN pip install --no-cache-dir --break-system-packages -r /tmp/req_socket.txt -r /tmp/req_racer.txt

WORKDIR /workspace

RUN apt install git -y

# olab_camera and olab_utils (from olab_code, released on PyPI; formerly
# ub_camera / ub_code). olab_camera and ultralytics both use plain
# opencv-python now, so the yolo extra installs cleanly with no opencv swap.
# libzbar0 is the system library pyzbar ([barcode] extra) wraps --
# socket_demo's client uses addBarcode().
# --ignore-installed because pip can't upgrade apt's python3-numpy in place.
RUN apt update && apt install -y libzbar0 && rm -rf /var/lib/apt/lists/*
RUN pip install --break-system-packages --ignore-installed \
        "olab-camera[yolo,websocket,webrtc,barcode]>=0.1.0" \
        "olab-utils>=0.2.0"


COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
