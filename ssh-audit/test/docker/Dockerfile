FROM ubuntu:16.04

COPY openssh-4.0p1/sshd /openssh/sshd-4.0p1
COPY openssh-5.6p1/sshd /openssh/sshd-5.6p1
COPY openssh-8.0p1/sshd /openssh/sshd-8.0p1
COPY dropbear-2019.78/dropbear /dropbear/dropbear-2019.78
COPY tinyssh-20190101/build/bin/tinysshd /tinysshd/tinyssh-20190101

# Dropbear host keys.
COPY dropbear_*_host_key* /etc/dropbear/

# OpenSSH configs.
COPY sshd_config* /etc/ssh/

# OpenSSH host keys & moduli file.
COPY ssh_host_* /etc/ssh/
COPY ssh1_host_* /etc/ssh/
COPY moduli_1024 /usr/local/etc/moduli

# TinySSH host keys.
COPY ed25519.pk /etc/tinyssh/
COPY .ed25519.sk /etc/tinyssh/

COPY debug.sh /debug.sh

RUN apt update 2> /dev/null
RUN apt install -y libssl-dev strace rsyslog ucspi-tcp 2> /dev/null
RUN apt clean 2> /dev/null
RUN useradd -s /bin/false sshd
RUN mkdir /var/empty

EXPOSE 22
