FROM python:2.7.11

MAINTAINER jason.p.stone@oracle.com

COPY leo_heatgen /tmp/package/leo_heatgen
COPY leo_stacktools /tmp/package/leo_stacktools
COPY setup.py /tmp/package/setup.py

ENV http_proxy=http://adc-proxy.oracle.com:80 \
    https_proxy=http://adc-proxy.oracle.com:80 \
    HTTP_PROXY=http://adc-proxy.oracle.com:80 \
    HTTPS_PROXY=http://adc-proxy.oracle.com:80 \
    no_proxy=ccp1,labs.nc.tekelec.com,us.oracle.com

RUN pip install /tmp/package

WORKDIR /root

COPY samples samples

CMD ["bash"]
