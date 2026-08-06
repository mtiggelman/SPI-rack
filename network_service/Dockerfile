FROM python:3.14-slim
LABEL authors="jc"

ENV PYTHONUNBUFFERED=1

RUN pip install --no-cache-dir pyserial==3.5

WORKDIR /app
COPY spirack_proxy.py .

ENTRYPOINT ["python", "spirack_proxy.py"]
