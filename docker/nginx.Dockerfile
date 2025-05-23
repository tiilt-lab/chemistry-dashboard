FROM nginx
WORKDIR /var/lib/

RUN mkdir -p chemistry-dashboard/frontend/build
RUN chmod 777 -R chemistry-dashboard
COPY frontend/build chemistry-dashboard/frontend/build
COPY frontend/entry.sh chemistry-dashboard/entry.sh
COPY UA chemistry-dashboard/UA

COPY deploy/nginx.conf /etc/nginx/nginx.conf
COPY deploy/nginx-headers.conf /etc/nginx/nginx-headers.conf


EXPOSE 80 443 9000 9001 9003

ENTRYPOINT [ "chemistry-dashboard/entry.sh" ]

CMD ["tail", "-f", "/dev/null"]
