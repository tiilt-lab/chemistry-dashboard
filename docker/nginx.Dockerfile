FROM nginx
WORKDIR /var/lib/

# Create build folder and create database
RUN mkdir -p chemistry-dashboard/frontend/build && \
    chmod 777 -R chemistry-dashboard
COPY frontend/entry.sh chemistry-dashboard/entry.sh
RUN chmod +x /var/lib/chemistry-dashboard/entry.sh
COPY deploy/nginx.conf /etc/nginx/nginx.conf
COPY deploy/nginx-headers.conf /etc/nginx/nginx-headers.conf

EXPOSE 80 443 9000 9001 9003

HEALTHCHECK --start-period=2m --interval=30s --timeout=10s --retries=3 \
  CMD curl -sSf http://127.0.0.1 > /dev/null

ENTRYPOINT [ "/var/lib/chemistry-dashboard/entry.sh" ]

CMD ["tail", "-f", "/dev/null"]
