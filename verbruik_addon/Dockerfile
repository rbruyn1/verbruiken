ARG BUILD_FROM
FROM $BUILD_FROM

WORKDIR /app
COPY app/ /app/
RUN pip install --no-cache-dir flask openpyxl

COPY run.sh /
RUN chmod a+x /run.sh

CMD [ "/run.sh" ]
