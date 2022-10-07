FROM python:3.10
RUN echo 'root:toor' | chpasswd
SHELL ["/bin/bash", "-c"]
ENV DEBIAN_FRONTEND="noninteractive"
RUN apt update
RUN apt install -y python3-dev
RUN apt install -y python3-venv
#RUN apt install -y rustc
RUN apt install -y wget
RUN apt install -y git
RUN apt install -y libssl-dev
RUN apt install -y libffi-dev
RUN apt install -y aria2
RUN apt clean

# workaround for QEMU bug: https://github.com/rust-lang/cargo/issues/8719
#RUN --security=insecure mkdir -p /root/.cargo && chmod 777 /root/.cargo && mount -t tmpfs none /root/.cargo && pip3 install --no-cache-dir cryptography

#RUN pip install certifi
#COPY utils/install_certificates.py /tmp
# RUN python /tmp/install_certificates.py


WORKDIR /app



RUN wget  http://raw.githubusercontent.com/python-poetry/poetry/master/install-poetry.py -O - > install-poetry.py
RUN  python3 install-poetry.py

ADD poetry.lock pyproject.toml  /app/

ENV PATH="/root/.local/bin:${PATH}"
RUN echo $PATH
RUN poetry install --no-interaction


COPY  . .




ENTRYPOINT ["poetry"]

