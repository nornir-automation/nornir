FROM python:3.6
RUN set -x && \
	pip install nornir
VOLUME [ "/nornir" ]
WORKDIR "/nornir"
ENTRYPOINT [ "/usr/local/bin/python" ]
#usage:
# from inside your nornir base directory run: docker run -it --rm -v `pwd`:/nornir nornir:latest get_facts.py
