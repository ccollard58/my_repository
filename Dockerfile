FROM python:2.7.11

MAINTAINER jason.p.stone@oracle.com

COPY commscloud_heatgen /tmp/package/commscloud_heatgen
COPY commscloud_stacktools /tmp/package/commscloud_stacktools
COPY setup.py /tmp/package/setup.py

ENV http_proxy http://adc-proxy.oracle.com:80
ENV https_proxy http://adc-proxy.oracle.com:80
ENV HTTP_PROXY http://adc-proxy.oracle.com:80
ENV HTTPS_PROXY http://adc-proxy.oracle.com:80
ENV no_proxy ccp1,labs.nc.tekelec.com,us.oracle.com

RUN pip install /tmp/package

WORKDIR /root

COPY samples samples

CMD ["bash"]
