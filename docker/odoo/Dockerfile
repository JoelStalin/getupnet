FROM odoo:19.0
USER root
COPY requirements.txt /tmp/requirements.txt
RUN apt-get update && apt-get install -y --no-install-recommends \
    awscli \
    openssh-client \
    nano \
    iputils-ping \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --no-cache-dir --break-system-packages -r /tmp/requirements.txt
USER odoo
